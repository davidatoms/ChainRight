"""Tests for chainright.sat_solver."""

import pytest

from chainright.equilibrium import (
    EquilibriumReport,
    expert_agreement_test,
    proportionality_test,
)
from chainright.sat_solver import (
    SearchResult,
    solve_equilibrium,
    truncation_generator,
    word_drop_generator,
)


def _passing_evaluator(_candidate: str) -> EquilibriumReport:
    report = EquilibriumReport()
    report.add("expert", expert_agreement_test("p", "e", 5.0, 3.0))
    return report


def _failing_evaluator(_candidate: str) -> EquilibriumReport:
    report = EquilibriumReport()
    report.add("expert", expert_agreement_test("p", "e", 1.0, 3.0))
    return report


def _gates_at_word_count(target_words: int):
    """Evaluator that passes only when the candidate has <= target_words."""
    def fn(candidate: str) -> EquilibriumReport:
        report = EquilibriumReport()
        if len(candidate.split()) <= target_words:
            report.add("expert", expert_agreement_test("p", "e", 5.0, 3.0))
        else:
            report.add("expert", expert_agreement_test("p", "e", 1.0, 3.0))
        return report
    return fn


class TestSolveEquilibriumBasics:
    def test_initial_prompt_satisfies_immediately(self):
        result = solve_equilibrium(
            initial_prompt="hi",
            candidate_generator=lambda p: [],
            evaluator=_passing_evaluator,
            budget_seconds=10.0,
            cps=10.0,
        )
        assert result.accepted
        assert result.final_candidate == "hi"
        assert result.candidates_examined == 1

    def test_no_candidate_satisfies(self):
        result = solve_equilibrium(
            initial_prompt="hi",
            candidate_generator=lambda p: ["a", "b", "c"],
            evaluator=_failing_evaluator,
            budget_seconds=100.0,
        )
        assert not result.accepted
        assert result.final_candidate is None
        assert result.candidates_examined == 4  # initial + 3

    def test_search_finds_satisfying_candidate(self):
        # Initial fails (3 words > 2), one of the candidates passes.
        result = solve_equilibrium(
            initial_prompt="one two three",
            candidate_generator=lambda p: ["a b c d", "ok ok"],
            evaluator=_gates_at_word_count(2),
            budget_seconds=100.0,
        )
        assert result.accepted
        assert result.final_candidate == "ok ok"
        assert result.candidates_examined == 3  # initial fail, longer fail, then pass


class TestBudgetEnforcement:
    def test_budget_aborts_search(self):
        # Long candidates each cost ~1s at cps=10, budget=2s, so we get 2 then abort.
        long_str = "x" * 10
        result = solve_equilibrium(
            initial_prompt=long_str,
            candidate_generator=lambda p: [long_str, long_str, long_str, long_str],
            evaluator=_failing_evaluator,
            budget_seconds=2.0,
            cps=10.0,
        )
        assert result.aborted_over_budget
        assert not result.accepted
        assert result.candidates_examined == 2

    def test_cost_to_satisfy_recorded(self):
        result = solve_equilibrium(
            initial_prompt="abcdefghij",  # 10 chars
            candidate_generator=lambda p: [],
            evaluator=_passing_evaluator,
            budget_seconds=100.0,
            cps=10.0,
        )
        assert result.cost_to_satisfy == pytest.approx(1.0)


class TestCandidateGenerators:
    def test_truncation_generator_skips_too_long_strides(self):
        gen = truncation_generator(strides=(2, 5, 100))
        out = gen("one two three four five six")
        assert out == ["one two", "one two three four five"]

    def test_truncation_generator_dedups(self):
        gen = truncation_generator(strides=(2, 2, 3))
        out = gen("one two three four")
        assert out == ["one two", "one two three"]

    def test_word_drop_generator(self):
        gen = word_drop_generator(n_drops=1, keep_first=1, keep_last=0)
        out = gen("the fed raised rates")
        # keep_first=1, n_drops=1, can drop position 1 ("fed"), 2 ("raised")
        assert "the raised rates" in out
        assert "the fed rates" in out

    def test_word_drop_generator_empty_when_short(self):
        gen = word_drop_generator(n_drops=2, keep_first=1, keep_last=1)
        out = gen("only three words")
        assert out == []
