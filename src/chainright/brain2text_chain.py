"""Two-layer letter→word chain for Brain2Text-style decoder outputs.

Letter events: one block per character recognition with predicted_class,
confidence, raw_signal_hash, and validity-per-NIST-dictionary.

Word events: one block per assembled word with letter_block_indices
linking back to composing letter events, plus corpus-membership result
(is the word a substring of the pretraining corpus?).

The two layers are linked through block-index pointers, so a regulator
walking a word block can verify it composes from the recorded letters,
and verify each letter against the dictionary id and signal hash.

See `notes/brain2text_letter_word_chain.md` for the full design.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from chainright.blockchain import Blockchain
from chainright.nist_dictionary import dictionary_id, is_valid_class


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Letter layer
# ---------------------------------------------------------------------------

@dataclass
class LetterEventRecord:
    """One per-character recognition event from a decoder.

    The `raw_signal_hash` is the cryptographic anchor — sha256 of whatever
    input window produced this character (a BCI signal slice, a handwritten-
    character image, an audio frame). If the source is unavailable, hash
    a session_id + time_index tuple as a degraded substitute.
    """
    predicted_class: str
    confidence: float
    raw_signal_hash: str
    timestamp: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


def chain_letter_event(
    blockchain: Blockchain,
    record: LetterEventRecord,
    nist_dictionary: Set[str],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Append a per-character recognition event to the chain.

    Returns block metadata plus the computed `valid` field. The block
    payload includes `validity_per_nist_dictionary` (computed by checking
    `record.predicted_class in nist_dictionary`) and `nist_class_set_id`
    (the deterministic hash of the dictionary).
    """
    valid = is_valid_class(record.predicted_class, nist_dictionary)
    payload: Dict[str, Any] = {
        "kind": "letter_event",
        "session_id": session_id,
        "timestamp": record.timestamp or _now_utc(),
        "predicted_class": record.predicted_class,
        "confidence": float(record.confidence),
        "raw_signal_hash": record.raw_signal_hash,
        "nist_class_set_id": dictionary_id(nist_dictionary),
        "validity_per_nist_dictionary": valid,
    }
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


# ---------------------------------------------------------------------------
# Word layer
# ---------------------------------------------------------------------------

@dataclass
class WordEventRecord:
    """One per-word assembly event linking back to its composing letters."""
    word_string: str
    letter_block_indices: List[int]
    confidence_min: Optional[float] = None
    confidence_mean: Optional[float] = None
    timestamp: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


def chain_word_event(
    blockchain: Blockchain,
    record: WordEventRecord,
    corpus_check_fn: Callable[[str], Dict[str, Any]],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Append a per-word assembly event with corpus-membership result.

    `corpus_check_fn(word) -> dict` is the validation oracle. Typically a
    closure around `chainright.datasets.iter_records` or `check_corpus.
    check_membership` configured for a specific corpus source. The result
    must contain at least the keys `present` (bool), `first_match_record_index`,
    `source`, and `split` — those are the fields embedded in the block.
    """
    corpus_result = corpus_check_fn(record.word_string)
    payload: Dict[str, Any] = {
        "kind": "word_event",
        "session_id": session_id,
        "timestamp": record.timestamp or _now_utc(),
        "word_string": record.word_string,
        "word_length": len(record.word_string),
        "letter_block_indices": list(record.letter_block_indices),
        "corpus_match": bool(corpus_result.get("present", False)),
        "corpus_first_match_record_index": corpus_result.get("first_match_record_index"),
        "corpus_source": corpus_result.get("source"),
        "corpus_split": corpus_result.get("split"),
    }
    if record.confidence_min is not None:
        payload["confidence_min"] = float(record.confidence_min)
    if record.confidence_mean is not None:
        payload["confidence_mean"] = float(record.confidence_mean)
    if record.extra:
        payload["extra"] = dict(record.extra)
    blockchain.add_data(json.dumps(payload, sort_keys=True))
    mined = blockchain.mine_pending_data()
    block = mined["block"]
    return {
        "block_index": block.index,
        "block_hash": block.hash,
        "payload": payload,
        "corpus_match": payload["corpus_match"],
    }


def assemble_word_record(
    letter_block_infos: List[Dict[str, Any]],
) -> WordEventRecord:
    """Build a `WordEventRecord` from the list of letter-event return values.

    `letter_block_infos` is a list of dicts as returned by
    `chain_letter_event` — each must contain `block_index` and a
    `payload` with `predicted_class` and `confidence`.
    """
    chars = [b["payload"]["predicted_class"] for b in letter_block_infos]
    indices = [b["block_index"] for b in letter_block_infos]
    confidences = [float(b["payload"]["confidence"]) for b in letter_block_infos]
    return WordEventRecord(
        word_string="".join(chars),
        letter_block_indices=indices,
        confidence_min=min(confidences) if confidences else None,
        confidence_mean=(sum(confidences) / len(confidences)) if confidences else None,
    )


# ---------------------------------------------------------------------------
# Session-level summary
# ---------------------------------------------------------------------------

def _iter_session_payloads(blockchain: Blockchain, session_id: Optional[str]):
    """Yield every payload dict whose session_id matches (or all if None)."""
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
            if not isinstance(payload, dict):
                continue
            if session_id is not None and payload.get("session_id") != session_id:
                continue
            yield payload


def session_summary(blockchain: Blockchain, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Aggregate stats for a Brain2Text session chain.

    If `session_id` is None, summarizes the entire chain. Otherwise filters
    to blocks tagged with that session.

    Returns counts of letter events, valid letters per the NIST dictionary,
    word events, corpus-validated words, and per-letter mean confidence.
    These are the numbers that feed the HB1-HB5 hypotheses in
    notes/brain2text_letter_word_chain.md.
    """
    letter_count = 0
    letter_valid = 0
    word_count = 0
    word_corpus_match = 0
    confidences: List[float] = []
    out_of_dict_chars: List[str] = []

    for payload in _iter_session_payloads(blockchain, session_id):
        kind = payload.get("kind")
        if kind == "letter_event":
            letter_count += 1
            if payload.get("validity_per_nist_dictionary"):
                letter_valid += 1
            else:
                ch = payload.get("predicted_class")
                if isinstance(ch, str):
                    out_of_dict_chars.append(ch)
            conf = payload.get("confidence")
            if isinstance(conf, (int, float)):
                confidences.append(float(conf))
        elif kind == "word_event":
            word_count += 1
            if payload.get("corpus_match"):
                word_corpus_match += 1

    return {
        "session_id": session_id,
        "letter_events": letter_count,
        "letter_valid_count": letter_valid,
        "letter_validity_rate": (letter_valid / letter_count) if letter_count > 0 else 0.0,
        "word_events": word_count,
        "word_corpus_match_count": word_corpus_match,
        "word_corpus_match_rate": (word_corpus_match / word_count) if word_count > 0 else 0.0,
        "mean_letter_confidence": (sum(confidences) / len(confidences)) if confidences else 0.0,
        "out_of_dict_chars_seen": sorted(set(out_of_dict_chars)),
    }
