"""Tests for chainright.equilibrium.

The LLM is mocked throughout — these tests exercise the harness logic, not
any real provider. Real-provider runs belong in examples/.
"""

import pytest

from chainright.equilibrium import (
    EquilibriumReport,
    compression_test,
    expert_agreement_test,
    ground_truth_score,
    jaccard,
    prompt_decomposition_test,
    proportionality_test,
    provider_comparison_test,
    semantic_stability_test,
    time_cost_test,
    verifiability_iteration_test,
)


# ---------------------------------------------------------------------------
# Scoring primitives
# ---------------------------------------------------------------------------

class TestJaccard:
    def test_identical_strings_score_1(self):
        assert jaccard("the fed raised rates", "the fed raised rates") == 1.0

    def test_disjoint_strings_score_0(self):
        assert jaccard("apples oranges", "trains planes") == 0.0

    def test_partial_overlap(self):
        # {fed, raised, rates} vs {fed, cut, rates} -> intersection 2, union 4
        assert jaccard("fed raised rates", "fed cut rates") == pytest.approx(2 / 4)

    def test_case_insensitive(self):
        assert jaccard("FED Raised Rates", "fed raised rates") == 1.0

    def test_empty_inputs(self):
        assert jaccard("", "") == 1.0
        assert jaccard("hello", "") == 0.0


# ---------------------------------------------------------------------------
# 1. Compression
# ---------------------------------------------------------------------------

class TestCompressionTest:
    def test_compression_wins_when_tokens_drop_and_accuracy_holds(self):
        gt = "the fed raised rates by 25 basis points"

        def llm(p: str) -> str:
            return gt  # both prompts produce the same correct answer

        verbose = "Could you please tell me, if you would, what action the Federal Reserve recently took regarding interest rates"
        compressed = "What did the Fed do to rates?"

        result = compression_test(llm, verbose, compressed, gt)
        assert result.token_reduction > 0
        assert result.accuracy_delta == 0.0
        assert result.passes

    def test_compression_loses_when_accuracy_drops(self):
        gt = "the fed raised rates by 25 basis points"
        verbose = "What did the Federal Reserve do to interest rates last meeting"
        compressed = "Fed?"

        def llm(p: str) -> str:
            return gt if "Federal Reserve" in p else "I don't know"

        result = compression_test(llm, verbose, compressed, gt)
        assert result.accuracy_delta < 0
        assert not result.passes


# ---------------------------------------------------------------------------
# 2. Proportionality
# ---------------------------------------------------------------------------

class TestProportionalityTest:
    def test_short_prompt_long_response_is_flagged(self):
        long_response = "word " * 200

        def llm(_: str) -> str:
            return long_response

        result = proportionality_test(llm, "Who is the chair?", threshold=5.0)
        assert result.flagged
        assert result.ratio > 5.0
        assert not result.passes

    def test_proportionate_response_passes(self):
        def llm(_: str) -> str:
            return "Jerome Powell"

        result = proportionality_test(llm, "Who is the chair of the Federal Reserve?", threshold=5.0)
        assert not result.flagged
        assert result.passes


# ---------------------------------------------------------------------------
# 3. Time cost
# ---------------------------------------------------------------------------

class TestTimeCostTest:
    def test_ai_wins_when_baseline_is_long(self):
        result = time_cost_test(
            prompt="Summarize Q3 earnings for AAPL",
            response="Revenue $90B, EPS $1.46, beat consensus.",
            expert_baseline_seconds=600.0,
            verification_seconds=20.0,
        )
        assert result.passes
        assert result.total_human_time_seconds < 600.0

    def test_ai_loses_when_baseline_is_short(self):
        result = time_cost_test(
            prompt="An extremely long, hedged, multi-clause prompt " * 20,
            response="A correspondingly long answer " * 50,
            expert_baseline_seconds=10.0,
            verification_seconds=60.0,
        )
        assert result.efficiency_collapses
        assert not result.passes


# ---------------------------------------------------------------------------
# 4. Semantic stability
# ---------------------------------------------------------------------------

class TestSemanticStability:
    def test_stable_model_passes(self):
        canonical = "the fed raised rates by twenty five basis points"

        def llm(_: str) -> str:
            return canonical

        variants = [
            "What did the Fed do to rates?",
            "Did the Federal Reserve adjust rates?",
            "Tell me about the Fed's recent rate decision.",
        ]
        result = semantic_stability_test(llm, variants, threshold=0.9)
        assert result.mean_similarity == pytest.approx(1.0)
        assert result.passes

    def test_unstable_model_fails(self):
        responses_iter = iter([
            "the fed raised rates",
            "the ecb cut deposit rates",
            "japan kept rates near zero",
        ])

        def llm(_: str) -> str:
            return next(responses_iter)

        variants = ["a", "b", "c"]
        result = semantic_stability_test(llm, variants, threshold=0.6)
        assert not result.passes
        assert result.min_similarity < 0.6

    def test_requires_at_least_two_variants(self):
        with pytest.raises(ValueError):
            semantic_stability_test(lambda p: "x", ["only one"])


# ---------------------------------------------------------------------------
# 5. Prompt decomposition
# ---------------------------------------------------------------------------

class TestPromptDecomposition:
    def test_consistent_decomposition_passes(self):
        def llm(p: str) -> str:
            return "fed raised rates inflation cooling labor market tight"

        result = prompt_decomposition_test(
            llm,
            composite_prompt="Tell me about the Fed, inflation, and the labor market.",
            sub_prompts=[
                "What did the Fed do?",
                "What is happening with inflation?",
                "How is the labor market?",
            ],
            threshold=0.4,
        )
        assert result.passes

    def test_inconsistent_decomposition_fails(self):
        def llm(p: str) -> str:
            if "Fed, inflation, and the labor market" in p:
                return "completely unrelated answer about ocean tides"
            return "fed raised rates inflation cooling labor market tight"

        result = prompt_decomposition_test(
            llm,
            composite_prompt="Tell me about the Fed, inflation, and the labor market.",
            sub_prompts=["What did the Fed do?", "What is happening with inflation?"],
            threshold=0.4,
        )
        assert not result.passes


# ---------------------------------------------------------------------------
# 6. Expert agreement
# ---------------------------------------------------------------------------

class TestExpertAgreement:
    def test_pass_at_or_above_minimum(self):
        r = expert_agreement_test(
            prompt="What is the Fed's reaction function?",
            expert_id="econ-pm-01",
            rating=4.0,
            minimum=3.0,
            rationale="well-scoped, single concept",
        )
        assert r.passes

    def test_fail_below_minimum(self):
        r = expert_agreement_test(
            prompt="thoughts??",
            expert_id="econ-pm-01",
            rating=1.0,
            minimum=3.0,
        )
        assert not r.passes


# ---------------------------------------------------------------------------
# 7. Provider comparison
# ---------------------------------------------------------------------------

class TestProviderComparison:
    def test_best_provider_is_highest_score(self):
        gt = "fed raised rates by 25 basis points"
        providers = {
            "good_open_source": lambda p: "fed raised rates by 25 basis points",
            "bad_open_source": lambda p: "no idea",
            "closed": lambda p: "fed raised rates",
        }
        cmp = provider_comparison_test(providers, "What did the Fed do?", gt)
        best = cmp.best()
        assert best is not None
        assert best.provider == "good_open_source"
        assert best.score == 1.0

    def test_results_have_latency(self):
        cmp = provider_comparison_test(
            {"x": lambda p: "answer"},
            "q",
            "answer",
        )
        assert cmp.results[0].latency_seconds >= 0.0

    def test_passes_when_best_above_floor(self):
        cmp = provider_comparison_test(
            {"x": lambda p: "fed raised rates"},
            "q",
            "fed raised rates",
            score_floor=0.5,
        )
        assert cmp.passes

    def test_fails_when_best_below_floor(self):
        cmp = provider_comparison_test(
            {"x": lambda p: "completely different words"},
            "q",
            "fed raised rates",
            score_floor=0.5,
        )
        assert not cmp.passes

    def test_default_floor_is_0_5(self):
        # Score 0.5 exactly should pass with default floor.
        cmp = provider_comparison_test(
            {"x": lambda p: "fed cut rates"},  # 2/4 jaccard with "fed raised rates"
            "q",
            "fed raised rates",
        )
        assert cmp.score_floor == 0.5
        assert cmp.passes

    def test_provider_comparison_participates_in_equilibrium(self):
        """Regression: aggregator must see provider_comparison_test as a real clause."""
        from chainright.equilibrium import EquilibriumReport
        report = EquilibriumReport()
        report.add(
            "providers",
            provider_comparison_test(
                {"good": lambda p: "fed raised rates"},
                "q",
                "fed raised rates",
                score_floor=0.5,
            ),
        )
        assert report.at_equilibrium is True
        assert report.failing() == []


# ---------------------------------------------------------------------------
# 8. Verifiability iteration
# ---------------------------------------------------------------------------

class TestVerifiabilityIteration:
    def test_accepted_on_first_try(self):
        result = verifiability_iteration_test(
            llm=lambda p: "correct",
            initial_prompt="ask",
            verifier=lambda r: r == "correct",
            refine=lambda p, r: p + " more detail",
            max_rounds=5,
        )
        assert result.accepted
        assert result.rounds == 1

    def test_accepted_after_refinement(self):
        attempts = iter(["wrong", "still wrong", "correct"])

        def llm(_: str) -> str:
            return next(attempts)

        result = verifiability_iteration_test(
            llm=llm,
            initial_prompt="ask",
            verifier=lambda r: r == "correct",
            refine=lambda p, r: p + " try again",
            max_rounds=5,
        )
        assert result.accepted
        assert result.rounds == 3

    def test_gives_up_at_max_rounds(self):
        result = verifiability_iteration_test(
            llm=lambda p: "wrong",
            initial_prompt="ask",
            verifier=lambda r: False,
            refine=lambda p, r: p,
            max_rounds=3,
        )
        assert not result.accepted
        assert result.rounds == 3


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

class TestEquilibriumReport:
    def test_empty_report_is_not_at_equilibrium(self):
        assert not EquilibriumReport().at_equilibrium

    def test_all_passing_components_means_equilibrium(self):
        report = EquilibriumReport()
        report.add("expert", expert_agreement_test("p", "e", 5.0, 3.0))
        report.add("time", time_cost_test("p", "r", expert_baseline_seconds=600.0))
        assert report.at_equilibrium
        assert report.failing() == []

    def test_one_failing_component_breaks_equilibrium(self):
        report = EquilibriumReport()
        report.add("expert_ok", expert_agreement_test("p", "e", 5.0, 3.0))
        report.add("expert_bad", expert_agreement_test("p", "e", 1.0, 3.0))
        assert not report.at_equilibrium
        assert "expert_bad" in report.failing()

    def test_ground_truth_score_used_via_jaccard(self):
        assert ground_truth_score("alpha beta", "alpha beta") == 1.0


# ---------------------------------------------------------------------------
# Cost-weighted aggregation
# ---------------------------------------------------------------------------

class TestCostWeightedAggregation:
    def test_typing_cost_zero_for_empty_report(self):
        assert EquilibriumReport().typing_cost_seconds() == 0.0

    def test_typing_cost_scales_with_cps(self):
        report = EquilibriumReport()
        report.add(
            "expert",
            expert_agreement_test("p" * 100, "e", 5.0, 3.0, rationale="r" * 100),
        )
        # 200 chars typed total
        slow = report.typing_cost_seconds(cps=1.0)
        fast = report.typing_cost_seconds(cps=10.0)
        assert slow == pytest.approx(200.0)
        assert fast == pytest.approx(20.0)

    def test_cost_breakdown_contains_passes(self):
        report = EquilibriumReport()
        report.add("ok", expert_agreement_test("hi", "e", 5.0, 3.0))
        report.add("bad", expert_agreement_test("hi", "e", 1.0, 3.0))
        bd = report.cost_breakdown(cps=3.5)
        assert bd["ok"]["passes"] is True
        assert bd["bad"]["passes"] is False
        assert bd["ok"]["typed_chars"] == 2

    def test_cost_weighted_summary_shape(self):
        report = EquilibriumReport()
        report.add("expert", expert_agreement_test("p" * 35, "e", 5.0, 3.0))
        s = report.cost_weighted_summary(cps=3.5)
        assert s["at_equilibrium"] is True
        assert s["failing_components"] == []
        assert s["total_typing_seconds"] == pytest.approx(10.0)
        assert s["cps_assumed"] == 3.5
        assert "expert" in s["components"]

    def test_time_cost_result_has_zero_typed_chars(self):
        from chainright.equilibrium import result_typed_chars
        r = time_cost_test("anything", "anything", expert_baseline_seconds=1.0)
        assert result_typed_chars(r) == 0
