"""Phoneme-layer chain — per-frame phoneme recognition events.

Each block records one prediction from a phoneme decoder (typically a
CTC-trained RNN with N-class softmax output, where N ~ 40-41 for English
ARPABET decoders). The phoneme set used at recognition time is hashed
and stored in every block, so an auditor can verify exactly which
inventory was applied.

This is the bottom layer for BCI / speech / phonological audit pipelines.
A higher word layer (a future `phoneme_word_chain.py`) would collapse
the phoneme stream into per-word phoneme sequences and validate those
sequences against a phonemized pretraining corpus.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from chainright.blockchain import Blockchain
from chainright.phoneme.phoneme_dictionary import is_valid_phoneme, phoneme_set_id


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PhonemeEventRecord:
    """One per-frame phoneme-recognition event from a decoder.

    `raw_signal_hash` is the cryptographic anchor — sha256 of whatever
    neural / audio / feature window produced this frame. If the source
    is unavailable, hash a (session_id, frame_index) tuple as a degraded
    substitute.
    """
    predicted_phoneme: str
    confidence: float
    raw_signal_hash: str
    frame_index: Optional[int] = None
    timestamp: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


def chain_phoneme_event(
    blockchain: Blockchain,
    record: PhonemeEventRecord,
    phoneme_set: Set[str],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Append a per-frame phoneme-recognition event to the chain.

    Returns block metadata plus the computed `valid` field. The block
    payload includes `validity_per_phoneme_set` (computed against
    `phoneme_set`) and `phoneme_set_id` (the deterministic hash of the
    inventory used).
    """
    valid = is_valid_phoneme(record.predicted_phoneme, phoneme_set)
    payload: Dict[str, Any] = {
        "kind": "phoneme_event",
        "session_id": session_id,
        "timestamp": record.timestamp or _now_utc(),
        "predicted_phoneme": record.predicted_phoneme,
        "confidence": float(record.confidence),
        "raw_signal_hash": record.raw_signal_hash,
        "phoneme_set_id": phoneme_set_id(phoneme_set),
        "validity_per_phoneme_set": valid,
    }
    if record.frame_index is not None:
        payload["frame_index"] = int(record.frame_index)
    if record.extra:
        payload["extra"] = dict(record.extra)
    blockchain.add_data(json.dumps(payload, sort_keys=True))
    mined = blockchain.mine_pending_data()
    block = mined["block"]
    return {
        "block_index": block.index,
        "block_hash": block.hash,
        "payload": payload,
        "valid": valid,
    }


def phoneme_session_summary(blockchain: Blockchain, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Aggregate stats for a phoneme-layer session.

    Counts phoneme events, valid-per-inventory events, out-of-set
    phonemes observed, and mean confidence. The output mirrors the
    letter chain's `session_summary` so downstream tools can treat
    both layers uniformly.
    """
    n_phonemes = 0
    n_valid = 0
    confidences: List[float] = []
    out_of_set: List[str] = []

    for block in blockchain.chain[1:]:
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
            if not isinstance(payload, dict):
                continue
            if session_id is not None and payload.get("session_id") != session_id:
                continue
            if payload.get("kind") != "phoneme_event":
                continue

            n_phonemes += 1
            if payload.get("validity_per_phoneme_set"):
                n_valid += 1
            else:
                p = payload.get("predicted_phoneme")
                if isinstance(p, str):
                    out_of_set.append(p)
            conf = payload.get("confidence")
            if isinstance(conf, (int, float)):
                confidences.append(float(conf))

    return {
        "session_id": session_id,
        "phoneme_events": n_phonemes,
        "phoneme_valid_count": n_valid,
        "phoneme_validity_rate": (n_valid / n_phonemes) if n_phonemes > 0 else 0.0,
        "mean_phoneme_confidence": (sum(confidences) / len(confidences)) if confidences else 0.0,
        "out_of_set_phonemes_seen": sorted(set(out_of_set)),
    }
