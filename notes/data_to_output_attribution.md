# Output-to-data attribution: the fourth direction

The first three notes argued what an audit of a closed-API frontier model
*cannot* be:

- `integration_versus_derivation.md` — training is the derivative; the
  trajectory is gone; the integral is what ChainRight maintains.
- `equilibrium_as_sat.md` — the verifier is SAT-shaped but carries a
  ~10⁶ human-typing constant, so audit cost dominates audit speed.
- `training_vs_inference_combinatorics.md` — the inference space (V^N)
  is exponentially larger than any training corpus, so sample-based
  audit cannot scale.

This fourth note argues what an audit of a *non-closed* model — one
trained with chained data and logged trajectory — *can* be: a
retroactive map from any output back to the training data, the
training phase, and the inference circuit that produced it.

## The composition

Three established research lines, composed:

1. **Influence functions / TracIn / datamodels.** Output-to-training-
   example attribution at small-model scale. Given a model output
   and a small training corpus, rank which training examples most
   influenced the output. Published; well-validated up to ~1B params
   and ~10⁵ training examples.

2. **Mechanistic attribution (circuit-tracer).** Per-prompt feature
   attribution at inference time. Given a prompt and a model with
   transcoders, compute which transcoder features most contributed
   to each output logit. Published 2025 (Ameisen et al., Lindsey
   et al.); already wired into our adapter stack.

3. **Chained trajectory (ChainRight).** Cryptographically chained
   ledger that records, per training step, the data hash, gradient
   summary, loss, and resulting weight summary; per inference call,
   the prompt, response, and attribution graph hash.

None of these is novel on its own. The composition is.

## What the composition gives you

For any model output, in principle:

1. Run an attribution method on the output → ranked list of
   contributing training examples (TracIn) and ranked list of
   contributing transcoder features (circuit-tracer).
2. For each contributing training example, walk the chain backward
   to find the block that recorded its inclusion in training.
3. Each chain block has a phase label — pretraining batch, fine-tune
   batch, RLHF reward step. The phase tells you whether the
   attributed influence came from pretraining, fine-tuning, or
   post-training reward shaping.
4. For each contributing transcoder feature, the chain has the
   feature's first-emergence step (when it first activated above a
   threshold during training).
5. The intersection of (data, feature) trace gives a per-output
   audit: *"this output was produced by these features, which
   emerged during this training phase, on these training batches,
   whose data hashes are these."*

This is the first audit primitive that crosses from inference back
to training in a single chain.

## What it doesn't give you

- **Bit-exact training replay.** That requires storing the full
  weights and optimizer state per step, which is size-prohibitive at
  any non-trivial scale. The chain certifies the trajectory was
  *consistent with* what was recorded, not bit-identical.
- **Frontier-scale attribution.** At 10¹²+ parameters and 10¹³+
  training tokens, exact influence-function computation is
  intractable (~10²⁵ FLOPs per query). Approximation via
  gradient-similarity hashing or datamodel sketches is the published
  frontier; ChainRight inherits whatever rigor those proxy methods
  can offer.
- **Causal interpretation.** The chain shows correlation between
  training data and output features. Causal claims require
  intervention — re-training without the suspect data, or
  feature-clamping during inference. Both are doable but expensive.

## Connection to the N vs NP intuition

The §1.4 framing in the underlying paper draft reaches for N vs NP.
Each of the previous three notes argued why N-side audit (inspecting
bounded resources) fails to constrain NP-side behavior (combinatorial
inference space). This note argues the symmetric path:

If you build the NP-side trajectory yourself — every training step
and every inference call gets chained — then the audit operates
entirely within the N-side traversal. The exponential inference
space is irrelevant because you only ever reason about the points
the trajectory actually visited.

Put differently: ChainRight does not reduce the size of the NP-space.
It bypasses the size of the NP-space by only ever auditing the
trajectory, a subset of the space whose size is linear in time × users
rather than exponential in context length.

## Tractable scope on consumer hardware

The 3070 Ti / 64 GB workstation is sufficient for:

- 100M–1B param model
- 10⁴–10⁵ fine-tune examples
- Per-step chain entry of ~1–2 KB
- Influence-function attribution: O(model_size × n_examples) per
  query, minutes per output for a 350M model on 50K examples

The full pipeline could be demonstrated as a paper artifact in
weeks, not months. The bottleneck is engineering effort, not compute.

## What this turns into for the paper

> A model trained with chained data provenance and per-step
> trajectory logging admits retroactive output-to-data attribution.
> Given any output: (a) the training examples whose inclusion most
> influenced the output, (b) the training phase that introduced that
> influence, and (c) whether any output traces back to data that
> should have been excluded — all from the chain, without re-running
> training and without accessing the model weights at audit time.

This is the project's positive contribution. Not "audit closed
frontier models" — which the first three notes argue is structurally
impossible — but "build a small auditable model whose audit
defensibility is the value proposition." The first three notes
argue the negative case; this fourth note argues the positive case;
together they form the four legs of the framework's table.

## Why "small and verifiable" is competitive, not consolation

The substitution argument from `reports/potential_impact_in_financial_markets.md`
turns on this note. A frontier API has unbounded inference space and
no per-call audit. A chained-provenance small model has bounded
inference space (the model has only ever seen what's in its chain)
and exact per-call audit. For tasks where regulatory cost dominates
capability cost — most regulated financial activities — the
chained-provenance path wins on TCO even if it loses on benchmark
accuracy. That is not a fallback position. It's the actual contract
the framework is built to win.
