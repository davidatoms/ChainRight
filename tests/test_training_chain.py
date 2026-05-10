"""Tests for chainright.training_chain — per-step trajectory logging."""

import pytest

from chainright.blockchain import Blockchain
from chainright.training_chain import (
    TrainingStepRecord,
    build_step_payload,
    chain_training_step,
    chain_training_summary,
    find_step_by_data_hash,
    find_steps_by_phase,
    sha256_text,
)


def _record(step_idx: int = 0, phase: str = "finetune", **kwargs) -> TrainingStepRecord:
    defaults = dict(
        step_idx=step_idx,
        phase=phase,
        batch_data_hashes=[sha256_text(f"example {step_idx}-a"),
                           sha256_text(f"example {step_idx}-b")],
        loss_before=2.5,
        loss_after=2.3,
        grad_norm=0.45,
    )
    defaults.update(kwargs)
    return TrainingStepRecord(**defaults)


class TestSha256Text:
    def test_deterministic(self):
        assert sha256_text("the fed raised rates") == sha256_text("the fed raised rates")

    def test_different_inputs(self):
        assert sha256_text("a") != sha256_text("b")

    def test_hex_format(self):
        h = sha256_text("anything")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestBuildStepPayload:
    def test_required_fields_present(self):
        payload = build_step_payload(_record(step_idx=42))
        assert payload["kind"] == "training_step"
        assert payload["step_idx"] == 42
        assert payload["phase"] == "finetune"
        assert payload["batch_size"] == 2
        assert payload["loss_delta"] == pytest.approx(-0.2)
        assert "timestamp" in payload

    def test_optional_fields_omitted_when_unset(self):
        payload = build_step_payload(_record())
        # These should not appear unless supplied:
        assert "val_loss" not in payload
        assert "learning_rate" not in payload
        assert "weights_hash" not in payload
        assert "per_layer_delta_norms" not in payload

    def test_optional_fields_included_when_set(self):
        payload = build_step_payload(_record(
            val_loss=1.8,
            learning_rate=5e-5,
            weights_hash="a" * 64,
            per_layer_delta_norms={"q_proj": 0.01, "v_proj": 0.02},
            optimizer_state_hash="b" * 64,
            extra={"seed": 42},
        ))
        assert payload["val_loss"] == 1.8
        assert payload["learning_rate"] == 5e-5
        assert payload["weights_hash"] == "a" * 64
        assert payload["per_layer_delta_norms"] == {"q_proj": 0.01, "v_proj": 0.02}
        assert payload["optimizer_state_hash"] == "b" * 64
        assert payload["extra"] == {"seed": 42}

    def test_session_id_propagates(self):
        payload = build_step_payload(_record(), session_id="run-001")
        assert payload["session_id"] == "run-001"


class TestChainTrainingStep:
    def test_appends_block(self):
        bc = Blockchain(difficulty=1)
        info = chain_training_step(bc, _record(step_idx=0))
        assert info["block_index"] == 1
        assert len(bc.chain) == 2

    def test_chain_remains_valid_across_many_steps(self):
        bc = Blockchain(difficulty=1)
        for step in range(20):
            chain_training_step(bc, _record(step_idx=step))
        assert bc.is_chain_valid()
        assert len(bc.chain) == 21  # genesis + 20 steps

    def test_payload_round_trips(self):
        import json
        bc = Blockchain(difficulty=1)
        chain_training_step(bc, _record(step_idx=7, learning_rate=1e-4))
        block = bc.chain[1]
        items = json.loads(block.data)
        payload = json.loads(items[0])
        assert payload["step_idx"] == 7
        assert payload["learning_rate"] == 1e-4


class TestFindStepByDataHash:
    def test_finds_single_step(self):
        bc = Blockchain(difficulty=1)
        target_hash = sha256_text("project alpha leak")
        chain_training_step(bc, _record(step_idx=0))
        chain_training_step(bc, TrainingStepRecord(
            step_idx=1, phase="finetune",
            batch_data_hashes=[target_hash, sha256_text("other")],
            loss_before=2.0, loss_after=1.9, grad_norm=0.3,
        ))
        chain_training_step(bc, _record(step_idx=2))

        matches = find_step_by_data_hash(bc, target_hash)
        assert len(matches) == 1
        assert matches[0]["payload"]["step_idx"] == 1

    def test_finds_across_epochs(self):
        bc = Blockchain(difficulty=1)
        target_hash = sha256_text("repeated example")
        # Same example seen in three different steps (3 epochs)
        for step in range(3):
            chain_training_step(bc, TrainingStepRecord(
                step_idx=step, phase="finetune",
                batch_data_hashes=[target_hash, sha256_text(f"other-{step}")],
                loss_before=2.0 - step * 0.1,
                loss_after=1.9 - step * 0.1,
                grad_norm=0.3,
            ))
        matches = find_step_by_data_hash(bc, target_hash)
        assert len(matches) == 3
        assert [m["payload"]["step_idx"] for m in matches] == [0, 1, 2]

    def test_no_match_returns_empty(self):
        bc = Blockchain(difficulty=1)
        chain_training_step(bc, _record())
        assert find_step_by_data_hash(bc, sha256_text("never seen")) == []


class TestFindStepsByPhase:
    def test_filters_by_phase(self):
        bc = Blockchain(difficulty=1)
        chain_training_step(bc, _record(step_idx=0, phase="pretrain"))
        chain_training_step(bc, _record(step_idx=1, phase="pretrain"))
        chain_training_step(bc, _record(step_idx=2, phase="finetune"))
        chain_training_step(bc, _record(step_idx=3, phase="rlhf"))

        pretrain = find_steps_by_phase(bc, "pretrain")
        finetune = find_steps_by_phase(bc, "finetune")
        rlhf = find_steps_by_phase(bc, "rlhf")
        assert len(pretrain) == 2
        assert len(finetune) == 1
        assert len(rlhf) == 1


class TestChainTrainingSummary:
    def test_summary_aggregates_correctly(self):
        bc = Blockchain(difficulty=1)
        for step in range(5):
            chain_training_step(bc, _record(
                step_idx=step,
                val_loss=2.0 - step * 0.1,
                learning_rate=5e-5,
            ))
        summary = chain_training_summary(bc)
        assert summary["n_training_step_blocks"] == 5
        assert summary["phases"] == {"finetune": 5}
        assert summary["total_examples_seen"] == 10  # 5 steps × batch=2
        assert summary["final_step_idx"] == 4
        assert summary["final_val_loss"] == pytest.approx(1.6)
        assert summary["chain_valid"] is True

    def test_empty_chain_summary(self):
        bc = Blockchain(difficulty=1)
        summary = chain_training_summary(bc)
        assert summary["n_training_step_blocks"] == 0
        assert summary["phases"] == {}
        assert summary["total_examples_seen"] == 0
        assert summary["final_step_idx"] is None
        assert summary["final_val_loss"] is None

    def test_summary_distinguishes_phases(self):
        bc = Blockchain(difficulty=1)
        for step in range(3):
            chain_training_step(bc, _record(step_idx=step, phase="pretrain"))
        for step in range(3, 5):
            chain_training_step(bc, _record(step_idx=step, phase="finetune"))
        summary = chain_training_summary(bc)
        assert summary["phases"] == {"pretrain": 3, "finetune": 2}
