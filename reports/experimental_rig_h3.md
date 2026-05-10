# Experimental rig for H3 — trained-model retracing

A concrete plan for the experiment that tests Hypothesis 3 from
`reports/hypotheses_to_test.md`:

> A small (~125M–1B param) model trained from scratch on a chained
> corpus admits retroactive output-to-training-example attribution
> with per-output audit cost ≤ 5× the inference cost.

This is the project's positive contribution made empirical. The rig
sketched below is what an artifact section of the paper would
describe.

## Goal in one sentence

Train a small model with full chained data + trajectory provenance,
then demonstrate that any output's top-1 attributed training example
matches a chain block whose `batch_data_hashes` includes that
example's hash, at ≥ 80% match rate.

## What to fine-tune

**GPT-2-small (124M)** via **LoRA** (low-rank adaptation, `peft`).

Why:

- Smallest widely-used baseline for attribution research; published
  TracIn / influence-function results exist for it.
- Tokenizer matches the gpt-2-output-dataset, so no out-of-vocab
  surprises against our corpus.
- LoRA keeps trainable parameters at ~1–4M (rank=16 on q/v
  projections), making influence-function attribution tractable in
  minutes per output rather than hours.
- 124M params + LoRA + AdamW state + fp16 activations at batch=16,
  context=512 fits comfortably on the 3070 Ti's 8 GB VRAM.

## What corpus

A **10,000-record slice** of `webtext.train.jsonl` from the
gpt-2-output-dataset. Already on disk locally.

Why this slice:

- In-distribution for GPT-2 (no domain shift, isolates attribution
  effects from generalization effects).
- Small enough for full per-step chain logging to stay under ~50 MB
  total chain size.
- Pretokenized records map cleanly to GPT-2's BPE tokenizer.
- We have the matching test/valid splits already loaded for
  evaluation.

A **finance-relevant variant** is feasible later: replace the slice
with a 10K-record blend of SEC 10-K excerpts + earnings call
transcripts. For H3 the topic doesn't matter — the attribution
mechanic does. Topic specialization is a follow-up experiment.

## Per-step chain payload

Each training step appends one block. Fields:

| Field | Type | Source | Why |
|---|---|---|---|
| `step_idx` | int | training loop counter | Order anchor |
| `phase` | str | constant per run ("finetune") | Distinguishes pretraining / finetuning / RLHF in multi-phase chains |
| `timestamp` | ISO str | UTC now | Wall-clock provenance |
| `batch_data_hashes` | list[str] | sha256 of each example's text | The audit-critical field — these are what attribution will look up |
| `batch_size` | int | derived | Convenience |
| `loss_before` | float | model.eval() on batch before update | Trajectory shape |
| `loss_after` | float | model.eval() on batch after update | Trajectory shape |
| `loss_delta` | float | derived | Per-step learning signal |
| `grad_norm` | float | torch.nn.utils.clip_grad_norm_ return | Health signal |
| `per_layer_delta_norms` | dict[str, float] | norm of weight delta per LoRA layer | Where in the network this step landed |
| `val_loss` | float | model.eval() on fixed val batch | Generalization signal |
| `learning_rate` | float | optimizer.param_groups[0]["lr"] | Reconstructable optimizer state |
| `weights_hash` | str | sha256 of full LoRA weight vector | Certifies the post-step state |
| `optimizer_state_hash` | str | sha256 of optimizer.state_dict() bytes | Certifies the optimizer state for replay |

Total per-block payload: ~1–2 KB. For 10K examples × 10 epochs at
batch=16, that's ~6,250 steps → ~10–13 MB chain. Fits cleanly.

## Attribution method

**TracIn-CP** (Pruthi et al., NeurIPS 2020). Concretely:

For each test example x_test and each training example x_train:

```
influence(x_test, x_train) ≈ Σ_k η_k · ∇L(x_test; θ_k) · ∇L(x_train; θ_k)
```

where the sum is over checkpoints `k`, `η_k` is the learning rate at
checkpoint `k`, and `θ_k` is the LoRA weights at checkpoint `k`.

Implementation choices for the rig:

- **Checkpoints:** save LoRA weights every 100 steps (~62
  checkpoints over the run). Stored as separate `.safetensors`
  files indexed by `weights_hash`. Cross-references the chain
  trivially.
- **Gradient computation:** in `torch.no_grad(loss=True)` mode (we
  want the gradient w.r.t. weights, not w.r.t. inputs), with
  `torch.autograd.grad`. ~1 second per example per checkpoint on
  the 3070 Ti.
- **Top-K retrieval:** for each test output, rank training examples
  by influence sum. Take top-1 (and top-5 for robustness).

Audit cost per output: ~62 checkpoints × ~10⁴ training examples × ~1 s
= ~17 minutes. That's higher than the H3 prediction of "≤ 5× inference
cost" — single inference is ~50 ms, so 5× is 250 ms, far under 17
minutes. **The 5× target requires precomputing per-checkpoint
training-example gradients once and caching them**, after which
attribution is one forward+backward on the test example plus a dot
product against the cache: ~1 second per output.

## Validation method

For N=100 test outputs:

1. Generate the output by running the trained LoRA model on a held-out
   prompt (drawn from `webtext.test.jsonl`).
2. Run TracIn-CP attribution against the cached training-example
   gradients. Get top-1 attributed training-example hash.
3. Walk the chain: query `find_step_by_data_hash(top_1_hash)`. Pull
   the step's payload.
4. Verify match: chain says the training example was in batch at
   step S; the influence sum should be dominated by checkpoints
   ≥ S (the training example couldn't have influenced earlier
   updates).
5. Aggregate: top-1 match rate across N=100 outputs.

Predicted result: top-1 chain-match rate ≥ 80%.

## Code modules to build

| Module | Purpose | Status |
|---|---|---|
| `src/chainright/training_chain.py` | Per-step trajectory logging into a Blockchain; helpers for finding steps by data hash | **Built in this commit** |
| `src/chainright/attribution.py` | TracIn-CP loop over saved checkpoints, ranking, and chain lookup | Skeleton TBD |
| `examples/train_with_chain.py` | LoRA fine-tune script wired to log every step to a chain | **Skeleton built in this commit** |
| `examples/attribute_outputs.py` | Run TracIn against a trained model + chain, emit match-rate statistics | TBD |
| `tests/test_training_chain.py` | Coverage for chain_training_step + find_step_by_data_hash | **Built in this commit** |

## Hardware fit

Wall-time estimate on 3070 Ti for the H3 experiment:

- Training: 6,250 steps × ~0.5 s/step ≈ 50 minutes (LoRA fp16,
  batch=16).
- Per-step chain logging overhead: ~10 ms (sha256 + JSON serialize +
  proof-of-work at difficulty=1). Negligible.
- Per-checkpoint LoRA save: ~50 ms × 62 checkpoints = 3 seconds total.
  Negligible.
- Gradient cache build (one-time after training): 10⁴ examples × 62
  checkpoints × ~50 ms = ~9 hours. **Dominant cost.**
- Per-output attribution at audit time, with cache: ~1 second.

So the rig's wall time is dominated by the one-time cache build,
which is acceptable because it's amortized over all subsequent audit
queries. The H3 efficiency claim (audit ≤ 5× inference) is about the
amortized per-query cost, not the cache build.

## Risks and what could fail

1. **LoRA adapter influence is too weak.** If the LoRA rank is too
   low or the fine-tune is too short, the model's outputs may be
   dominated by the frozen base model's behavior, not the LoRA
   adaptation. Top-1 attribution would then point at the base
   model's training data (which we don't have chained), not at our
   10K corpus slice. Mitigation: rank=32 or higher, longer fine-tune
   (≥ 5 epochs).

2. **TracIn-CP variance.** Empirically, TracIn-CP top-1 has ~70-90%
   accuracy on standard benchmarks even at small scale. A match
   rate of 70% would still be a meaningful result, but it's below
   the H3 prediction of 80%. The hypothesis allows falsification at
   < 50%; partial success at 60-79% is still informative.

3. **Chain integrity under append throughput.** 6,250 mined blocks
   at difficulty=1 should be fine, but if proof-of-work overhead
   compounds across the run, we may need difficulty=0 (no PoW) or
   batch-mining (one block per N steps). Difficulty=1 is the current
   default; the helper exposes the override.

4. **Tokenizer drift.** If the BPE tokenization of the same text
   differs between the training run and the attribution run (e.g.,
   different transformers version), the data hashes won't match.
   Mitigation: hash the *text*, not the *token IDs*, and snapshot
   the transformers version into the chain's session metadata.

## Concrete next commands

After the modules in this commit land:

```bash
# Build the gradient cache + chain — one-time, ~50 minutes training
python examples/train_with_chain.py \
    --base-model gpt2 \
    --lora-rank 32 \
    --corpus webtext \
    --split train \
    --n-records 10000 \
    --epochs 5 \
    --chain-out runs/h3_train.chain.json \
    --checkpoint-dir runs/h3_checkpoints/

# Run attribution + chain match — once attribute_outputs.py exists
python examples/attribute_outputs.py \
    --model-checkpoint runs/h3_checkpoints/final.safetensors \
    --chain runs/h3_train.chain.json \
    --gradient-cache runs/h3_checkpoints/grad_cache.pt \
    --test-prompts 100 \
    --report runs/h3_attribution_report.json
```

The H3 result is a single number in `runs/h3_attribution_report.json`:
the top-1 chain-match rate across the 100 test prompts.

## What this experiment establishes if it succeeds

A defensible technical claim: **on the gpt-2-output-dataset webtext
slice, with GPT-2-small + LoRA, the composition of TracIn attribution
+ ChainRight per-step trajectory logging recovers the training origin
of model outputs at ≥80% top-1 match rate.**

That's the empirical core of the project's positive contribution. It
doesn't generalize to frontier-scale models on its own (H7 is the
honest claim there), but it demonstrates that the *primitive* works
end-to-end at a scale a regulator could replicate on commodity
hardware. That's the bar the substitution argument in
`reports/potential_impact_in_financial_markets.md` actually needs.
