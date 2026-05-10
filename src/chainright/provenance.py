"""Provenance: append equilibrium runs to a ChainRight blockchain.

This is the integration-direction operation from notes/integration_versus_derivation.md
applied to the equilibrium verifier itself: every (prompt, model, response,
report) tuple gets hashed, summarized, and chained, so the audit trail of
how a regulator concluded "this passed" or "this failed" is itself
auditable.

The block payload stores:
    - session_id (caller-supplied)
    - timestamp (UTC ISO)
    - prompt_hash, response_hash (sha256 hex)
    - model_id (free-form string identifying the model)
    - at_equilibrium (bool)
    - failing_components (list[str])
    - total_typing_seconds (float, cost of running the verifier)
    - cps (the characters-per-second assumed for the cost calculation)

The full prompt and response strings are *not* stored on-chain — only
their hashes. That keeps the chain compact and lets a regulator verify
that a known prompt-response pair matches a recorded block without the
chain itself becoming a content store.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from chainright.blockchain import Blockchain
from chainright.equilibrium import DEFAULT_HUMAN_CPS, EquilibriumReport


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_attribution_graph(graph) -> str:
    """SHA-256 hex of a circuit-tracer Graph's serialized state.

    Uses torch.save into an in-memory buffer so the hash is deterministic
    given fixed transcoder weights and prompt. The serialized graph is not
    stored on-chain; only the hash is.
    """
    import io
    import torch  # local import; circuit-tracer/torch are heavy
    buf = io.BytesIO()
    torch.save(graph, buf)
    return hashlib.sha256(buf.getvalue()).hexdigest()


def summarize_attribution_graph(graph) -> Dict[str, Any]:
    """Pull the lightweight, audit-readable fields off a circuit-tracer Graph.

    Returns a JSON-serializable dict suitable for inclusion in a chain block
    payload. Heavy tensors (adjacency matrix, full feature lists) are *not*
    included — the full graph hash certifies them separately.

    Tolerant to graphs missing optional fields; safe to call on partially-
    populated graphs or on torch-tensor stand-ins used in tests.
    """
    summary: Dict[str, Any] = {}

    input_string = getattr(graph, "input_string", None)
    if input_string is not None:
        summary["input_string_length"] = len(input_string)

    input_tokens = getattr(graph, "input_tokens", None)
    if input_tokens is not None:
        try:
            summary["input_token_count"] = int(input_tokens.shape[0])
        except (AttributeError, IndexError):
            try:
                summary["input_token_count"] = len(input_tokens)
            except TypeError:
                pass

    vocab_size = getattr(graph, "vocab_size", None)
    if vocab_size is not None:
        summary["vocab_size"] = int(vocab_size)

    n_pos = getattr(graph, "n_pos", None)
    if n_pos is not None:
        summary["n_positions"] = int(n_pos)

    scan = getattr(graph, "scan", None)
    if scan is not None:
        summary["transcoder_scan"] = str(scan)

    active_features = getattr(graph, "active_features", None)
    if active_features is not None:
        try:
            summary["n_active_features"] = int(active_features.shape[0])
        except (AttributeError, IndexError):
            try:
                summary["n_active_features"] = len(active_features)
            except TypeError:
                pass

    cfg = getattr(graph, "cfg", None)
    if cfg is not None:
        for attr in ("model_name", "n_layers", "n_heads", "d_model"):
            value = getattr(cfg, attr, None)
            if value is not None:
                summary[f"cfg_{attr}"] = (
                    str(value) if isinstance(value, str) else int(value)
                )

    logit_targets = getattr(graph, "logit_targets", None)
    logit_probabilities = getattr(graph, "logit_probabilities", None)
    if logit_targets is not None and logit_probabilities is not None:
        try:
            probs = logit_probabilities.tolist() if hasattr(logit_probabilities, "tolist") else list(logit_probabilities)
            summary["logit_targets"] = [
                {
                    "vocab_idx": int(getattr(t, "vocab_idx", t) if not isinstance(t, int) else t),
                    "probability": float(p),
                }
                for t, p in zip(logit_targets, probs)
            ]
        except (AttributeError, TypeError, ValueError):
            pass

    return summary


def build_payload(
    prompt: str,
    response: str,
    model_id: str,
    report: EquilibriumReport,
    session_id: Optional[str] = None,
    cps: float = DEFAULT_HUMAN_CPS,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble the JSON payload that gets serialized into a block."""
    summary = report.cost_weighted_summary(cps=cps)
    payload: Dict[str, Any] = {
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_hash": sha256_hex(prompt),
        "response_hash": sha256_hex(response),
        "model_id": model_id,
        "at_equilibrium": summary["at_equilibrium"],
        "failing_components": summary["failing_components"],
        "total_typing_seconds": summary["total_typing_seconds"],
        "cps_assumed": summary["cps_assumed"],
    }
    if extra:
        payload["extra"] = extra
    return payload


def chain_equilibrium_run(
    blockchain: Blockchain,
    prompt: str,
    response: str,
    model_id: str,
    report: EquilibriumReport,
    session_id: Optional[str] = None,
    cps: float = DEFAULT_HUMAN_CPS,
    extra: Optional[Dict[str, Any]] = None,
    attribution_graph: Optional[Any] = None,
) -> Dict[str, Any]:
    """Append one equilibrium run to the blockchain and return block metadata.

    If `attribution_graph` is supplied (a circuit-tracer Graph object), its
    SHA-256 is added to the payload under `attribution_graph_hash`. The
    graph itself is not stored on-chain — only its hash. That way the chain
    can certify that a specific (prompt, response, graph) triple was
    produced, without bloating the chain with tensor data.
    """
    payload = build_payload(
        prompt=prompt,
        response=response,
        model_id=model_id,
        report=report,
        session_id=session_id,
        cps=cps,
        extra=extra,
    )
    if attribution_graph is not None:
        payload["attribution_graph_hash"] = hash_attribution_graph(attribution_graph)
        summary = summarize_attribution_graph(attribution_graph)
        if summary:
            payload["attribution_graph_summary"] = summary
    blockchain.add_data(json.dumps(payload, sort_keys=True))
    mined = blockchain.mine_pending_data()
    block = mined["block"]
    return {
        "block_index": block.index,
        "block_hash": block.hash,
        "payload": payload,
    }


def build_corpus_check_payload(
    text: str,
    results: List[Dict[str, Any]],
    verdict: str,
    sources: List[str],
    splits: List[str],
    mode: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble the JSON payload that gets serialized into a corpus-check block.

    Stores `text_hash` only — never the text itself — so the chain can be
    used to attest to the *absence* of non-public material from a known
    corpus set without storing the material itself on-chain.
    """
    payload: Dict[str, Any] = {
        "kind": "corpus_check",
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "text_hash": sha256_hex(text),
        "text_length": len(text),
        "sources": list(sources),
        "splits": list(splits),
        "verdict": verdict,
        "mode": mode or {},
        "results": [
            {
                "source": r.get("source"),
                "split": r.get("split"),
                "present": r.get("present"),
                "first_match_record_index": r.get("first_match_record_index"),
                "records_scanned": r.get("records_scanned"),
            }
            for r in results
        ],
    }
    if extra:
        payload["extra"] = extra
    return payload


def chain_corpus_check(
    blockchain: Blockchain,
    text: str,
    results: List[Dict[str, Any]],
    verdict: str,
    sources: List[str],
    splits: List[str],
    mode: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Append a corpus-membership-check result to the blockchain.

    This is the absence-attestation primitive: the chain block records that,
    at this timestamp, the supplied text was searched against this specific
    set of corpora, and these specific present/absent results were observed.
    The text itself is hashed, never stored, so non-public material remains
    private while the audit claim about it stays cryptographically anchored.
    """
    payload = build_corpus_check_payload(
        text=text, results=results, verdict=verdict,
        sources=sources, splits=splits, mode=mode,
        session_id=session_id, extra=extra,
    )
    blockchain.add_data(json.dumps(payload, sort_keys=True))
    mined = blockchain.mine_pending_data()
    block = mined["block"]
    return {
        "block_index": block.index,
        "block_hash": block.hash,
        "payload": payload,
    }


def chain_runs(
    blockchain: Blockchain,
    runs: List[Dict[str, Any]],
    session_id: Optional[str] = None,
    cps: float = DEFAULT_HUMAN_CPS,
) -> List[Dict[str, Any]]:
    """Chain a list of {prompt, response, model_id, report, [extra]} dicts in order."""
    out: List[Dict[str, Any]] = []
    for run in runs:
        out.append(
            chain_equilibrium_run(
                blockchain=blockchain,
                prompt=run["prompt"],
                response=run["response"],
                model_id=run["model_id"],
                report=run["report"],
                session_id=run.get("session_id", session_id),
                cps=cps,
                extra=run.get("extra"),
            )
        )
    return out


def _iter_payloads(block) -> List[Dict[str, Any]]:
    """Yield decoded payload dicts from a block's data field.

    `Blockchain.mine_pending_data` JSON-encodes a list of pending_data
    strings into block.data, so a block contains a list of payloads —
    even when that list has only one item.
    """
    try:
        items = json.loads(block.data)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(items, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in items:
        if isinstance(item, str):
            try:
                out.append(json.loads(item))
            except json.JSONDecodeError:
                continue
        elif isinstance(item, dict):
            out.append(item)
    return out


def verify_against_chain(
    blockchain: Blockchain,
    prompt: str,
    response: str,
) -> List[Dict[str, Any]]:
    """Return all blocks whose stored hashes match this (prompt, response).

    Useful for "did this exact pair ever pass equilibrium?" queries without
    requiring the chain to store full content.
    """
    p_hash = sha256_hex(prompt)
    r_hash = sha256_hex(response)
    matches: List[Dict[str, Any]] = []
    for block in blockchain.chain[1:]:  # skip genesis
        for payload in _iter_payloads(block):
            if payload.get("prompt_hash") == p_hash and payload.get("response_hash") == r_hash:
                matches.append({
                    "block_index": block.index,
                    "block_hash": block.hash,
                    "payload": payload,
                })
    return matches
