# Integration vs. Derivation

A note on why forward training and ChainRight are different operations on
different objects, and why conflating them produces almost every legal,
epistemic, and audit problem in AI right now.

## The shape of forward training

Forward training is differentiation.

Every step of stochastic gradient descent reduces a batch of data to a vector
of partial derivatives, then nudges the weights in the direction that locally
reduces loss. The process is pointwise. It sees a slice of data, computes a
gradient, updates, and forgets. What was the loss yesterday? The optimizer
doesn't know. What was the input that caused this update? The optimizer
doesn't carry it. The training trajectory is consumed; only the endpoint —
the trained weights — remains.

This is the operation underneath every "law" people have written for AI:

- **Scaling laws** (Kaplan, Hoffmann) describe how loss falls as a *function*
  of compute, parameters, and data. They are power laws on derivatives.
- **Emergence** describes capabilities that appear at scale —
  non-linearities in the gradient landscape.
- **Catastrophic forgetting** is the literal statement that gradients late in
  training overwrite gradients early in training. The derivative wins; the
  integral is discarded.

Every law of forward training is a statement about how the model *changes*.
None of them are statements about what the model *contains*.

## The shape of ChainRight

ChainRight is the other direction.

Every prompt and every response is hashed, chained, and appended. The chain
doesn't compress; it accumulates. If forward training is

```
weights_{t+1} = weights_t − η · ∇L(batch_t, weights_t)
```

then ChainRight is

```
chain_{t+1} = chain_t ++ block(prompt_t, response_t, hash_{t−1})
```

One is a recurrence that destroys its inputs. The other is a recurrence that
preserves them. One is a derivative. The other is an integral.

## Why the distinction matters

The legal and epistemic problems with current AI deployments come from
treating these two operations as if they were the same operation, or as if
one could substitute for the other.

When a frontier-model provider says they "trained on public data," they are
describing a differentiation. They took the gradient of the data and stored
it as weights. The data itself is no longer recoverable in any practical
sense. That is the *point* of training — training compresses.

When I run my own conversations through a chain, I am integrating. The
inputs and outputs are still there, in order, with cryptographic continuity.
Nothing is compressed. Nothing is forgotten.

These are different operations on different objects, and pretending
otherwise is what produces the accusation that I "distilled" a model when I
clone a project to my workstation. Distillation *is* differentiation — you
query a teacher model and use its outputs to compute gradients against a
student. ChainRight has no student. It has no gradients. It has a ledger.
The accusation conflates two operations that are mathematically as different
as `d/dx` and `∫ dx`.

## Conservation and recovery

A useful diagnostic for which operation you are running: can you reverse it?

- A trained model cannot reproduce its training corpus on demand. The
  derivative threw it away. Membership-inference attacks recover scraps;
  they do not recover the corpus.
- A ChainRight ledger reproduces every input and every output deterministically
  by walking the chain. The integral kept everything.

This is the same asymmetry as the fundamental theorem of calculus.
Differentiation discards constants. Integration recovers them up to a
constant. If you only have weights, you cannot reconstruct the trajectory.
If you only have the trajectory, you cannot reconstruct the weights — but
you can audit them. You can ask of any output, "did this model produce this
string in response to this prompt at this time?" and answer yes or no in
O(chain length).

## What this means for the laws we should be writing

The "laws of AI" that the industry has spent the last few years producing are
all derivative laws. Scaling laws, loss-curve fits, capability thresholds —
they describe motion. They do not describe state. They cannot, because the
state was discarded the moment training ended.

If we want adjudicable AI — the kind a regulator can review, the kind a court
can subpoena, the kind an enterprise can audit against a Chinese wall — we
need integral laws. Append-only laws. Laws that operate on the trajectory
of inputs and outputs rather than on the gradient of weights.

The laws I think we need:

1. **Conservation of provenance.** Every output has exactly one prompt and
   one model identifier. The triple is hashed and chained.
2. **Append-only.** No deletion, no overwrite. If a fact about an output
   changes, it changes by appending a correction, not by editing history.
3. **Compositionality.** Two chains can be merged. The merged chain is
   itself a chain. Provenance is closed under concatenation.
4. **Locality of failure.** A tampered block invalidates only the suffix
   from that block forward, not the prefix. Audits can quote-and-cite.
5. **No silent re-training.** If a model's weights change, it gets a new
   identifier in the chain. The integral does not assume the integrand is
   constant.

None of these are statements you can express in gradient-descent terms,
because gradient descent is not the right operator. They are statements
about an integral.

## The N-body connection

In an N-body system there is no closed-form solution. You integrate
numerically. The state at time t+1 is a function of every body's state at
time t and the forces between them.

Forward training treats the AI ecosystem as if every gradient update were
independent — each lab differentiating in isolation, each model trained
without reference to the others. ChainRight treats it the way an N-body
problem is actually solved: as a trajectory you accumulate. The state of
"AI in financial services" at time t is not the weights of any one model.
It is the integral of every prompt, every output, every model identifier,
every cross-firm exposure, since the system began.

If we want to adjudicate that system, we need the integral. The derivative
was already taken. The data is gone. What remains is the chain.
