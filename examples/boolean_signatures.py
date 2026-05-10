#!/usr/bin/env python3
"""Boolean signatures per corpus — equilibrium clauses as a detector.

For each triple drawn from the gpt-2-output-dataset, run all 8 equilibrium
clauses and capture their .passes outputs as an 8-bit signature. Compare
signature distributions across:

    webtext              (human; response is a different webtext sample so
                          ground-truth comparisons are non-trivial)
    small-117M-k40       (model)
    xl-1542M-k40         (model)
    xl-1542M             (model, no top-K)

Then train a logistic regression on the 8 Boolean features (human=0 vs
model=1) and compare accuracy to the TF-IDF baseline (89.61% / 82.40% on
small / xl at n_train=10K).

Usage:
    python examples/boolean_signatures.py
    python examples/boolean_signatures.py --n 500 --out signatures.json
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from chainright.datasets import (
    iter_equilibrium_triples,
    iter_texts,
)
from chainright.equilibrium import (
    compression_test,
    expert_agreement_test,
    ground_truth_score,
    prompt_decomposition_test,
    proportionality_test,
    provider_comparison_test,
    semantic_stability_test,
    time_cost_test,
    verifiability_iteration_test,
)
from chainright.llm_adapters import static_corpus_llm


CLAUSE_NAMES = (
    "compression",
    "proportionality",
    "time_cost",
    "stability",
    "decomposition",
    "expert",
    "providers",
    "verifiability",
)


def compute_signature(
    prompt: str,
    response: str,
    ground_truth: str,
    *,
    proportionality_threshold: float = 8.0,
    time_cost_baseline_seconds: float = 300.0,
    verification_seconds: float = 15.0,
    stability_threshold: float = 0.6,
    decomposition_threshold: float = 0.4,
    score_floor: float = 0.5,
    verifiability_floor: float = 0.5,
    expert_rating: float = 4.0,
    expert_minimum: float = 3.0,
    max_rounds: int = 3,
) -> Tuple[bool, ...]:
    """Run all 8 clauses and return their .passes as a tuple of bools."""
    response_llm = static_corpus_llm(response)

    compressed_prompt = " ".join(prompt.split()[:8])
    sub_prompts = [s.strip() for s in prompt.split(". ") if s.strip()][:3]
    variants = [prompt, prompt + " (rephrased)", "Tell me: " + prompt]

    c1 = compression_test(response_llm, prompt, compressed_prompt, ground_truth).passes
    c2 = proportionality_test(response_llm, prompt, threshold=proportionality_threshold).passes
    c3 = time_cost_test(
        prompt=prompt, response=response,
        expert_baseline_seconds=time_cost_baseline_seconds,
        verification_seconds=verification_seconds,
    ).passes
    c4 = semantic_stability_test(response_llm, variants, threshold=stability_threshold).passes
    c5 = (
        prompt_decomposition_test(response_llm, prompt, sub_prompts,
                                  threshold=decomposition_threshold).passes
        if sub_prompts else True
    )
    c6 = expert_agreement_test(prompt, "auto", rating=expert_rating,
                               minimum=expert_minimum).passes
    c7 = provider_comparison_test(
        {"corpus": response_llm}, prompt, ground_truth, score_floor=score_floor,
    ).passes

    def verifier(r: str, gt: str = ground_truth) -> bool:
        return ground_truth_score(r, gt) >= verifiability_floor

    c8 = verifiability_iteration_test(
        llm=response_llm,
        initial_prompt=prompt,
        verifier=verifier,
        refine=lambda p, _r: p,
        max_rounds=max_rounds,
    ).accepted

    return (c1, c2, c3, c4, c5, c6, c7, c8)


def collect_signatures(
    sources: List[str],
    n: int,
    split: str,
    k_words: int,
    data_dir: Path,
) -> Dict[str, List[Tuple[bool, ...]]]:
    """For each source, build N triples and compute their 8-bit signatures.

    For source 'webtext', response is taken from a *different* webtext record
    (offset+1) so the response/ground-truth Jaccard isn't trivially 1.0.
    For model sources, response is the model record at the same index as the
    webtext prompt; ground truth stays the human continuation.
    """
    out: Dict[str, List[Tuple[bool, ...]]] = {s: [] for s in sources}

    # Pre-load webtext continuations once for both the GT axis and the
    # shifted-human-response axis.
    webtext_records = list(iter_equilibrium_triples(
        human_source="webtext",
        model_source="webtext",  # placeholder; we'll override below
        split=split,
        k_words=k_words,
        data_dir=data_dir,
        n=n + 1,  # +1 to allow the offset-by-one shuffle
    ))
    if len(webtext_records) < 2:
        raise SystemExit("Need at least 2 webtext records to build human signatures.")

    for source in sources:
        if source == "webtext":
            for i in range(min(n, len(webtext_records) - 1)):
                prompt, human_gt, _ = webtext_records[i]
                _, shifted_response, _ = webtext_records[(i + 1) % len(webtext_records)]
                if not shifted_response:
                    continue
                sig = compute_signature(prompt, shifted_response, human_gt)
                out[source].append(sig)
        else:
            triples = list(iter_equilibrium_triples(
                human_source="webtext",
                model_source=source,
                split=split,
                k_words=k_words,
                data_dir=data_dir,
                n=n,
            ))
            for prompt, human_gt, model_response in triples:
                sig = compute_signature(prompt, model_response, human_gt)
                out[source].append(sig)
    return out


def per_clause_pass_rate(sigs: List[Tuple[bool, ...]]) -> List[float]:
    if not sigs:
        return [0.0] * 8
    arr = np.array(sigs, dtype=int)
    return arr.mean(axis=0).tolist()


def k_of_8_distribution(sigs: List[Tuple[bool, ...]]) -> Dict[int, int]:
    counts: Dict[int, int] = {k: 0 for k in range(9)}
    for sig in sigs:
        counts[sum(sig)] += 1
    return counts


def signature_frequencies(sigs: List[Tuple[bool, ...]]) -> Counter:
    return Counter(tuple(int(b) for b in sig) for sig in sigs)


def train_classifier(
    signatures_by_source: Dict[str, List[Tuple[bool, ...]]],
    seed: int = 42,
) -> Dict:
    """Binary classifier: human (webtext) vs model (any other source)."""
    X: List[List[int]] = []
    y: List[int] = []
    for source, sigs in signatures_by_source.items():
        label = 0 if source == "webtext" else 1
        for sig in sigs:
            X.append([int(b) for b in sig])
            y.append(label)

    X_arr = np.array(X)
    y_arr = np.array(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X_arr, y_arr, test_size=0.3, random_state=seed, stratify=y_arr,
    )
    clf = LogisticRegression(max_iter=1000)
    clf.fit(X_train, y_train)
    train_acc = clf.score(X_train, y_train) * 100.0
    test_acc = clf.score(X_test, y_test) * 100.0

    # Coefficients per clause tell us which Booleans the classifier leans on.
    coef_by_clause = dict(zip(CLAUSE_NAMES, clf.coef_[0].tolist()))
    return {
        "train_accuracy": train_acc,
        "test_accuracy": test_acc,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "coefficients_per_clause": coef_by_clause,
        "intercept": float(clf.intercept_[0]),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--n", type=int, default=500,
                        help="triples per source")
    parser.add_argument("--split", default="test",
                        choices=["train", "valid", "test"])
    parser.add_argument("--k-words", type=int, default=30)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["webtext", "small-117M-k40", "xl-1542M-k40", "xl-1542M"],
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    print(f"Building signatures for {args.sources} (n={args.n} per source)...")
    sigs_by_source = collect_signatures(
        sources=args.sources, n=args.n, split=args.split,
        k_words=args.k_words, data_dir=args.data_dir,
    )

    print("\n=== Per-clause pass rates ===")
    print(f"  {'source':22s}  " + "  ".join(f"{c[:8]:>8s}" for c in CLAUSE_NAMES))
    for source in args.sources:
        rates = per_clause_pass_rate(sigs_by_source[source])
        print(f"  {source:22s}  " + "  ".join(f"{r:>8.2%}" for r in rates))

    print("\n=== K-of-8 distribution (count of triples passing exactly K clauses) ===")
    print(f"  {'source':22s}  " + "  ".join(f"K={k}" for k in range(9)))
    for source in args.sources:
        d = k_of_8_distribution(sigs_by_source[source])
        n = max(sum(d.values()), 1)
        print(f"  {source:22s}  " + "  ".join(f"{d[k]/n:>4.0%}" for k in range(9)))

    print("\n=== Top-5 signatures per source (b1..b8) ===")
    for source in args.sources:
        freq = signature_frequencies(sigs_by_source[source])
        total = sum(freq.values())
        print(f"  {source}:")
        for sig, count in freq.most_common(5):
            sig_str = "".join(str(b) for b in sig)
            print(f"    {sig_str}  count={count:4d}  ({count/total:>5.1%})")

    print("\n=== Logistic regression: human (webtext) vs model ===")
    cls_report = train_classifier(sigs_by_source, seed=args.seed)
    print(f"  Train accuracy:   {cls_report['train_accuracy']:.2f}%")
    print(f"  Test accuracy:    {cls_report['test_accuracy']:.2f}%")
    print(f"  N train / test:   {cls_report['n_train']} / {cls_report['n_test']}")
    print(f"  TF-IDF baseline (small-117M-k40, n_train=10K): 89.61%")
    print(f"  TF-IDF baseline (xl-1542M-k40, n_train=10K):   82.40%")
    print(f"  Coefficient per clause (positive => predicts model):")
    for clause, coef in cls_report["coefficients_per_clause"].items():
        print(f"    {clause:18s}  {coef:+.3f}")

    if args.out:
        report = {
            "config": {
                "n_per_source": args.n,
                "split": args.split,
                "k_words": args.k_words,
                "sources": args.sources,
            },
            "per_clause_pass_rate": {
                s: dict(zip(CLAUSE_NAMES, per_clause_pass_rate(sigs_by_source[s])))
                for s in args.sources
            },
            "k_of_8_distribution": {
                s: {str(k): v for k, v in k_of_8_distribution(sigs_by_source[s]).items()}
                for s in args.sources
            },
            "top_signatures": {
                s: [
                    {"signature": "".join(str(b) for b in sig), "count": count}
                    for sig, count in signature_frequencies(sigs_by_source[s]).most_common(10)
                ]
                for s in args.sources
            },
            "classifier": cls_report,
        }
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
