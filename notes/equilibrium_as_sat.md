# Equilibrium as SAT, and where the typing test breaks the analogy

A note connecting three things that have been building up in this project: the
equilibrium harness in `chainright.equilibrium`, the `--typing-test` mode in
`cli.py`, and the §1.4 P-vs-NP intuition in the paper draft.

## 1. The equilibrium aggregator is a CNF formula

The harness aggregates eight per-test predicates over a tuple
`(prompt P, model M, response R, environment E)`:

```
equilibrium(P, M, R, E) ≡
    compression_test(P, P', R, R', GT)         ∧
    proportionality_test(P, R, τ_prop)         ∧
    time_cost_test(P, R, E.baseline, τ_time)   ∧
    semantic_stability_test([Pᵢ], R, τ_stab)   ∧
    prompt_decomposition_test(P, [Sⱼ], R)      ∧
    expert_agreement_test(P, expert)           ∧
    provider_comparison_test(providers, P, GT) ∧
    verifiability_iteration_test(P, R, verifier, refine)
```

Each clause is a Boolean predicate. The aggregate is a conjunction. That is
the form of a CNF formula, and equilibrium holds iff the assignment
`(P, M, R, E)` satisfies every clause.

`EquilibriumReport.at_equilibrium` is the literal evaluator of that formula.
It is a SAT verifier in the textbook sense.

## 2. SAT says: verification is the easy part

The defining property of SAT — and the entire reason it matters — is the
asymmetry between solving and verifying. Given a candidate assignment x, the
verifier walks each clause once and checks it in polynomial time. Finding x
is, on every formulation we have, exponentially hard in the worst case.
NP-completeness is the formal name for that asymmetry.

The equilibrium harness is shaped the same way:

- **Verification**: run each test. Each test is bounded — single-pass over
  text, a fixed number of function calls, no search. The whole verifier
  finishes in milliseconds for any reasonable input.
- **Solving**: find a `(P, M, R)` tuple that passes every test. The search
  space is the space of prompt phrasings × model choices × response
  alternatives. Combinatorial. No closed form.

So equilibrium is an NP-shaped problem. Generation is hard. Verification is
easy. This matches the intuition in §1.4 of the paper draft, where the
"N v NP" sketch is reaching for exactly this asymmetry.

## 3. The typing test breaks the SAT promise

Here is where the analogy stops being clean, and where it stops mattering
that equilibrium is in NP.

In real SAT, "verification is easy" means polynomial in the size of the
input. The verifier is a deterministic algorithm running on a CPU. There is
no human in the loop.

The equilibrium verifier has humans inside it. Specifically:

| Clause                            | Requires a human to write... |
| --------------------------------- | ---------------------------- |
| compression_test                  | the compressed prompt P'     |
| semantic_stability_test           | the paraphrastic variants Pᵢ |
| prompt_decomposition_test         | the sub-questions Sⱼ         |
| expert_agreement_test             | the rating + rationale       |
| verifiability_iteration_test      | the verifier and refine fns  |

Five of the eight clauses are gated on typing. The other three
(proportionality, time-cost, provider-comparison) are mechanical — but they
are minority.

The typing test in `cli.py` lets us put a number on what "gated on typing"
costs. The empirical numbers I get on this workstation:

- ~3.5 characters per second sustained
- ~50 ms median inter-keystroke interval
- "thinking pauses" of 1–2 seconds clustered at clause boundaries
- chainright.tokenization runs the same text in tens of microseconds

The human-to-tokenizer ratio is order 10⁶.

In SAT terms: the equilibrium verifier is polynomial, but the polynomial has
a human-typing factor of ~10⁶ in front of it on every clause that requires
human-written input. Five of eight clauses pay that factor.

That is not a constant you can absorb. That is the constant.

## 4. Why this matters for whether equilibrium is reachable

If equilibrium is SAT-shaped, you could in principle write a solver:
enumerate candidate prompts, run the verifier on each, return the first that
satisfies. Equilibrium becomes a search problem.

Every candidate the solver examines costs a typing burden. The search depth
times the per-step typing cost is the total cost of the search. Past some
depth, you have spent more time searching for an equilibrium prompt than a
domain expert would have spent answering the original question directly.

This is `time_cost_test` recursively applied to the verifier itself. The
equilibrium check is only worth running if the cost of running it is less
than the cost of the work it gates. If running the equilibrium check on a
prompt-response pair takes a finance analyst ten minutes of typing across
five clauses, the deployment is net-positive only on tasks that would have
cost the analyst more than ten minutes to do unaided.

This is the actual unit economics of AI-in-finance, and the typing test is
the only instrument in the project that measures it.

## 5. Connection to the N-body framing

An N-body system has no closed-form solution. You integrate numerically. The
total cost is the per-step cost times the number of steps.

An equilibrium AI deployment has the same shape:

- per-step cost = one verifier pass = one full equilibrium check, dominated
  by typing time on the human-gated clauses
- number of steps = how many candidate prompts the search explores before
  finding a satisfying one (or giving up)

The integral of the per-step cost over the search trajectory is the total
human cost of reaching equilibrium. That integral is what
`integration_versus_derivation.md` argues we should be computing in the
first place. The N-body title of the paper is, in this view, literally an
integration claim: equilibrium is what you reach by accumulating the cost of
every verifier pass, not by taking the gradient of any one of them.

## 6. Implication for regulation

A regulator who treats AI verification as ordinary SAT will conclude that
verification is fast and audit is therefore tractable. They will be wrong
in the same way an SGD optimizer is wrong about loss landscapes: locally
fast, globally wrong-shaped.

A regulator who measures the typing cost of running a single verification
cycle, and multiplies by the volume of AI interactions in the regulated
domain, gets the actual scale of the audit problem. For finance, where
every model call is potentially material, that is the difference between an
audit regime that is cosmetic and one that bites.

The typing test is not a curiosity. It is the unit cost in a calculation
the industry has not yet bothered to do.

## 7. What this suggests next

Three things that fall out of the SAT framing once you take it literally:

1. **Write the SAT-style solver.** A function that enumerates candidate
   prompts and returns the first one that passes all eight equilibrium
   clauses. Cap depth by typing-cost-budget rather than by iteration count.
   The cap is the empirical content of the §1 argument.

2. **Treat each clause as an independent threshold knob.** The equilibrium
   formula has 8 thresholds today (proportionality ratio, stability min,
   decomposition mean, etc.). They were chosen by hand. A grid sweep over
   them on the gpt-2-output-dataset triples would tell us which clauses
   carry the signal and which are slack.

3. **Cost-weighted aggregation.** Right now `at_equilibrium` is a hard
   conjunction. A cost-weighted version would assign a typing-cost to each
   clause and report the total cost of the verification, not just pass/fail.
   That is the form a regulator can actually act on.

None of these need a frontier model. They need the integral of typing time
across clauses, which the existing harness now measures.
