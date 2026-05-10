#!/usr/bin/env python3
"""Sweep equilibrium-test thresholds against the gpt-2-output-dataset triples.

For each clause that has a numeric threshold, run the test across N triples
at a range of threshold values and record the pass rate. The shape of the
resulting curve tells you whether the clause is carrying signal (steep
transition between pass and fail) or slack (flat curve, threshold doesn't
matter).

Outputs a JSON report and a small ASCII-table summary on stdout.

Usage:
    python examples/sweep_equilibrium_thresholds.py
    python examples/sweep_equilibrium_thresholds.py --n 200 --model xl-1542M-k40
    python examples/sweep_equilibrium_thresholds.py --out sweep.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

from chainright.datasets import iter_equilibrium_triples
from chainright.equilibrium import (
    jaccard,
    proportionality_test,
    semantic_stability_test,
    prompt_decomposition_test,
    word_count,
)


def _make_lookup_llm(text: str):
    return lambda _p, _t=text: _t


def sweep_proportionality(
    triples: List[Tuple[str, str, str]],
    thresholds: List[float],
) -> Dict[float, float]:
    out: Dict[float, float] = {}
    for tau in thresholds:
        passes = 0
        for prompt, _human, model in triples:
            llm = _make_lookup_llm(model)
            r = proportionality_test(llm, prompt, threshold=tau)
            if r.passes:
                passes += 1
        out[tau] = passes / len(triples) if triples else 0.0
    return out


def sweep_decomposition(
    triples: List[Tuple[str, str, str]],
    thresholds: List[float],
) -> Dict[float, float]:
    out: Dict[float, float] = {}
    for tau in thresholds:
        passes = 0
        evaluated = 0
        for prompt, _human, model in triples:
            sub = [s for s in prompt.split(". ") if s.strip()][:3]
            if not sub:
                continue
            llm = _make_lookup_llm(model)
            r = prompt_decomposition_test(llm, prompt, sub, threshold=tau)
            evaluated += 1
            if r.passes:
                passes += 1
        out[tau] = passes / evaluated if evaluated else 0.0
    return out


def sweep_stability(
    triples: List[Tuple[str, str, str]],
    thresholds: List[float],
    group_size: int = 3,
) -> Dict[float, float]:
    """Group consecutive triples and use their prompts as paraphrastic variants.

    This is a proxy: real paraphrastic variants are written by hand. Using
    consecutive prompts means the variants are about *different* topics, so
    we expect pass rates to be very low — the curve still shows where the
    threshold is most discriminating.
    """
    groups: List[List[Tuple[str, str, str]]] = []
    for i in range(0, len(triples) - group_size + 1, group_size):
        groups.append(triples[i:i + group_size])

    out: Dict[float, float] = {}
    for tau in thresholds:
        passes = 0
        for group in groups:
            variants = [g[0] for g in group]
            sample_completion = group[0][2]
            llm = _make_lookup_llm(sample_completion)
            r = semantic_stability_test(llm, variants, threshold=tau)
            if r.passes:
                passes += 1
        out[tau] = passes / len(groups) if groups else 0.0
    return out


def discriminating_threshold(curve: Dict[float, float]) -> Dict[str, float]:
    """Return the threshold where the pass rate transitions through 0.5.

    Also reports the slope around that point — large absolute slope means
    the clause is sensitive (good signal), small slope means it's flat
    (slack, threshold doesn't matter).
    """
    items = sorted(curve.items())
    if not items:
        return {"transition_threshold": float("nan"), "slope": 0.0}

    transition = items[-1][0] if items[-1][1] > 0.5 else items[0][0]
    for (t1, p1), (t2, p2) in zip(items, items[1:]):
        if (p1 - 0.5) * (p2 - 0.5) <= 0:
            transition = (t1 + t2) / 2.0
            slope = (p2 - p1) / (t2 - t1) if t2 != t1 else 0.0
            return {"transition_threshold": transition, "slope": slope}
    slope = (items[-1][1] - items[0][1]) / (items[-1][0] - items[0][0]) if items[-1][0] != items[0][0] else 0.0
    return {"transition_threshold": transition, "slope": slope}


def _ascii_curve(curve: Dict[float, float], width: int = 30) -> str:
    lines = []
    for tau, rate in sorted(curve.items()):
        bar = "#" * int(rate * width)
        lines.append(f"  tau={tau:>6.3f}  {rate:6.2%}  {bar}")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--model", default="small-117M-k40")
    parser.add_argument("--split", default="test", choices=["train", "valid", "test"])
    parser.add_argument("--k-words", type=int, default=30)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    print(f"Loading {args.n} triples from {args.model}.{args.split}...")
    triples = list(iter_equilibrium_triples(
        human_source="webtext",
        model_source=args.model,
        split=args.split,
        k_words=args.k_words,
        data_dir=args.data_dir,
        n=args.n,
    ))
    print(f"  loaded {len(triples)} triples\n")

    proportionality_thresholds = [1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 30.0, 50.0]
    stability_thresholds = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9]
    decomposition_thresholds = [0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7]

    print("Sweeping proportionality...")
    prop_curve = sweep_proportionality(triples, proportionality_thresholds)
    print(_ascii_curve(prop_curve))
    print()

    print("Sweeping decomposition...")
    decomp_curve = sweep_decomposition(triples, decomposition_thresholds)
    print(_ascii_curve(decomp_curve))
    print()

    print("Sweeping semantic stability...")
    stab_curve = sweep_stability(triples, stability_thresholds)
    print(_ascii_curve(stab_curve))
    print()

    report = {
        "config": {
            "n_triples": len(triples),
            "model": args.model,
            "split": args.split,
            "k_words_prompt": args.k_words,
        },
        "proportionality": {
            "curve": prop_curve,
            "discriminator": discriminating_threshold(prop_curve),
        },
        "decomposition": {
            "curve": decomp_curve,
            "discriminator": discriminating_threshold(decomp_curve),
        },
        "stability": {
            "curve": stab_curve,
            "discriminator": discriminating_threshold(stab_curve),
        },
    }

    print("Discriminator summary (transition threshold, slope at transition):")
    for clause in ("proportionality", "decomposition", "stability"):
        d = report[clause]["discriminator"]
        print(f"  {clause:18s}  tau*={d['transition_threshold']:.3f}  "
              f"slope={d['slope']:+.3f}")

    if args.out:
        # JSON keys must be strings.
        serializable = {
            **report,
            "proportionality": {**report["proportionality"], "curve": {str(k): v for k, v in prop_curve.items()}},
            "decomposition": {**report["decomposition"], "curve": {str(k): v for k, v in decomp_curve.items()}},
            "stability": {**report["stability"], "curve": {str(k): v for k, v in stab_curve.items()}},
        }
        args.out.write_text(json.dumps(serializable, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
