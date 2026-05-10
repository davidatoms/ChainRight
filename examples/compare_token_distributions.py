#!/usr/bin/env python3
"""Compare ChainRight tokenization views across human vs. GPT-2 generated text.

Loads N samples from `webtext` and from one or more model corpora in the
gpt-2-output-dataset, runs every tokenization view from chainright.tokenization
on each sample, and reports per-source statistics that should separate human
from model text:

    - mean and stddev token counts per view
    - type-token ratio (vocabulary richness) on the words view
    - sentence-length distribution
    - punctuation density

Usage:
    python examples/compare_token_distributions.py
    python examples/compare_token_distributions.py --n 500 --out report.json
    python examples/compare_token_distributions.py --models xl-1542M-k40 small-117M-k40
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Dict, List

from chainright.datasets import iter_texts
from chainright.tokenization import (
    tokenize_characters,
    tokenize_sentences,
    tokenize_whitespace,
    tokenize_words_and_punctuation,
)


def _is_punctuation(token: str) -> bool:
    return len(token) == 1 and not token.isalnum() and not token.isspace()


def summarize_source(source: str, split: str, n: int, data_dir: Path) -> Dict:
    char_counts: List[int] = []
    word_counts: List[int] = []
    sentence_counts: List[int] = []
    sentence_lengths: List[float] = []
    type_token_ratios: List[float] = []
    punct_densities: List[float] = []

    for text in iter_texts(source, split, data_dir=data_dir, n=n, min_length=200):
        chars = tokenize_characters(text).tokens
        words = tokenize_words_and_punctuation(text).tokens
        sentences = tokenize_sentences(text).tokens
        whitespace_tokens = tokenize_whitespace(text).tokens

        char_counts.append(len(chars))
        word_counts.append(len(words))
        sentence_counts.append(len(sentences))

        if sentences:
            mean_sentence_len = sum(len(s.split()) for s in sentences) / len(sentences)
            sentence_lengths.append(mean_sentence_len)

        if whitespace_tokens:
            unique = {t.lower() for t in whitespace_tokens}
            type_token_ratios.append(len(unique) / len(whitespace_tokens))

        if words:
            punct = sum(1 for t in words if _is_punctuation(t))
            punct_densities.append(punct / len(words))

    def stats(xs: List[float]) -> Dict[str, float]:
        if not xs:
            return {"n": 0}
        return {
            "n": len(xs),
            "mean": statistics.fmean(xs),
            "stdev": statistics.pstdev(xs) if len(xs) > 1 else 0.0,
            "min": min(xs),
            "max": max(xs),
        }

    return {
        "source": source,
        "split": split,
        "samples": len(char_counts),
        "characters": stats(char_counts),
        "words_and_punctuation": stats(word_counts),
        "sentences_per_doc": stats(sentence_counts),
        "mean_sentence_length_words": stats(sentence_lengths),
        "type_token_ratio": stats(type_token_ratios),
        "punctuation_density": stats(punct_densities),
    }


def diff_tables(rows: List[Dict]) -> Dict:
    """Side-by-side delta of each metric vs. webtext baseline."""
    if not rows:
        return {}
    baseline = next((r for r in rows if r["source"] == "webtext"), rows[0])

    metrics = [
        "characters", "words_and_punctuation", "sentences_per_doc",
        "mean_sentence_length_words", "type_token_ratio", "punctuation_density",
    ]
    table: Dict[str, Dict[str, float]] = {}
    for metric in metrics:
        table[metric] = {}
        base = baseline[metric].get("mean", 0.0)
        for row in rows:
            mean = row[metric].get("mean", 0.0)
            delta = mean - base
            pct = (delta / base * 100.0) if base else float("nan")
            table[metric][row["source"]] = {"mean": mean, "delta_vs_webtext": delta, "pct": pct}
    return table


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--split", default="test", choices=["train", "valid", "test"])
    parser.add_argument("--n", type=int, default=300, help="samples per source")
    parser.add_argument(
        "--models",
        nargs="+",
        default=["small-117M-k40", "xl-1542M-k40", "xl-1542M"],
        help="model sources to compare against webtext",
    )
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    sources = ["webtext"] + list(args.models)
    rows: List[Dict] = []
    for source in sources:
        print(f"Summarizing {source} (n={args.n}, split={args.split})...")
        rows.append(summarize_source(source, args.split, args.n, args.data_dir))

    report = {
        "split": args.split,
        "samples_per_source": args.n,
        "sources": rows,
        "diff_vs_webtext": diff_tables(rows),
    }

    payload = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
        print(f"\nWrote {args.out}")
    else:
        print()
        print(payload)

    print("\nKey deltas vs. webtext (mean):")
    diff = report["diff_vs_webtext"]
    for metric, by_source in diff.items():
        print(f"  {metric}:")
        for source, row in by_source.items():
            if source == "webtext":
                continue
            print(f"    {source:22s}  {row['mean']:.4f}   "
                  f"delta={row['delta_vs_webtext']:+.4f}  ({row['pct']:+.1f}%)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
