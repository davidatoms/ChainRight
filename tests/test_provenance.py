"""Tests for chainright.provenance and chainright.llm_adapters.static_corpus_llm."""

import json

import pytest

from chainright.blockchain import Blockchain
from chainright.equilibrium import (
    EquilibriumReport,
    expert_agreement_test,
    proportionality_test,
)
from chainright.llm_adapters import static_corpus_llm
from chainright.provenance import (
    build_corpus_check_payload,
    build_payload,
    chain_corpus_check,
    chain_equilibrium_run,
    chain_runs,
    sha256_hex,
    verify_against_chain,
)


def _passing_report(prompt: str = "p") -> EquilibriumReport:
    report = EquilibriumReport()
    report.add("expert", expert_agreement_test(prompt, "e", 5.0, 3.0))
    return report


def _failing_report() -> EquilibriumReport:
    report = EquilibriumReport()
    report.add("expert", expert_agreement_test("p", "e", 1.0, 3.0))
    return report


class TestStaticCorpusLLM:
    def test_returns_text_regardless_of_prompt(self):
        llm = static_corpus_llm("the fed raised rates")
        assert llm("anything") == "the fed raised rates"
        assert llm("") == "the fed raised rates"


class TestSha256:
    def test_deterministic(self):
        assert sha256_hex("hello") == sha256_hex("hello")

    def test_different_inputs_different_hashes(self):
        assert sha256_hex("a") != sha256_hex("b")


class TestBuildPayload:
    def test_payload_contains_required_fields(self):
        payload = build_payload(
            prompt="p", response="r", model_id="claude-3-5-sonnet",
            report=_passing_report(),
            session_id="abc123",
        )
        assert payload["session_id"] == "abc123"
        assert payload["prompt_hash"] == sha256_hex("p")
        assert payload["response_hash"] == sha256_hex("r")
        assert payload["model_id"] == "claude-3-5-sonnet"
        assert payload["at_equilibrium"] is True
        assert payload["failing_components"] == []

    def test_payload_includes_extra(self):
        payload = build_payload(
            prompt="p", response="r", model_id="m",
            report=_passing_report(),
            extra={"corpus_index": 42, "split": "test"},
        )
        assert payload["extra"]["corpus_index"] == 42


class TestChainEquilibriumRun:
    def test_appends_block(self):
        bc = Blockchain(difficulty=1)
        result = chain_equilibrium_run(
            bc, prompt="p", response="r", model_id="m",
            report=_passing_report(),
        )
        assert result["block_index"] == 1  # genesis is 0
        assert len(bc.chain) == 2

    def test_chain_remains_valid(self):
        bc = Blockchain(difficulty=1)
        chain_equilibrium_run(bc, "p", "r", "m", _passing_report())
        chain_equilibrium_run(bc, "p2", "r2", "m", _failing_report())
        assert bc.is_chain_valid()
        assert len(bc.chain) == 3

    def test_payload_recoverable_from_block(self):
        bc = Blockchain(difficulty=1)
        chain_equilibrium_run(bc, "p", "r", "m", _passing_report())
        block = bc.chain[1]
        # mine_pending_data wraps pending_data as a JSON list of strings.
        items = json.loads(block.data)
        assert isinstance(items, list)
        payload = json.loads(items[0])
        assert payload["model_id"] == "m"


class TestChainRuns:
    def test_batch_chains_in_order(self):
        bc = Blockchain(difficulty=1)
        runs = [
            {"prompt": "p1", "response": "r1", "model_id": "m", "report": _passing_report()},
            {"prompt": "p2", "response": "r2", "model_id": "m", "report": _failing_report()},
            {"prompt": "p3", "response": "r3", "model_id": "m", "report": _passing_report()},
        ]
        out = chain_runs(bc, runs)
        assert len(out) == 3
        assert [r["block_index"] for r in out] == [1, 2, 3]


class TestAttributionGraphHashing:
    """Coverage for the optional attribution_graph parameter on chain_equilibrium_run.

    Uses a torch tensor as a stand-in for a circuit-tracer Graph since both
    are torch.save-serializable and that's all hash_attribution_graph
    requires.
    """

    def test_hash_is_deterministic(self):
        import torch
        from chainright.provenance import hash_attribution_graph
        g = torch.zeros(3, 3)
        h1 = hash_attribution_graph(g)
        h2 = hash_attribution_graph(g)
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_changes_with_content(self):
        import torch
        from chainright.provenance import hash_attribution_graph
        a = torch.zeros(3, 3)
        b = torch.ones(3, 3)
        assert hash_attribution_graph(a) != hash_attribution_graph(b)

    def test_chain_run_includes_graph_hash_when_supplied(self):
        import torch
        bc = Blockchain(difficulty=1)
        fake_graph = torch.zeros(2, 2)
        result = chain_equilibrium_run(
            bc, "p", "r", "m", _passing_report(),
            attribution_graph=fake_graph,
        )
        assert "attribution_graph_hash" in result["payload"]
        assert len(result["payload"]["attribution_graph_hash"]) == 64

    def test_chain_run_omits_graph_hash_when_absent(self):
        bc = Blockchain(difficulty=1)
        result = chain_equilibrium_run(bc, "p", "r", "m", _passing_report())
        assert "attribution_graph_hash" not in result["payload"]
        assert "attribution_graph_summary" not in result["payload"]


class TestSummarizeAttributionGraph:
    """Coverage for summarize_attribution_graph using a Graph-like stand-in."""

    def _make_fake_graph(self):
        """A SimpleNamespace with the fields summarize cares about."""
        from types import SimpleNamespace
        import torch
        cfg = SimpleNamespace(
            model_name="meta-llama/Llama-3.2-1B",
            n_layers=16, n_heads=32, d_model=2048,
        )
        target = SimpleNamespace(vocab_idx=42)
        return SimpleNamespace(
            input_string="the fed raised rates",
            input_tokens=torch.zeros(7, dtype=torch.long),
            adjacency_matrix=torch.zeros(8, 8),
            active_features=torch.zeros(120, 3),
            activation_values=torch.zeros(120),
            selected_features=torch.zeros(50, 3),
            scan="mntss/transcoder-Llama-3.2-1B",
            n_pos=7,
            vocab_size=128256,
            cfg=cfg,
            logit_targets=[target],
            logit_probabilities=torch.tensor([0.85]),
        )

    def test_summary_extracts_lightweight_fields(self):
        from chainright.provenance import summarize_attribution_graph
        g = self._make_fake_graph()
        s = summarize_attribution_graph(g)
        assert s["input_string_length"] == len("the fed raised rates")
        assert s["input_token_count"] == 7
        assert s["n_positions"] == 7
        assert s["vocab_size"] == 128256
        assert s["n_active_features"] == 120
        assert s["transcoder_scan"] == "mntss/transcoder-Llama-3.2-1B"
        assert s["cfg_model_name"] == "meta-llama/Llama-3.2-1B"
        assert s["cfg_n_layers"] == 16
        assert len(s["logit_targets"]) == 1
        assert s["logit_targets"][0]["vocab_idx"] == 42
        assert s["logit_targets"][0]["probability"] == pytest.approx(0.85, rel=1e-3)

    def test_summary_tolerates_missing_fields(self):
        from types import SimpleNamespace
        from chainright.provenance import summarize_attribution_graph
        # Graph stand-in with almost nothing — should not raise.
        g = SimpleNamespace(input_string="hi")
        s = summarize_attribution_graph(g)
        assert s["input_string_length"] == 2

    def test_chain_run_includes_graph_summary(self):
        from chainright.provenance import chain_equilibrium_run
        bc = Blockchain(difficulty=1)
        g = self._make_fake_graph()
        result = chain_equilibrium_run(
            bc, "p", "r", "m", _passing_report(),
            attribution_graph=g,
        )
        assert "attribution_graph_hash" in result["payload"]
        assert "attribution_graph_summary" in result["payload"]
        s = result["payload"]["attribution_graph_summary"]
        assert s["transcoder_scan"] == "mntss/transcoder-Llama-3.2-1B"
        assert s["cfg_n_layers"] == 16


class TestCorpusCheckChaining:
    """Coverage for chain_corpus_check — the absence-attestation primitive."""

    def _sample_results(self):
        return [
            {"source": "webtext", "split": "test", "present": False,
             "first_match_record_index": None, "records_scanned": 5000},
            {"source": "small-117M-k40", "split": "test", "present": False,
             "first_match_record_index": None, "records_scanned": 5000},
        ]

    def test_payload_stores_text_hash_not_text(self):
        results = self._sample_results()
        payload = build_corpus_check_payload(
            text="confidential memo about Project Alpha",
            results=results,
            verdict="NOT FOUND in any selected corpus.",
            sources=["webtext", "small-117M-k40"],
            splits=["test"],
        )
        assert "text" not in payload
        assert payload["text_hash"] == sha256_hex("confidential memo about Project Alpha")
        assert payload["text_length"] == len("confidential memo about Project Alpha")
        assert payload["kind"] == "corpus_check"

    def test_chain_corpus_check_appends_block(self):
        bc = Blockchain(difficulty=1)
        results = self._sample_results()
        info = chain_corpus_check(
            blockchain=bc,
            text="never published anywhere",
            results=results,
            verdict="NOT FOUND in any selected corpus.",
            sources=["webtext", "small-117M-k40"],
            splits=["test"],
            session_id="audit-2026-05-10-001",
        )
        assert info["block_index"] == 1
        assert len(bc.chain) == 2
        assert bc.is_chain_valid()
        assert info["payload"]["session_id"] == "audit-2026-05-10-001"

    def test_payload_includes_per_source_results(self):
        results = [
            {"source": "webtext", "split": "test", "present": True,
             "first_match_record_index": 142, "records_scanned": 142},
            {"source": "custom:internal_archive", "split": "custom",
             "present": False, "first_match_record_index": None,
             "records_scanned": 89},
        ]
        payload = build_corpus_check_payload(
            text="some text",
            results=results,
            verdict="FOUND IN webtext",
            sources=["webtext", "custom:internal_archive"],
            splits=["test"],
        )
        assert len(payload["results"]) == 2
        assert payload["results"][0]["present"] is True
        assert payload["results"][0]["first_match_record_index"] == 142
        assert payload["results"][1]["source"] == "custom:internal_archive"

    def test_negative_attestation_round_trips(self):
        bc = Blockchain(difficulty=1)
        chain_corpus_check(
            blockchain=bc, text="never seen text",
            results=self._sample_results(),
            verdict="NOT FOUND in any selected corpus.",
            sources=["webtext", "small-117M-k40"], splits=["test"],
        )
        # The block stores the hash of "never seen text". Verify by hashing.
        block = bc.chain[1]
        items = json.loads(block.data)
        recovered = json.loads(items[0])
        assert recovered["text_hash"] == sha256_hex("never seen text")
        assert recovered["verdict"].startswith("NOT FOUND")


class TestVerifyAgainstChain:
    def test_finds_matching_pair(self):
        bc = Blockchain(difficulty=1)
        chain_equilibrium_run(bc, "the fed raised rates", "by 25 bps", "m", _passing_report())
        chain_equilibrium_run(bc, "other prompt", "other response", "m", _passing_report())

        matches = verify_against_chain(bc, "the fed raised rates", "by 25 bps")
        assert len(matches) == 1
        assert matches[0]["payload"]["model_id"] == "m"

    def test_no_match_returns_empty(self):
        bc = Blockchain(difficulty=1)
        chain_equilibrium_run(bc, "p", "r", "m", _passing_report())
        assert verify_against_chain(bc, "different", "pair") == []

    def test_finds_multiple_matches(self):
        bc = Blockchain(difficulty=1)
        # Same prompt+response evaluated twice (e.g., two providers, two times)
        chain_equilibrium_run(bc, "p", "r", "claude", _passing_report())
        chain_equilibrium_run(bc, "p", "r", "ollama-llama3", _failing_report())
        matches = verify_against_chain(bc, "p", "r")
        assert len(matches) == 2
        assert {m["payload"]["model_id"] for m in matches} == {"claude", "ollama-llama3"}
