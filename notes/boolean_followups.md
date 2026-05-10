# Followup moves on the Boolean equilibrium outputs

The equilibrium harness produces eight pass/fail bits per (prompt, response,
model) tuple, plus an aggregate `at_equilibrium`. Today most of the analysis
collapses these to that single aggregate bit. Five moves use the underlying
Boolean structure more aggressively. Listed in order matching the question
that prompted this note ("optimization techniques for inputs, or testing a
few thresholds"); (1) and (2) answer it directly, (3)–(5) are cheap
adjacent moves on the same Boolean outputs.

## 1. 2D threshold grid

`examples/sweep_equilibrium_thresholds.py` varies one threshold at a time.
A joint sweep of (proportionality_τ × decomposition_τ), or any other pair,
produces a 2D heatmap of equilibrium pass rate.

- Reveals clause interactions: does relaxing one threshold change the
  optimal value of another?
- The Pareto frontier of (τ_A, τ_B) is the set of pairs that no relaxation
  strictly improves.
- Output: a heatmap PNG plus a JSON of the grid. ~1 hour to build.

## 2. Optimize toward arbitrary Boolean targets

Extend `solve_equilibrium` so the target is any 8-bit pattern, not just
(1,1,1,1,1,1,1,1). Lets the harness answer "find prompts that pass clauses
1, 2, 3 but fail 4" — useful for regulatory carve-outs where some clauses
are mandatory and others advisory.

- Same SAT-style search, different acceptance predicate.
- Adds a `target_pattern: Tuple[bool, ...]` parameter.
- ~30 lines on top of the existing solver.

## 3. K-of-8 distribution

Score each triple by *how many* clauses pass (0–8) instead of just
`at_equilibrium`. Histogram across the gpt-2-output-dataset triples.

- Tells you whether triples cleanly all-pass or all-fail, or cluster at
  intermediate K.
- Drives the regulatory choice between "all 8" and "at least 6 of 8" as
  the equilibrium floor.
- Output: a histogram + the per-K stats (mean cost, mean fail mode).

## 4. Boolean signature per corpus

Extract the 8-bit pattern (b₁, b₂, …, b₈) per triple. Count distinct
patterns per source. Compare distributions across `webtext`,
`small-117M-k40`, `xl-1542M-k40`, etc.

- If the patterns differ between human and model corpora, the equilibrium
  clause outputs are themselves a detector.
- Head-to-head against the TF-IDF baseline (89% / 82% on small / xl) using
  *only* the eight Boolean values.
- Paper-worthy if the comparison is anywhere near baseline: "the
  equilibrium framework's pass/fail outputs encode the same signal as a
  trained detector, with full per-clause interpretability."

## 5. Clause redundancy

On the truth table observed in (4), check which clauses always co-pass or
co-fail across the corpus. Quine-McCluskey reduces the 8-clause CNF to its
minimum equivalent.

- Finding: "in practice, the 8 clauses collapse to N actually-distinct
  discriminators on real data."
- Tells you which clauses are doing work and which are slack on this
  dataset.

## Recommended order

(4) is the most paper-worthy single move because it gives a head-to-head
with the TF-IDF detector using only Boolean signals — and Boolean signals
are auditable in a way TF-IDF features aren't.

(3) is a free byproduct of doing (4): once you have the 8-bit signature
per triple, the K-of-8 distribution falls out by counting bits.

(1) and (5) are the analytical follow-ons that tell you *why* the
signatures look the way they do.

(2) is a tool for the next paper, not this one — it generalizes the
solver but doesn't add empirical findings on the existing corpus.
