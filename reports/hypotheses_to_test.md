# Hypotheses to test

Structured list of empirical claims the ChainRight framework generates,
organized under the **N vs NP** framing the paper draft reaches for in §1.4.
Each hypothesis carries a falsifier — a specific empirical condition that
would refute it. The point is to make the framework's claims discoverable
and contestable, not just defensible.

## The N vs NP framing as ground

For this document, define:

- **N** = the bounded resources used to *produce* a model: pretraining
  corpus size D, parameter count P, compute budget C, training time T.
  N grows polynomially with budget.
- **NP** = the combinatorial space the model *operates on* after
  deployment: prompts (V^N where V is vocab and N is context length),
  responses (V^M), users (U), and elapsed deployment time (T). NP grows
  exponentially with context length and linearly with deployment time.

The empirical content of every hypothesis below is whether some claim
about N maps usefully onto observable behavior in NP, or fails to. The
asymmetry between the two — bounded inspectable producer vs unbounded
non-inspectable user-facing surface — is the audit problem in one breath.

---

## H1 — Boolean signatures match TF-IDF detection

**Claim.** When the equilibrium harness is run with a real
prompt-sensitive LLM (rather than corpus lookup), the 8-bit Boolean
signatures from the equilibrium clauses approach the TF-IDF baseline
(89.6% on small-117M-k40, 82.4% on xl-1542M-k40) using only 8 bits per
sample.

**Currently observed.** 75.0% test accuracy in corpus mode, where 5 of
8 clauses are degenerate. Effectively a 2-bit detector
(time_cost + proportionality) carrying the signal.

**Test.** Re-run `examples/boolean_signatures.py` with `--llm-source
ollama` (Llama 3 8B) or `--llm-source huggingface` (Llama 3.2 1B via
circuit-tracer) on ≥500 triples per source. Train logistic regression
on signatures. Report test accuracy.

**Predicted result.** Test accuracy in [80%, 90%].

**Falsifier.** Test accuracy ≤ 75% with all 8 clauses active (no
better than corpus mode), or ≤ 60% (signal collapses).

**N vs NP relevance.** Tests whether the framework's N-side compress
(8 bits per sample) preserves NP-side discriminative information that
TF-IDF (10⁵ features per sample) extracts.

---

## H2 — Verifier cost dominates audit budget

**Claim.** The cost of running the equilibrium verifier on a (prompt,
response) pair, measured in seconds-of-typing-equivalent, is at least
an order of magnitude greater than the time the underlying LLM call
takes.

**Currently observed.** ~52.6 typing-equivalent seconds per triple
on small-117M-k40 corpus mode. LLM call time is ~0 in corpus mode (it's
a lookup), so the ratio is unmeasurable today.

**Test.** Measure both: typing cost via `cli.py --typing-test`, LLM
wall-clock call time via `chainright.llm_cli.LLMCli` against
Anthropic / Ollama / HuggingFace on the same prompt set. Compute the
ratio across providers.

**Predicted result.** Ratio in [10, 1000] for typical financial-services
prompts.

**Falsifier.** Ratio < 10 — verifier is fast enough that audit
deployment is cheap and the paper's regulatory cost argument
collapses.

**N vs NP relevance.** Tests whether verifier cost scales with N (small)
or with the human-side input cost (constant per call, independent of
N). The latter dominates is the framework's claim.

---

## H3 — Trained model retraces

**Claim.** A small (~125M–1B param) model trained from scratch on a
chained corpus admits retroactive output-to-training-example attribution
with per-output audit cost ≤ 5× the inference cost.

**Currently observed.** Composition validated component-wise — TracIn
works on small models, circuit-tracer works on small models, the chain
holds — but the composition has not been demonstrated end-to-end on a
trained model.

**Test.** LoRA fine-tune of GPT-2-small (124M) on 10K records from
gpt-2-output-dataset webtext slice. Log per-step trajectory into a
ChainRight blockchain. After training, for N=100 outputs: run
TracIn-style attribution; for each, walk the chain to identify the
top-1 contributing training example; verify the chain's recorded data
hash matches the data the influence function points to.

**Predicted result.** Top-1 attribution match rate ≥ 80%.
Per-output audit cost ≤ 5× inference cost.

**Falsifier.** Match rate < 50%, or audit cost > 100× inference.

**N vs NP relevance.** Tests whether building a known-N model collapses
the NP-side audit problem to an N-sized problem in practice, not just
in principle.

---

## H4 — Cross-firm wall violations are detectable in attribution

**Claim.** When a model is fine-tuned on data from two distinct sources
(analogous to two business units inside a financial firm), the
per-prompt attribution graph reveals which features came from which
source, allowing detection of cross-source feature mixing.

**Currently observed.** Hypothetical. The §1.4 paper concern.

**Test.** LoRA fine-tune a small model on data labeled
(source_A, source_B) — for example, source_A = SEC filings,
source_B = earnings call transcripts. Generate outputs from prompts
that should only require source_A features. Compute attribution.
Measure mean source_B contribution to source_A-only outputs.

**Predicted result.** Mean source_B contribution ≤ 5% under good wall
enforcement; ≥ 20% under shared-weight training without wall.

**Falsifier.** Indistinguishable contribution levels — attribution
cannot detect wall violations.

**N vs NP relevance.** Tests whether N-side attribution methods extend
to per-source feature isolation in NP-traversal. If they do, ChainRight
can audit Chinese walls; if they don't, the wall-violation claim
weakens.

---

## H5 — Negative attestation strengthens with corpus size

**Claim.** The information value of a clean-negative scan (text not
found in any of the configured corpora) grows with corpus size up to a
saturation point, beyond which adding more corpora doesn't reduce the
chance of a missed positive.

**Currently observed.** Three smoke-test runs against
gpt-2-output-dataset (250K records). One verbatim-match finding
(`xl-1542M` reproducing webtext). No systematic corpus-size sweep yet.

**Test.** Pick a fixed query set. Run `check_corpus.py` against
incrementally larger custom corpora (say, 10², 10³, 10⁴, 10⁵, 10⁶
records). For each size, measure the rate of clean-negative scans.
Look for the size at which the rate plateaus.

**Predicted result.** Plateau emerges around 10⁷–10⁸ documents — the
natural-language frequency cutoff where most unique 5-grams become
findable somewhere.

**Falsifier.** Rate continues to drop monotonically with no plateau —
absence-attestation never converges, the primitive is too weak in
practice.

**N vs NP relevance.** Tests whether absence-attestation about NP
(text not in any of these N corpora) becomes meaningful as N grows
past a threshold. If the threshold exists and is achievable, MNPI
verification is tractable; if it doesn't, the primitive is mostly
ceremonial.

---

## H6 — Trajectory-aware training improves efficiency

**Claim.** Training with chain-recorded per-step trajectory information
enables 2–10× improvement in compute-to-loss efficiency via
branch-and-merge or trajectory-aware curriculum.

**Currently observed.** Hypothetical. Published evidence supports the
2× end of the range (model soups) under restricted conditions.

**Test.** Run two parallel fine-tunes from the same starting checkpoint:
one with default SGD curriculum, one with branch-and-merge selecting
the best of K=8 short trajectories using chain-recorded val_loss.
Measure final task accuracy at fixed compute budget across multiple
seeds.

**Predicted result.** Branch-and-merge produces equal or better final
accuracy at the same compute, or matches baseline at 0.5× compute.

**Falsifier.** No improvement at 2× compute budget, or improvement
attributable to randomness rather than trajectory data (no consistent
ordering across seeds).

**N vs NP relevance.** Pure N-side claim — does N-side trajectory
information reduce N-side training cost. Does not require NP-side
behavior claims, so it can be tested in isolation from the rest of
the framework.

---

## H7 — Frontier-scale attribution is bounded by approximation, not framework

**Claim.** The output-to-training-example attribution achievable at
frontier scale (10¹²+ params, 10¹³+ tokens) is limited by the available
approximation methods (gradient hashing, datamodel sketches), not by
ChainRight's chain primitive. The chain at frontier scale records
~10⁻⁴ to 10⁻² of full influence-function precision, depending on the
proxy.

**Currently observed.** Inherited from published work. ChainRight does
not move the frontier; it records its outputs.

**Test.** Replicate published TracIn / datamodel benchmarks at
intermediate scale (1B params, 10⁹ tokens) — feasible on cloud rental.
Compute the precision-versus-cost frontier. Extrapolate to frontier
scale using the known scaling exponents.

**Predicted result.** Linear in compute, sublinear in coverage —
extrapolation to frontier gives the order-of-magnitude limit on
attribution precision available today.

**Falsifier.** Methods scale better than published claims (in which
case the framework can claim more), or worse (in which case
frontier-scale claims need tightening).

**N vs NP relevance.** Tests whether the gap between exact NP-traversal
and approximate NP-traversal is bridged by current methods.

---

## H8 — N-side audit cannot constrain NP-side behavior for closed models

**Claim.** For a closed-API frontier model, no analysis of the N-side
bounded resources (data corpus, parameter count, compute spent) can
predict per-prompt NP-side behavior with accuracy above the empirical
Boolean-signature detector run against the model's outputs.

**Currently observed.** Hypothetical. This is the framework's central
asymmetry claim.

**Test.** Compare two predictors of "did model X produce response R for
prompt P": (a) trained classifier on N-side metadata (model card,
parameter count, training data summary, tokenizer, license), (b)
8-bit Boolean signature from running the equilibrium harness on the
(P, R) pair. Use the same gpt-2-output-dataset triples for both.

**Predicted result.** (a) at chance (~50%); (b) at ≥75% (already
observed in corpus mode, expected higher with real LLM).

**Falsifier.** N-side metadata predictors approach (b)'s accuracy,
suggesting model behavior is constrained by N-side properties more
than the framework claims.

**N vs NP relevance.** Central asymmetry. If N-side analysis works,
ChainRight's positive contribution shrinks. If it doesn't, the
framework's structural argument (NP-side must be observed, not
inferred from N-side) is supported.

---

## H9 — SAT-style search converges on common prompts

**Claim.** For prompts whose responses pass equilibrium with realistic
threshold settings, SAT-style search finds a satisfying candidate
within typing-cost budget for ≥ 50% of attempts on the
gpt-2-output-dataset triples.

**Currently observed.** 1 of 5 triples accepted on initial prompt with
truncation generator and 300s budget; 4 of 5 UNSAT after exploring
all 7 truncations. Sample size too small to claim a rate.

**Test.** Run `solve_equilibrium` on 500 (prompt, response) triples
with realistic clause thresholds (proportionality τ=20, time_cost
baseline=600s, etc.) and a 300-second typing-cost budget. Measure
pass rate and average candidates examined to satisfaction.

**Predicted result.** Pass rate ≥ 50% at budget=300s. Mean candidates ≤ 5.

**Falsifier.** Pass rate < 20% at any feasible budget — search is
ineffective even with relaxed thresholds.

**N vs NP relevance.** Tests whether N-side prompt search (a polynomial
procedure with budget cap) can satisfy the NP-shaped equilibrium
formula on real data. If yes, the framework's adjudication primitive
is operational; if no, the SAT framing is structurally right but
practically hollow.

---

## How these hypotheses compose

Taken together, the hypotheses define the empirical content of the
framework's claims:

| Group | Hypotheses | What they establish |
|---|---|---|
| Audit cost economics | H2 | Per-call audit is expensive in the right way |
| Detection signal | H1, H8 | Equilibrium clauses encode separable signal |
| Trained-model claims | H3, H4, H6 | Chained provenance + attribution composes |
| Absence claims | H5 | Negative attestation has empirical content |
| Frontier-scale honesty | H7 | The framework is bounded by its inputs, not overclaiming |
| SAT shape | H9 | The CNF framing has practical traction |

Three groupings of effort:

- **Achievable in days on existing infrastructure** (H1, H2, H8, H9).
  These need a real-LLM run plus a couple of analysis scripts.
- **Achievable in weeks with new fine-tunes** (H3, H4, H5, H6). These
  need the chained-trajectory training pipeline plus targeted
  experiments.
- **Achievable in months at intermediate scale** (H7). Cloud rental,
  literature-grade benchmarks.

A successful resolution of any one of these advances the paper's
empirical case. A clean falsification of any one tightens what the
paper can claim. The list itself is the project's discoverable
surface — the contestable parts of the framework, made explicit so
they can be tested rather than assumed.

## What this list does *not* contain

The framework also makes ethical, legal, and policy claims that are
not amenable to direct empirical testing:

- That negative attestation chains have evidentiary weight in court.
- That regulator-side cost-per-call calculations should drive
  AI-deployment policy.
- That the substitution argument (small auditable models can replace
  frontier APIs in regulated activities) is sound TCO-wise.

These are claims for which the empirical results above are
*supporting evidence*, not direct tests. The hypotheses here are the
discoverable technical surface; the larger claims need engagement
with practitioners, regulators, and counsel — none of which a
hypothesis test on the gpt-2-output-dataset can substitute for.
