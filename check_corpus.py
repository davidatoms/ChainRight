#!/usr/bin/env python3
"""Check whether a piece of text appears in selected corpora.

For each (source, split) selected, streams the gpt-2-output-dataset records
and checks for substring membership. Prints a TRUE/FALSE table plus a
verdict line that compares matches across the human reference (webtext) and
the model-generated corpora.

Usage:
    python check_corpus.py "the fed raised rates by 25 basis points"
    python check_corpus.py --text "..." --sources webtext small-117M-k40
    echo "some text" | python check_corpus.py
    python check_corpus.py --text "..." --case-insensitive --json
    python check_corpus.py --text "..." --splits test valid
    python check_corpus.py --text "..." --ngram 3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Dict, Iterable, List, Optional, Tuple

from chainright.blockchain import Blockchain
from chainright.datasets import VALID_SOURCES, VALID_SPLITS, iter_records
from chainright.provenance import chain_corpus_check


def _word_tokenize(text: str) -> List[str]:
    return re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE)


def _ngrams(tokens: List[str], n: int) -> List[Tuple[str, ...]]:
    if n <= 0 or len(tokens) < n:
        return []
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def check_membership(
    text: str,
    source: str,
    split: str,
    data_dir: Optional[Path] = None,
    case_insensitive: bool = False,
) -> Dict:
    """Stream `(source, split)` and report whether `text` appears as a substring."""
    needle = text.lower() if case_insensitive else text
    first_match_id: Optional[str] = None
    first_match_record_index: Optional[int] = None
    records_scanned = 0
    t0 = perf_counter()

    for record in iter_records(source, split, data_dir=data_dir):
        records_scanned += 1
        haystack = record.get("text", "")
        if case_insensitive:
            haystack = haystack.lower()
        if needle and needle in haystack:
            first_match_id = str(record.get("id", ""))
            first_match_record_index = records_scanned
            break

    return {
        "source": source,
        "split": split,
        "present": first_match_id is not None,
        "first_match_id": first_match_id,
        "first_match_record_index": first_match_record_index,
        "records_scanned": records_scanned,
        "elapsed_seconds": perf_counter() - t0,
    }


def _iter_custom_texts(path: Path) -> Iterable[Tuple[str, str]]:
    """Yield (record_id, text) from a custom corpus path.

    Path semantics:
      - .jsonl file → each line is a JSON record; pulls the "text" field.
      - directory   → iterates every .txt file inside it (sorted).
      - .txt file or anything else → treated as a single document.
    """
    if path.is_dir():
        for child in sorted(path.iterdir()):
            if child.suffix.lower() == ".txt":
                try:
                    yield child.name, child.read_text(encoding="utf-8")
                except OSError:
                    continue
        return

    if path.suffix.lower() == ".jsonl":
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = record.get("text", "")
                if text:
                    yield str(record.get("id", line_no)), text
        return

    yield path.name, path.read_text(encoding="utf-8")


def check_custom_corpus(
    text: str,
    corpus_path: Path,
    case_insensitive: bool = False,
) -> Dict:
    """Substring membership check over an arbitrary user-supplied corpus."""
    needle = text.lower() if case_insensitive else text
    label = f"custom:{corpus_path.stem if corpus_path.is_file() else corpus_path.name}"

    first_match_id: Optional[str] = None
    first_match_record_index: Optional[int] = None
    records_scanned = 0
    t0 = perf_counter()

    for record_id, body in _iter_custom_texts(corpus_path):
        records_scanned += 1
        haystack = body.lower() if case_insensitive else body
        if needle and needle in haystack:
            first_match_id = record_id
            first_match_record_index = records_scanned
            break

    return {
        "source": label,
        "split": "custom",
        "present": first_match_id is not None,
        "first_match_id": first_match_id,
        "first_match_record_index": first_match_record_index,
        "records_scanned": records_scanned,
        "elapsed_seconds": perf_counter() - t0,
    }


def ngram_overlap(
    text: str,
    source: str,
    split: str,
    n: int,
    data_dir: Optional[Path] = None,
    case_insensitive: bool = False,
    max_records: Optional[int] = None,
) -> Dict:
    """Fraction of the input's n-grams that appear anywhere in `(source, split)`.

    Stops early as soon as every input n-gram has been observed at least once.
    Useful as a fuzzier signal than exact substring presence.
    """
    tokens = _word_tokenize(text.lower() if case_insensitive else text)
    input_ngrams = set(_ngrams(tokens, n))
    if not input_ngrams:
        return {
            "source": source, "split": split, "n": n,
            "input_ngrams": 0, "matched": 0, "overlap_fraction": 0.0,
            "records_scanned": 0,
        }

    seen: set = set()
    records_scanned = 0
    t0 = perf_counter()

    for record in iter_records(source, split, data_dir=data_dir):
        records_scanned += 1
        if max_records is not None and records_scanned > max_records:
            break
        haystack = record.get("text", "")
        haystack_tokens = _word_tokenize(haystack.lower() if case_insensitive else haystack)
        for ng in _ngrams(haystack_tokens, n):
            if ng in input_ngrams:
                seen.add(ng)
        if seen == input_ngrams:
            break

    return {
        "source": source,
        "split": split,
        "n": n,
        "input_ngrams": len(input_ngrams),
        "matched": len(seen),
        "overlap_fraction": len(seen) / len(input_ngrams),
        "records_scanned": records_scanned,
        "elapsed_seconds": perf_counter() - t0,
    }


def verdict(results: List[Dict]) -> str:
    in_webtext = any(r["source"] == "webtext" and r["present"] for r in results)
    model_hits = sorted({
        r["source"] for r in results
        if r["present"] and r["source"] != "webtext" and not r["source"].startswith("custom:")
    })
    custom_hits = sorted({
        r["source"] for r in results
        if r["present"] and r["source"].startswith("custom:")
    })

    if not in_webtext and not model_hits and not custom_hits:
        return "NOT FOUND in any selected corpus."

    pieces: List[str] = []
    if in_webtext and model_hits:
        pieces.append(
            f"BOTH webtext (human) and {len(model_hits)} model corpus(es): "
            f"{model_hits} (likely common phrase or memorized training data)"
        )
    elif in_webtext:
        pieces.append("WEBTEXT (human reference) only")
    elif model_hits:
        pieces.append(f"MODEL CORPORA only: {model_hits}")

    if custom_hits:
        pieces.append(f"custom corpora: {custom_hits}")

    return "FOUND IN " + "; also in ".join(pieces) + "."


def _format_present(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def _print_table(results: List[Dict], with_overlap: bool) -> None:
    if with_overlap:
        header = f"{'source':22s} {'split':6s} {'present':8s} {'overlap':>8s} {'first_match':>14s} {'scanned':>10s}"
    else:
        header = f"{'source':22s} {'split':6s} {'present':8s} {'first_match':>14s} {'scanned':>10s}"
    print(header)
    print("-" * len(header))
    for r in results:
        first_match = (
            f"#{r['first_match_record_index']}" if r["first_match_record_index"] is not None else "-"
        )
        if with_overlap:
            overlap = r.get("overlap_fraction")
            overlap_str = f"{overlap:.2%}" if overlap is not None else "-"
            print(
                f"{r['source']:22s} {r['split']:6s} {_format_present(r['present']):8s} "
                f"{overlap_str:>8s} {first_match:>14s} {r['records_scanned']:>10d}"
            )
        else:
            print(
                f"{r['source']:22s} {r['split']:6s} {_format_present(r['present']):8s} "
                f"{first_match:>14s} {r['records_scanned']:>10d}"
            )


def _read_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.input:
        return Path(args.input).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read().rstrip("\n")
    raise SystemExit(
        "No text supplied. Pass as positional argument, --text, --input <file>, or pipe via stdin."
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chainright-check",
        description="Check whether a piece of text appears in gpt-2-output-dataset corpora.",
    )
    p.add_argument(
        "text",
        nargs="?",
        help="Text to look for. Omit to use --text, --input, or stdin.",
    )
    p.add_argument("--text", dest="text", help="Text to look for (alias for positional).")
    p.add_argument("--input", "-i", help="Read query text from a file.")
    p.add_argument(
        "--sources",
        nargs="+",
        default=sorted(VALID_SOURCES),
        choices=sorted(VALID_SOURCES),
        help="Which corpora to check. Default: all 9.",
    )
    p.add_argument(
        "--splits",
        nargs="+",
        default=["test"],
        choices=sorted(VALID_SPLITS),
        help="Which splits to scan. Default: test only.",
    )
    p.add_argument("--data-dir", type=Path, default=None,
                   help="Path to gpt-2-output-dataset/data. Auto-detected if omitted.")
    p.add_argument("--case-insensitive", "-I", action="store_true")
    p.add_argument("--json", action="store_true",
                   help="Emit a JSON report instead of a human-readable table.")
    p.add_argument(
        "--ngram",
        type=int,
        default=0,
        help="If >0, also compute N-gram overlap fraction per corpus. "
             "Slower than substring presence but tolerant of minor edits.",
    )
    p.add_argument("--ngram-max-records", type=int, default=None,
                   help="Cap how many records the n-gram scan reads per corpus.")
    p.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Append the full run record (query, query_sha256, mode, results, "
             "verdict, runtime) as one JSON line to this file. Creates the "
             "file if missing; appends otherwise.",
    )
    p.add_argument(
        "--custom-corpus",
        type=Path,
        action="append",
        default=None,
        help="Additional corpus to check against. Path may be a .jsonl file "
             "(records with a 'text' field), a .txt file, or a directory of "
             ".txt files. May be repeated to scan multiple custom corpora.",
    )
    p.add_argument(
        "--chain-out",
        type=Path,
        default=None,
        help="Append the corpus-check result to this ChainRight blockchain "
             "(creates a new chain if the file doesn't exist). The chain "
             "stores only the text's sha256, never the text itself — suitable "
             "for attesting to the absence of non-public material from a "
             "known corpus set without exposing the material on-chain.",
    )
    p.add_argument(
        "--session-id",
        type=str,
        default=None,
        help="Optional session identifier stored in the chain block payload.",
    )
    return p


def _append_log_entry(log_path: Path, entry: Dict) -> None:
    """Append one JSON line to `log_path`. Creates parent dirs if needed."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main(argv: List[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    text = _read_text(args)
    if not text.strip():
        raise SystemExit("Empty query text.")

    total_start = perf_counter()

    results: List[Dict] = []
    for source in args.sources:
        for split in args.splits:
            r = check_membership(
                text=text, source=source, split=split,
                data_dir=args.data_dir,
                case_insensitive=args.case_insensitive,
            )
            if args.ngram > 0:
                ov = ngram_overlap(
                    text=text, source=source, split=split, n=args.ngram,
                    data_dir=args.data_dir,
                    case_insensitive=args.case_insensitive,
                    max_records=args.ngram_max_records,
                )
                r["overlap_fraction"] = ov["overlap_fraction"]
                r["overlap_matched"] = ov["matched"]
                r["overlap_input_ngrams"] = ov["input_ngrams"]
            results.append(r)

    for cc_path in (args.custom_corpus or []):
        if not cc_path.exists():
            print(f"Warning: custom corpus path not found, skipping: {cc_path}",
                  file=sys.stderr)
            continue
        results.append(
            check_custom_corpus(
                text=text, corpus_path=cc_path,
                case_insensitive=args.case_insensitive,
            )
        )

    total_runtime = perf_counter() - total_start

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": text,
        "query_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "mode": {
            "case_insensitive": args.case_insensitive,
            "ngram_n": args.ngram if args.ngram > 0 else None,
            "ngram_max_records": args.ngram_max_records,
        },
        "sources": list(args.sources),
        "splits": list(args.splits),
        "results": results,
        "verdict": verdict(results),
        "total_runtime_seconds": total_runtime,
    }

    if args.log:
        _append_log_entry(args.log, summary)

    chain_block_info: Optional[Dict] = None
    if args.chain_out:
        if args.chain_out.exists():
            blockchain = Blockchain.load_from_file(str(args.chain_out))
        else:
            blockchain = Blockchain(difficulty=1)
        chain_block_info = chain_corpus_check(
            blockchain=blockchain,
            text=text,
            results=results,
            verdict=summary["verdict"],
            sources=summary["sources"] + (
                [r["source"] for r in results if r["source"].startswith("custom:")]
            ),
            splits=summary["splits"],
            mode=summary["mode"],
            session_id=args.session_id,
            extra={"total_runtime_seconds": total_runtime},
        )
        blockchain.save_to_file(str(args.chain_out))
        summary["chain"] = {
            "path": str(args.chain_out),
            "block_index": chain_block_info["block_index"],
            "block_hash": chain_block_info["block_hash"],
            "chain_length": len(blockchain.chain),
        }

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    print(f"Query ({len(text)} chars): {text[:120]!r}{'...' if len(text) > 120 else ''}")
    if args.case_insensitive:
        print("Mode: case-insensitive substring match")
    else:
        print("Mode: case-sensitive substring match")
    if args.ngram > 0:
        print(f"Plus: {args.ngram}-gram overlap")
    print()
    _print_table(results, with_overlap=args.ngram > 0)
    print()
    print("Verdict:", summary["verdict"])
    print(f"Total runtime: {total_runtime:.2f}s")
    if args.log:
        print(f"Logged to: {args.log}")
    if chain_block_info is not None:
        print(f"Chained: block #{chain_block_info['block_index']} "
              f"hash={chain_block_info['block_hash'][:16]}... "
              f"({summary['chain']['chain_length']} blocks total in {args.chain_out})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
