#!/usr/bin/env python3
"""End-to-end: load a HuggingFace model via circuit-tracer, generate a response,
compute its attribution graph, and chain (prompt, response, graph_hash,
equilibrium_report) into a ChainRight blockchain.

This is the per-prompt mechanistic provenance loop described in
notes/training_vs_inference_combinatorics.md §6: the chain records not just
what the model said but the circuit-level attribution that explains why,
addressed by hash so the chain stays compact.

Defaults target the 3070 Ti / 8 GB VRAM regime: Llama-3.2 1B in float16.
The attribution pass dominates wall time (minutes per prompt). Start with
--n 3 unless you want to wait.

Usage:
    python examples/circuit_tracer_demo.py
    python examples/circuit_tracer_demo.py --n 5 --chain-out ct_runs.chain.json
    python examples/circuit_tracer_demo.py --hf-model HuggingFaceTB/SmolLM-135M
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from chainright.blockchain import Blockchain
from chainright.datasets import iter_equilibrium_triples
from chainright.equilibrium import (
    DEFAULT_HUMAN_CPS,
    EquilibriumReport,
    proportionality_test,
    time_cost_test,
)
from chainright.llm_adapters import (
    huggingface_via_circuit_tracer_with_attribution,
    static_corpus_llm,
)
from chainright.provenance import chain_equilibrium_run


def build_report(prompt: str, response: str) -> EquilibriumReport:
    response_llm = static_corpus_llm(response)
    report = EquilibriumReport()
    report.add(
        "proportionality",
        proportionality_test(response_llm, prompt, threshold=8.0),
    )
    report.add(
        "time_cost",
        time_cost_test(
            prompt=prompt, response=response,
            expert_baseline_seconds=300.0,
            verification_seconds=30.0,
        ),
    )
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--n", type=int, default=3,
                   help="number of prompts (attribution is expensive)")
    p.add_argument("--corpus-model", default="small-117M-k40",
                   help="which gpt-2-output-dataset source to draw prompts from")
    p.add_argument("--split", default="test", choices=["train", "valid", "test"])
    p.add_argument("--k-words", type=int, default=20)
    p.add_argument("--data-dir", type=Path, default=None)
    p.add_argument("--hf-model", default="meta-llama/Llama-3.2-1B")
    p.add_argument("--hf-transcoder-set", default="mntss/transcoder-Llama-3.2-1B")
    p.add_argument("--hf-dtype", default="float16",
                   choices=["float32", "float16", "bfloat16"])
    p.add_argument("--max-new-tokens", type=int, default=64)
    p.add_argument("--max-feature-nodes", type=int, default=4096)
    p.add_argument("--attribution-offload", default="cpu",
                   choices=["cpu", "disk", "none"])
    p.add_argument("--chain-out", type=Path, default=None)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--cps", type=float, default=DEFAULT_HUMAN_CPS)
    args = p.parse_args(argv)

    print(f"Loading {args.hf_model} with transcoders {args.hf_transcoder_set}...")
    print("(This is slow on first run — model + transcoders are downloaded from HuggingFace.)")
    call = huggingface_via_circuit_tracer_with_attribution(
        model_name=args.hf_model,
        transcoder_set=args.hf_transcoder_set,
        dtype=args.hf_dtype,
        max_new_tokens=args.max_new_tokens,
        attribution_offload=None if args.attribution_offload == "none" else args.attribution_offload,
        max_feature_nodes=args.max_feature_nodes,
    )

    print(f"\nDrawing {args.n} prompts from {args.corpus_model}.{args.split}...")
    triples = list(iter_equilibrium_triples(
        human_source="webtext",
        model_source=args.corpus_model,
        split=args.split,
        k_words=args.k_words,
        data_dir=args.data_dir,
        n=args.n,
    ))

    blockchain = Blockchain(difficulty=1) if args.chain_out else None

    runs: List[dict] = []
    for idx, (prompt, _human, _corpus_model_response) in enumerate(triples):
        print(f"\n--- Prompt {idx} ({len(prompt.split())} words) ---")
        print(f"  prompt: {prompt[:120]!r}")
        response, graph = call(prompt)
        print(f"  response: {response[:120]!r}")
        print(f"  attribution graph: nodes={getattr(graph, 'n_active_features', '?')}")

        report = build_report(prompt, response)
        passes = report.at_equilibrium
        cost = report.typing_cost_seconds(cps=args.cps)
        print(f"  equilibrium: at_equilibrium={passes}  failing={report.failing()}  cost={cost:.1f}s")

        if blockchain is not None:
            block_info = chain_equilibrium_run(
                blockchain=blockchain,
                prompt=prompt,
                response=response,
                model_id=f"huggingface:{args.hf_model}",
                report=report,
                session_id=f"ct_demo:{idx}",
                cps=args.cps,
                attribution_graph=graph,
                extra={"corpus_index": idx, "transcoder_set": args.hf_transcoder_set},
            )
            print(f"  chained: block #{block_info['block_index']}  "
                  f"graph_hash={block_info['payload']['attribution_graph_hash'][:16]}...")
            runs.append(block_info)

    if blockchain is not None and args.chain_out:
        blockchain.save_to_file(str(args.chain_out))
        print(f"\nWrote chain to {args.chain_out} ({len(blockchain.chain)} blocks, "
              f"valid={blockchain.is_chain_valid()})")

    if args.out:
        summary = {
            "config": {
                "hf_model": args.hf_model,
                "hf_transcoder_set": args.hf_transcoder_set,
                "n_prompts": len(triples),
            },
            "runs": [
                {k: v for k, v in r["payload"].items() if k != "extra"} | {"block_index": r["block_index"]}
                for r in runs
            ],
        }
        args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
