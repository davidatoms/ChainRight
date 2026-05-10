# Training vs. inference: two combinatorial regimes

A note on why the pretraining → model pipeline is bounded combinatorial and
the model → inference pipeline is unbounded combinatorial, and why that
asymmetry is the actual reason no one can audit production AI by looking at
weights or corpora alone.

## 1. The training regime is bounded

Pretraining has three knobs and they all have ceilings.

- **Parameters P**: the dimensionality of weight space. State of the art today
  is ~10¹²–10¹³. Bounded by hardware and budget.
- **Corpus D**: training tokens. ~10¹³ for current frontier models. Bounded
  by what humans have written.
- **Compute C**: FLOPs spent on the optimizer. Optimal C ≈ k·P·D under
  Chinchilla scaling. Bounded by money.

The combinatorial structure being explored is weight space, R^P. That is a
continuous space of cardinality 2^ℵ₀, formally infinite. But SGD samples a
*single* one-dimensional trajectory through it. The thing the optimizer
produces is one point: one P-dimensional vector of floats. Many-to-one
compression of D tokens into P weights.

So the training regime has three properties that matter:

1. The cost is linear: O(P · D) FLOPs, paid once.
2. The output is a single point in weight space.
3. The map "corpus → model" is many-to-one. Different corpora yield similar
   models at similar loss.

These together mean training is *expensive* but *finite*. You can put a
dollar number on it. You can put a calendar date on when it ends.

## 2. The inference regime is unbounded

Inference has different knobs.

- **Vocab V**: ~10⁵. Bounded by the tokenizer.
- **Context length N**: ~10⁵–10⁶. Bounded by attention complexity.
- **Output length M**: ~10⁴. Bounded by max_tokens.
- **User count U** × **calls per user T**: unbounded. New users join, old
  users keep typing.

The combinatorial structure here is the *prompt space* V^N. With V=10⁵ and
N=10⁵, that is 10^500000 distinct prompts. Plus V^M responses per prompt.
Plus user-time UT.

Numbers for scale:

| Quantity                                  | Order of magnitude |
| ----------------------------------------- | ------------------ |
| Parameters in a frontier model            | 10¹²               |
| Training tokens                           | 10¹³               |
| Atoms in the observable universe          | 10⁸⁰               |
| Prompt space V^N at V=10⁵, N=10⁵          | 10⁵⁰⁰⁰⁰⁰           |
| V^N restricted to grammatical English-ish | 10⁵⁰⁰⁰⁰ (rough)   |

Even after restricting to "prompts a human might plausibly write," the
prompt space is something like 10⁵⁰⁰⁰⁰. That number divided by the
parameter count is 10⁴⁹⁹⁹⁸⁸. The prompt space is unimaginably larger than
the model that processes it.

This is the asymmetry that breaks every audit framework I have seen
proposed.

## 3. The ratio that matters

For any frontier model deployed today:

- **Information-theoretic gap**: |prompt space| / P ≈ 10⁴⁹⁹⁹⁸⁸. The model
  has vastly more possible behaviors than parameters with which to be
  introspected.
- **Compute gap**: inference compute already exceeds training compute by
  roughly two orders of magnitude for popular models, and the ratio grows
  with deployment time. Training is a one-time integral; inference is an
  ongoing one.
- **Observability gap**: you can observe the corpus and the optimizer
  trajectory and reconstruct training. You cannot observe a meaningful
  fraction of the prompt space, no matter how much you log. The space is
  too large.

These three gaps all point the same way: whatever the training process
produced, what the model *does* in production is determined by an input
distribution exponentially larger than anything you can pre-audit.

## 4. Why this matters for "trained on what"

The standard regulatory question is "what was this model trained on?"
That question targets the bounded side. Even fully answered, it does not
constrain the inference side.

A model trained on 10¹³ tokens of public text is, at inference, a function
that maps any of 10⁵⁰⁰⁰⁰⁰ possible prompts to a response. The training
corpus is a measure-zero subset of the prompt space. Knowing every token in
the corpus tells you nothing about what the model will produce on prompts
the corpus did not contain — and almost every prompt the model ever sees
falls into that category.

This is the thing §1.4 of the paper draft is reaching for when it talks
about "N v NP" and weights being shared across firms. The intuition is
right. The naming is not. Concretely:

- **N** = bounded resources used in training (data, parameters, compute).
- **The combinatorial explosion** = the prompt × response space at
  inference, which is exponential in N (specifically, V^N).
- **The audit gap** = trying to infer behavior in the V^N space from
  observations in the N space. Information-theoretically impossible past a
  point.

## 5. Connection to integration vs. derivation

The note `integration_versus_derivation.md` argues that training is the
derivative direction (lossy compression of D into P) and ChainRight is the
integral direction (append-only ledger of inputs and outputs).

The combinatorial argument here adds a quantitative claim: **the integral
direction is the only one that scales with the actual size of the problem.**

- Differentiation operates on the corpus. Cost ∝ D. Outcome compresses D
  into P. The corpus is the entire universe the derivative ever sees.
- Integration operates on the prompt-response stream at inference. Cost ∝
  T (interactions over time). Outcome accumulates the trajectory.

If the prompt space is 10⁵⁰⁰⁰⁰⁰ and the corpus is 10¹³, then any audit
that looks only at the corpus is sampling 10⁻⁴⁹⁹⁹⁸⁷ of the relevant space.
Any audit that integrates (prompt, response) pairs at inference samples a
linearly-growing fraction of the actual usage that occurred — which is the
only fraction that has ever produced material consequences.

The integral wins not because the integrator is smarter, but because the
integrator is in the right space.

## 6. Connection to equilibrium-as-SAT

`equilibrium_as_sat.md` argues that the equilibrium check is structurally a
SAT formula and that the verifier carries a 10⁶ human-typing constant on
five of eight clauses.

Add the inference combinatorics: the formula has V^N possible "variable
assignments" (prompts) and the verifier costs 10⁶× a tokenizer per check.
So the cost of *exhaustive* equilibrium verification across the prompt
space is:

```
V^N × (verifier cost per prompt)
= 10^500000 × ~50 typing-equivalent seconds
= 5 × 10^500001 seconds
```

Versus the age of the universe: ~4 × 10¹⁷ seconds. The exhaustive audit
exceeds the lifetime of physics by 499,983 orders of magnitude.

This is not a complaint about the verifier being slow. The verifier is
fine. The space is too big.

What this means in practice: equilibrium verification can only ever sample
the prompt space. The sampling has to be ledger-driven (audit what was
actually asked) rather than coverage-driven (audit a representative cross-
section), because no representative cross-section of V^N exists in any
useful sense. A ledger over actual usage, on the other hand, samples
exactly the prompts that carried consequence. That is the chain ChainRight
maintains.

## 7. Implications for the paper's regulatory argument

Three claims fall out cleanly:

1. **Auditing the training corpus is necessary but not sufficient.** The
   training corpus bounds *what* the model was shown, not *what it does*.
   For a model that operates over V^N inputs, observing the bounded
   training input is observing a measure-zero subset of the relevant
   distribution.

2. **Weight inspection is even less informative.** Weights are the
   compressed encoding of D into P. They describe a static configuration,
   not a behavioral envelope over the inference space. Mechanistic
   interpretability research is making slow progress here, but even a
   complete circuit-level understanding of P parameters does not enumerate
   the V^N prompt space.

3. **Per-call ledgering is not a "nice to have."** It is the only
   intervention that scales with the size of the problem the regulator
   actually faces. Pre-deployment audits scale with N (the bounded side).
   Per-call ledgering scales with the actually-used subset of V^N. The
   actually-used subset is what produces every material outcome the
   regulator cares about.

## 8. The number to put in the paper's introduction

If you want one sentence that frames the problem:

> A frontier language model is a function from a 10⁵⁰⁰⁰⁰⁰-dimensional input
> space to an output. Auditing this function by inspecting the 10¹³ tokens
> it was trained on is sampling 10⁻⁴⁹⁹⁹⁸⁷ of the space whose behavior the
> regulator is responsible for.

Every regulatory framework currently in flight in the U.S. and EU operates
in the bounded N-side. None of them samples in the right space. ChainRight
is an attempt to define what an audit in the right space would even look
like.
