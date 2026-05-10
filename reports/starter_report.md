# ChainRight: Starter Report

A current-state writeup of the project for someone new to it (a reviewer, a
collaborator, or future-me). Covers the thesis, what's been built, what
empirical results exist, and what the framework lets you do today. Not a
README — a starter report describes what the artifact actually is, not just
how to install it.

## What this project claims

Frontier language models cannot be audited the way regulators and
enterprises currently audit other forms of automation. The reasons are
structural: training compresses data into weights (lossy), inference space
is exponentially larger than training space (intractable to cover), and
verification requires human-typed inputs whose cost dominates the verifier
itself.

**ChainRight is the proposal that the right operation is integration, not
inspection.** Instead of auditing a frozen model by reading its weights or
re-checking its training corpus, you accumulate every (prompt, model,
response, attribution) tuple as it happens, into a cryptographically chained
ledger. Each tuple carries enough metadata to be adjudicated independently.
The chain itself is the audit artifact.

The full argument is in four notes:

- [`notes/integration_versus_derivation.md`](../notes/integration_versus_derivation.md) —
  why training is the derivative direction (lossy) and ChainRight is the
  integral direction (lossless).
- [`notes/equilibrium_as_sat.md`](../notes/equilibrium_as_sat.md) — why the
  equilibrium check is structurally a CNF formula, and where the ~10⁶
  human-typing constant breaks the SAT-style "verification is fast" promise.
- [`notes/training_vs_inference_combinatorics.md`](../notes/training_vs_inference_combinatorics.md) —
  why the inference space (~10⁵⁰⁰⁰⁰⁰ prompts) is exponentially larger than
  any training corpus, making sample-based audit hopeless and ledger-based
  audit the only viable scaling. The negative case for closed-model audit.
- [`notes/data_to_output_attribution.md`](../notes/data_to_output_attribution.md) —
  the positive case: chained training data + per-step trajectory + attribution
  methods compose into retroactive output-to-data tracing on a small model.
  This is the project's positive contribution.

Plus a research-direction list: [`notes/boolean_followups.md`](../notes/boolean_followups.md)
covers open moves on the framework's Boolean clause outputs.

For the empirical surface — the testable hypotheses the framework generates,
including the N vs NP framing — see [`reports/hypotheses_to_test.md`](hypotheses_to_test.md).

## What's runnable today

The codebase is a Python 3.10+ package (`chainright`) plus a set of
standalone CLI scripts and example runs.

**Library modules** (`src/chainright/`):

- `tokenization.py` — multi-strategy text tokenization (characters,
  whitespace, words+punct, sentences, utf8 bytes, optional tiktoken).
- `equilibrium.py` — eight-clause CNF verifier (compression,
  proportionality, time-cost, semantic stability, prompt decomposition,
  expert agreement, provider comparison, verifiability iteration).
  Cost-weighted aggregation in seconds-of-typing-equivalent.
- `sat_solver.py` — SAT-style search over candidate prompts under a
  typing-cost budget; built-in truncation and word-drop generators.
- `datasets.py` — streaming loaders for the gpt-2-output-dataset corpora
  (webtext + 8 model sources × 3 splits); equilibrium-triple synthesis.
- `llm_adapters.py` — `LLM = Callable[[str], str]` adapters for
  static-corpus lookup, `chainright.llm_cli` (Anthropic / OpenAI /
  Google), Ollama (local HTTP), and HuggingFace via circuit-tracer.
  Plus an attribution-graph variant for circuit-level provenance.
- `provenance.py` — Blockchain helpers: `chain_equilibrium_run`,
  `chain_corpus_check`, attribution-graph hashing and lightweight
  summarization, content-addressed lookup over chains.
- `blockchain.py` — the cryptographic chain itself; pre-existing.

**CLI tools** (`./`):

- `cli.py` — tokenize text in every view and emit JSON with per-view
  runtime; optional `--typing-test` mode captures per-keystroke
  intervals on Windows for empirical typing-cost measurement.
- `check_corpus.py` — substring + n-gram membership testing across the
  gpt-2-output-dataset and arbitrary `--custom-corpus` paths; verdict
  distinguishes human-source / model-source / both / neither; `--log`
  appends every check to a JSONL trail; `--chain-out` cryptographically
  chains the absence-attestation result.

**Example scripts** (`examples/`):

- `compare_token_distributions.py` — tokenization-view statistics
  across human and model corpora, replicating OpenAI's published
  type-token-ratio shift on top-K samples.
- `equilibrium_on_real_data.py` — runs the equilibrium harness on real
  triples; selectable LLM source (corpus, Anthropic, OpenAI, Google,
  Ollama, HuggingFace via circuit-tracer); chain output supported.
- `sweep_equilibrium_thresholds.py` — joint and marginal threshold
  sweeps; identifies signal-carrying clauses vs slack ones.
- `boolean_signatures.py` — 8-bit Boolean signature per triple,
  trained logistic regression human-vs-model classifier, head-to-head
  against the TF-IDF baseline.
- `circuit_tracer_demo.py` — end-to-end mechanistic provenance: load
  a HuggingFace model with transcoders, generate a response, compute
  the attribution graph, chain `(prompt, response, graph_hash,
  graph_summary, equilibrium_report)`.

## Empirical results to date

- **Tokenization-view distributional shift** between human and
  top-K-sampled GPT-2 outputs: type-token ratio drops 13–16% for
  top-K samples vs webtext, matching OpenAI's published findings —
  reproduced from purely deterministic tokenization views with no
  trained classifier.
- **TF-IDF detector replication** at sub-sampled scale:
  small-117M-k40 reaches 89.6% test accuracy at n_train=10K
  (vs OpenAI's 92.7% reference at n_train=500K); xl-1542M-k40 reaches
  82.4% (vs reference 92.7% at the harder target).
- **Equilibrium-as-detector**: 8-bit Boolean signatures from the
  equilibrium clauses reach **75.0% test accuracy** on a 4-source
  classification task — using **only 8 Boolean values per sample**,
  effectively a 2-bit detector (time_cost + proportionality carrying
  most of the signal). With prompt-sensitivity clauses unlocked
  (real LLM run pending), this is expected to close most of the gap
  to the TF-IDF baseline.
- **Verifier cost on real data**: ~52.6 seconds of human-typing-
  equivalent cost per (prompt, response) triple on
  `small-117M-k40` corpus mode. This is the unit cost a regulator
  would multiply by deployment volume to estimate audit-FTE budget.
- **Verbatim memorization**: webtext snippet
  *"Are the prices at this restaurant mid-range / moderate? Yes No
  Unsure..."* appears in xl-1542M-generated samples at record id
  `259697` — discovered on the first run of `check_corpus.py`,
  illustrating the audit primitive at work.

## Audit primitives available

| Primitive | What it attests | Where |
|---|---|---|
| Equilibrium chain | Verifier verdict + cost on a (prompt, response) pair | `chain_equilibrium_run` |
| Attribution chain | Per-prompt circuit-level mechanistic explanation (hash + summary) | `chain_equilibrium_run(..., attribution_graph=g)` |
| Corpus check chain | Presence/absence in a configured corpus set, hash-only payload | `chain_corpus_check` |
| JSONL log | Append-only log of every check_corpus run | `check_corpus.py --log` |

## Tests and integrity

68 tests passing across `tests/test_equilibrium.py`,
`tests/test_sat_solver.py`, and `tests/test_provenance.py`. Coverage
includes:

- Eight equilibrium clauses (per-clause behavior on hand-built
  passing/failing inputs).
- Cost-weighted aggregation across the eight clauses, with explicit
  zero-cost handling for clauses that don't require typing.
- SAT-style search budget enforcement and built-in candidate
  generators.
- Provenance round-trips: hash determinism, chain validity under
  save/load, content-addressed lookup, multi-provider lookup.
- Attribution-graph summarization with tolerance for
  partially-populated graph stand-ins.
- Corpus-check absence-attestation: text never on chain, only its
  hash.

## What's pending

- **First real-LLM run.** Every empirical number above comes from the
  static corpus-lookup adapter. A single batch through Ollama or
  HuggingFace-via-circuit-tracer would unlock the prompt-sensitivity
  clauses (compression, stability, decomposition, verifiability) and
  let the boolean-signature detector compete with TF-IDF on a fair
  basis.
- **Trained verifiable model.** The natural next milestone (argued in
  [`notes/data_to_output_attribution.md`](../notes/data_to_output_attribution.md)):
  a small (~125M–1B param) model trained from scratch or LoRA-fine-tuned
  on a scoped finance corpus, with every training datum chained and every
  training step's loss/grad/val logged. This is the artifact that
  demonstrates the project's positive contribution — a model whose outputs
  can be retroactively traced to specific training data via the composition
  of TracIn-style influence attribution, circuit-tracer mechanistic
  attribution, and the chained training trajectory.
- **Paper.** The four notes are the conceptual scaffolding. The
  paper draft (`paper/`, currently first-person opinionated prose
  with unfinished sentences) needs structural editing into a §1
  problem, §2 framework, §3 methods, §4 results, §5 implications.
  The empirical results above are §4 material.

## How to get started

```bash
# Install
pip install -e .

# Tokenize and time
python cli.py "your text here"
python cli.py --typing-test --target "the fed raised rates by 25 bps"

# Check corpus membership
python check_corpus.py "some text" --custom-corpus my_archive.jsonl --chain-out audit.chain.json

# Run the equilibrium harness on real data
python examples/equilibrium_on_real_data.py --n 50

# Compare distributions
python examples/compare_token_distributions.py --n 300

# Run the Boolean-signature detector
python examples/boolean_signatures.py --n 500
```

If you want the conceptual case before the code, read the four notes in
this order: integration → SAT → combinatorics → followups.
