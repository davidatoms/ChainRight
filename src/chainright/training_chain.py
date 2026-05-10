"""Per-step training-trajectory logging into a ChainRight blockchain.

Each training step appends a block recording the batch data hashes, loss
delta, gradient summary, and resulting weight summary. The chain becomes
the auditable trajectory that TracIn-style attribution can walk back to
when answering "which training example most influenced this output."

Designed to add negligible overhead to a fine-tune loop:

    blockchain = Blockchain(difficulty=1)
    for step, (batch, labels) in enumerate(loader):
        loss_before = eval_loss(model, batch, labels)
        loss_after, grad_norm = train_step(model, opt, batch, labels)
        chain_training_step(
            blockchain,
            TrainingStepRecord(
                step_idx=step,
                phase="finetune",
                batch_data_hashes=[sha256_text(t) for t in batch_texts],
                loss_before=loss_before,
                loss_after=loss_after,
                grad_norm=grad_norm,
                learning_rate=opt.param_groups[0]["lr"],
            ),
            session_id=run_id,
        )

Lookup is by data hash, so a held-out output's top attributed training
example can be located in the chain in O(chain length).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from chainright.blockchain import Blockchain


def sha256_text(text: str) -> str:
    """SHA-256 hex of a UTF-8 encoded string. Used to hash training examples."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class TrainingStepRecord:
    """One step's worth of trajectory data, ready to be chained.

    Required fields capture the audit-critical signal (which examples were
    seen, what loss change happened, what the resulting weights summarize
    to). Optional fields enrich the audit but are not load-bearing.
    """
    step_idx: int
    phase: str  # "pretrain", "finetune", "rlhf", or any caller-defined label
    batch_data_hashes: List[str]
    loss_before: float
    loss_after: float
    grad_norm: float
    per_layer_delta_norms: Optional[Dict[str, float]] = None
    val_loss: Optional[float] = None
    learning_rate: Optional[float] = None
    weights_hash: Optional[str] = None
    optimizer_state_hash: Optional[str] = None
    timestamp: Optional[str] = None
    extra: Optional[Dict[str, Any]] = field(default=None)

    @property
    def loss_delta(self) -> float:
        return self.loss_after - self.loss_before

    @property
    def batch_size(self) -> int:
        return len(self.batch_data_hashes)


def build_step_payload(
    record: TrainingStepRecord,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble the JSON payload for one training step. Pure function."""
    payload: Dict[str, Any] = {
        "kind": "training_step",
        "session_id": session_id,
        "step_idx": record.step_idx,
        "phase": record.phase,
        "timestamp": record.timestamp or datetime.now(timezone.utc).isoformat(),
        "batch_data_hashes": list(record.batch_data_hashes),
        "batch_size": record.batch_size,
        "loss_before": record.loss_before,
        "loss_after": record.loss_after,
        "loss_delta": record.loss_delta,
        "grad_norm": record.grad_norm,
    }
    if record.per_layer_delta_norms is not None:
        payload["per_layer_delta_norms"] = dict(record.per_layer_delta_norms)
    if record.val_loss is not None:
        payload["val_loss"] = record.val_loss
    if record.learning_rate is not None:
        payload["learning_rate"] = record.learning_rate
    if record.weights_hash is not None:
        payload["weights_hash"] = record.weights_hash
    if record.optimizer_state_hash is not None:
        payload["optimizer_state_hash"] = record.optimizer_state_hash
    if record.extra:
        payload["extra"] = dict(record.extra)
    return payload


def chain_training_step(
    blockchain: Blockchain,
    record: TrainingStepRecord,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Append one training-step record to the blockchain.

    Returns block metadata: index, hash, and the serialized payload.
    """
    payload = build_step_payload(record, session_id=session_id)
    blockchain.add_data(json.dumps(payload, sort_keys=True))
    mined = blockchain.mine_pending_data()
    block = mined["block"]
    return {
        "block_index": block.index,
        "block_hash": block.hash,
        "payload": payload,
    }


def _iter_training_step_payloads(blockchain: Blockchain):
    """Yield (block, payload) for every training_step block in the chain."""
    for block in blockchain.chain[1:]:  # skip genesis
        try:
            items = json.loads(block.data)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(items, list):
            continue
        for item in items:
            payload = item if isinstance(item, dict) else None
            if payload is None and isinstance(item, str):
                try:
                    payload = json.loads(item)
                except json.JSONDecodeError:
                    continue
            if payload is not None and payload.get("kind") == "training_step":
                yield block, payload


def find_step_by_data_hash(
    blockchain: Blockchain,
    data_hash: str,
) -> List[Dict[str, Any]]:
    """Return every training-step block whose batch contained `data_hash`.

    Useful for "which training step(s) used this example?" queries during
    attribution. A given example may appear in multiple steps if it's
    seen across epochs.
    """
    matches: List[Dict[str, Any]] = []
    for block, payload in _iter_training_step_payloads(blockchain):
        if data_hash in payload.get("batch_data_hashes", []):
            matches.append({
                "block_index": block.index,
                "block_hash": block.hash,
                "payload": payload,
            })
    return matches


def find_steps_by_phase(
    blockchain: Blockchain,
    phase: str,
) -> List[Dict[str, Any]]:
    """Return every training-step block whose phase matches."""
    matches: List[Dict[str, Any]] = []
    for block, payload in _iter_training_step_payloads(blockchain):
        if payload.get("phase") == phase:
            matches.append({
                "block_index": block.index,
                "block_hash": block.hash,
                "payload": payload,
            })
    return matches


def chain_training_summary(blockchain: Blockchain) -> Dict[str, Any]:
    """Aggregate stats across every training_step block in the chain.

    Useful for a quick sanity check after a training run: total steps,
    final val_loss, phases observed, total examples seen, etc.
    """
    n_steps = 0
    phases: Dict[str, int] = {}
    final_val_loss: Optional[float] = None
    total_examples_seen = 0
    final_step: Optional[int] = None

    for _block, payload in _iter_training_step_payloads(blockchain):
        n_steps += 1
        phase = payload.get("phase", "unknown")
        phases[phase] = phases.get(phase, 0) + 1
        if payload.get("val_loss") is not None:
            final_val_loss = payload["val_loss"]
        total_examples_seen += payload.get("batch_size", 0)
        final_step = payload.get("step_idx", final_step)

    return {
        "n_training_step_blocks": n_steps,
        "phases": phases,
        "total_examples_seen": total_examples_seen,
        "final_step_idx": final_step,
        "final_val_loss": final_val_loss,
        "chain_length": len(blockchain.chain),
        "chain_valid": blockchain.is_chain_valid(),
    }
