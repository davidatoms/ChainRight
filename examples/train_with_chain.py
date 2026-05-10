#!/usr/bin/env python3
"""Skeleton: LoRA fine-tune of GPT-2-small with full per-step chain logging.

This is the H3 experimental rig from reports/experimental_rig_h3.md, in
runnable form. The full implementation depends on `transformers` and
`peft`, which are heavy and not part of ChainRight's hard dependencies.
This script is therefore primarily a *structural skeleton* that shows
exactly how `chainright.training_chain.chain_training_step` integrates
into a real training loop. Filling in the bracketed sections turns it
into a complete experiment.

Install once before running:

    pip install transformers>=4.40 peft>=0.10 datasets>=2.18 safetensors

Usage when complete:

    python examples/train_with_chain.py \\
        --base-model gpt2 \\
        --lora-rank 32 \\
        --corpus webtext \\
        --split train \\
        --n-records 10000 \\
        --epochs 5 \\
        --batch-size 16 \\
        --chain-out runs/h3_train.chain.json \\
        --checkpoint-dir runs/h3_checkpoints/

The chain produced by this script is consumed by examples/attribute_outputs.py
(TBD) at audit time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

from chainright.blockchain import Blockchain
from chainright.datasets import iter_texts
from chainright.training_chain import (
    TrainingStepRecord,
    chain_training_step,
    chain_training_summary,
    sha256_text,
)


def _require(package_name: str):
    """Raise SystemExit with an install hint if a heavy dep isn't available."""
    try:
        __import__(package_name)
    except ImportError:
        raise SystemExit(
            f"This script requires the {package_name!r} package. Install with:\n"
            f"    pip install transformers>=4.40 peft>=0.10 datasets>=2.18 safetensors"
        )


def load_training_examples(
    corpus: str,
    split: str,
    n_records: int,
    data_dir: Optional[Path] = None,
    min_length: int = 200,
) -> List[Tuple[str, str]]:
    """Pull (data_hash, text) tuples from the gpt-2-output-dataset.

    Hashes are over the raw text so they survive any tokenizer change. If
    you change the tokenizer between training and attribution, the chain
    will still hash to the same values.
    """
    examples: List[Tuple[str, str]] = []
    for text in iter_texts(corpus, split, data_dir=data_dir, n=n_records, min_length=min_length):
        examples.append((sha256_text(text), text))
    return examples


def hash_state_dict(state_dict) -> str:
    """SHA-256 of a torch state_dict, serialized canonically."""
    import io
    import torch  # local import; heavy
    buf = io.BytesIO()
    torch.save(state_dict, buf)
    return hashlib.sha256(buf.getvalue()).hexdigest()


def per_layer_delta_norms(prev_state, curr_state) -> dict:
    """Per-named-parameter L2 norm of (curr - prev), trainable params only."""
    import torch
    out = {}
    for name, curr in curr_state.items():
        prev = prev_state.get(name)
        if prev is None or not torch.is_floating_point(curr):
            continue
        delta = (curr - prev).to(torch.float32)
        out[name] = float(delta.norm().item())
    return out


def train_loop(
    args: argparse.Namespace,
) -> None:
    """The actual training loop. Pseudocode-shaped — fill in the bracketed
    sections to run a real fine-tune."""
    _require("transformers")
    _require("peft")
    _require("torch")

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    # 1. Load base model + tokenizer.
    print(f"Loading base model {args.base_model}...")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(args.base_model, torch_dtype=torch.float16)

    # 2. Wrap in LoRA.
    lora_config = LoraConfig(
        r=args.lora_rank,
        lora_alpha=args.lora_rank * 2,
        target_modules=["c_attn"],  # GPT-2 uses fused QKV
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(base, lora_config)
    model = model.to("cuda" if torch.cuda.is_available() else "cpu")
    model.print_trainable_parameters()

    # 3. Load data.
    print(f"Loading {args.n_records} records from {args.corpus}.{args.split}...")
    examples = load_training_examples(
        corpus=args.corpus, split=args.split,
        n_records=args.n_records, data_dir=args.data_dir,
    )
    print(f"  {len(examples)} examples loaded")

    # 4. Set up optimizer.
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=args.learning_rate,
    )

    # 5. Initialize chain. Append-mode if file exists.
    if args.chain_out and args.chain_out.exists():
        blockchain = Blockchain.load_from_file(str(args.chain_out))
        print(f"  Resuming chain from {args.chain_out} ({len(blockchain.chain)} blocks)")
    else:
        blockchain = Blockchain(difficulty=args.chain_difficulty)
        print("  New chain initialized")

    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # 6. Training loop.
    session_id = args.session_id or f"h3-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    print(f"Session: {session_id}")
    step_idx = 0
    val_examples = examples[-200:]  # reserve tail for val (deterministic)
    train_examples = examples[:-200]

    prev_state = {k: v.detach().clone() for k, v in model.state_dict().items() if v.requires_grad}

    for epoch in range(args.epochs):
        # Shuffle deterministically per epoch
        order = list(range(len(train_examples)))
        rng = torch.Generator().manual_seed(args.seed + epoch)
        order = torch.randperm(len(train_examples), generator=rng).tolist()

        for batch_start in range(0, len(order), args.batch_size):
            batch_indices = order[batch_start:batch_start + args.batch_size]
            batch = [train_examples[i] for i in batch_indices]
            batch_hashes = [h for h, _t in batch]
            batch_texts = [t for _h, t in batch]

            # Tokenize and forward.
            inputs = tokenizer(
                batch_texts, padding=True, truncation=True,
                max_length=args.context_length, return_tensors="pt",
            ).to(model.device)

            # Loss before update: forward only, no grad.
            with torch.no_grad():
                loss_before = model(**inputs, labels=inputs["input_ids"]).loss.item()

            # Train step.
            optimizer.zero_grad()
            out = model(**inputs, labels=inputs["input_ids"])
            out.loss.backward()
            grad_norm = float(torch.nn.utils.clip_grad_norm_(
                [p for p in model.parameters() if p.requires_grad], max_norm=1.0,
            ))
            optimizer.step()
            loss_after = float(out.loss.item())

            # Layer-delta norms (against the previous step's weights).
            curr_state = {k: v.detach().clone() for k, v in model.state_dict().items() if v.requires_grad}
            delta_norms = per_layer_delta_norms(prev_state, curr_state)
            prev_state = curr_state

            # Periodic val_loss + checkpoint.
            val_loss: Optional[float] = None
            weights_hash: Optional[str] = None
            if step_idx % args.checkpoint_every == 0:
                with torch.no_grad():
                    val_inputs = tokenizer(
                        [t for _h, t in val_examples[:args.batch_size]],
                        padding=True, truncation=True,
                        max_length=args.context_length, return_tensors="pt",
                    ).to(model.device)
                    val_loss = float(model(**val_inputs, labels=val_inputs["input_ids"]).loss.item())

                # Save LoRA checkpoint, hash it for the chain.
                ckpt_path = args.checkpoint_dir / f"step_{step_idx:06d}.safetensors"
                model.save_pretrained(str(ckpt_path.parent / f"step_{step_idx:06d}"))
                weights_hash = hash_state_dict({
                    k: v.cpu() for k, v in model.state_dict().items() if v.requires_grad
                })

            # Append the trajectory record to the chain.
            record = TrainingStepRecord(
                step_idx=step_idx,
                phase="finetune",
                batch_data_hashes=batch_hashes,
                loss_before=loss_before,
                loss_after=loss_after,
                grad_norm=grad_norm,
                per_layer_delta_norms=delta_norms,
                val_loss=val_loss,
                learning_rate=optimizer.param_groups[0]["lr"],
                weights_hash=weights_hash,
                extra={"epoch": epoch},
            )
            chain_training_step(blockchain, record, session_id=session_id)

            if step_idx % args.log_every == 0:
                print(f"  step {step_idx:5d}  loss {loss_after:.4f}  "
                      f"grad {grad_norm:.3f}  "
                      f"{'val ' + format(val_loss, '.4f') if val_loss is not None else ''}")
            step_idx += 1

        # Save chain after each epoch so a crash doesn't lose progress.
        if args.chain_out:
            blockchain.save_to_file(str(args.chain_out))

    # Final summary.
    summary = chain_training_summary(blockchain)
    print()
    print("Training complete.")
    print(f"  Total steps logged:   {summary['n_training_step_blocks']}")
    print(f"  Total examples seen:  {summary['total_examples_seen']}")
    print(f"  Final val loss:       {summary['final_val_loss']}")
    print(f"  Chain length / valid: {summary['chain_length']} / {summary['chain_valid']}")
    if args.chain_out:
        blockchain.save_to_file(str(args.chain_out))
        print(f"  Chain written to:     {args.chain_out}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--base-model", default="gpt2")
    p.add_argument("--lora-rank", type=int, default=32)
    p.add_argument("--corpus", default="webtext")
    p.add_argument("--split", default="train", choices=["train", "valid", "test"])
    p.add_argument("--n-records", type=int, default=10000)
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--context-length", type=int, default=512)
    p.add_argument("--learning-rate", type=float, default=5e-5)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--checkpoint-every", type=int, default=100,
                   help="Save LoRA checkpoint + record val_loss every N steps.")
    p.add_argument("--log-every", type=int, default=10)
    p.add_argument("--data-dir", type=Path, default=None)
    p.add_argument("--chain-out", type=Path, default=Path("runs/h3_train.chain.json"))
    p.add_argument("--chain-difficulty", type=int, default=1)
    p.add_argument("--checkpoint-dir", type=Path, default=Path("runs/h3_checkpoints"))
    p.add_argument("--session-id", type=str, default=None)
    args = p.parse_args(argv)

    train_loop(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
