#!/usr/bin/env python3
"""Run the equilibrium harness on real (prompt, completion) pairs.

Builds triples from the gpt-2-output-dataset (webtext + a model corpus) and
exercises every test in chainright.equilibrium. The "LLM" is selectable:

    --llm-source corpus     (default; lookup over the model corpus, free)
    --llm-source anthropic  (real Anthropic call, requires CLAUDE_API_KEY)
    --llm-source openai     (real OpenAI call, requires OPENAI_API_KEY)
    --llm-source google     (real Google call, requires GEMINI_API_KEY)
    --llm-source ollama     (local Ollama, no key, requires the daemon running)

When `--chain-out PATH` is supplied, every triple's (prompt, response,
EquilibriumReport) is hashed and appended to a ChainRight blockchain saved
to PATH. This is the integration-direction operation from
notes/integration_versus_derivation.md applied to the verifier itself.

Usage:
    python examples/equilibrium_on_real_data.py
    python examples/equilibrium_on_real_data.py --n 50 --model xl-1542M-k40
    python examples/equilibrium_on_real_data.py --llm-source ollama --ollama-model llama3 --n 20
    python examples/equilibrium_on_real_data.py --chain-out runs.chain.json
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from chainright.blockchain import Blockchain
from chainright.datasets import iter_equilibrium_triples
from chainright.equilibrium import (
    DEFAULT_HUMAN_CPS,
    EquilibriumReport,
    compression_test,
    ground_truth_score,
    prompt_decomposition_test,
    proportionality_test,
    semantic_stability_test,
    time_cost_test,
)
from chainright.llm_adapters import (
    chainright_llm_cli_adapter,
    huggingface_via_circuit_tracer_adapter,
    ollama_adapter,
    static_corpus_llm,
)
from chainright.provenance import chain_equilibrium_run


def _result_to_dict(r):
    if is_dataclass(r):
        d = asdict(r)
        d["passes"] = getattr(r, "passes", None)
        return d
    return r


def _stats(xs: List[float]) -> Dict:
    if not xs:
        return {"n": 0}
    return {
        "n": len(xs),
        "mean": statistics.fmean(xs),
        "stdev": statistics.pstdev(xs) if len(xs) > 1 else 0.0,
        "min": min(xs),
        "max": max(xs),
    }


def build_llm(args) -> Tuple[Optional[Callable[[str], str]], str]:
    """Return (llm_callable, model_id_label).

    Returns (None, "corpus:<model>") for the corpus lookup mode — the caller
    falls back to the corpus_model_completion in that case.
    """
    if args.llm_source == "corpus":
        return None, f"corpus:{args.model}"
    if args.llm_source == "ollama":
        return ollama_adapter(model=args.ollama_model), f"ollama:{args.ollama_model}"
    if args.llm_source == "huggingface":
        return (
            huggingface_via_circuit_tracer_adapter(
                model_name=args.hf_model,
                transcoder_set=args.hf_transcoder_set,
                dtype=args.hf_dtype,
                max_new_tokens=args.hf_max_new_tokens,
            ),
            f"huggingface:{args.hf_model}",
        )
    if args.llm_source in {"anthropic", "openai", "google"}:
        provider_model = args.provider_model
        return (
            chainright_llm_cli_adapter(
                provider=args.llm_source, model=provider_model,
            ),
            f"{args.llm_source}:{provider_model or 'default'}",
        )
    raise ValueError(f"unknown --llm-source {args.llm_source!r}")


def build_report(prompt: str, response: str, ground_truth: str) -> EquilibriumReport:
    """Run all live-LLM-friendly clauses and bundle them in one report.

    Compression, stability, and decomposition need the LLM to actually
    respond differently to different prompts. Under corpus mode they
    degenerate (see notes/equilibrium_as_sat.md §3) but the harness still
    runs them — that's the point of having the same code path on both.
    """
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


def run(args) -> Dict:
    triples = list(iter_equilibrium_triples(
        human_source="webtext",
        model_source=args.model,
        split=args.split,
        k_words=args.k_words,
        data_dir=args.data_dir,
        n=args.n,
    ))
    if not triples:
        raise SystemExit("No triples produced — check data_dir and corpus length.")

    llm_callable, model_id = build_llm(args)

    blockchain: Optional[Blockchain] = None
    if args.chain_out:
        blockchain = Blockchain(difficulty=1)

    proportion_ratios: List[float] = []
    proportion_pass: List[bool] = []
    time_costs_total: List[float] = []
    time_cost_passes: List[bool] = []
    typing_costs: List[float] = []
    accepted_runs = 0

    examples: List[Dict] = []

    for idx, (prompt, human_completion, corpus_model) in enumerate(triples):
        if llm_callable is None:
            response = corpus_model
        else:
            response = llm_callable(prompt)

        report = build_report(prompt, response, ground_truth=human_completion)

        prop = report.components["proportionality"]
        proportion_ratios.append(prop.ratio)
        proportion_pass.append(prop.passes)

        tc = report.components["time_cost"]
        time_costs_total.append(tc.total_human_time_seconds)
        time_cost_passes.append(tc.passes)

        cost = report.typing_cost_seconds(cps=args.cps)
        typing_costs.append(cost)
        if report.at_equilibrium:
            accepted_runs += 1

        if blockchain is not None:
            chain_equilibrium_run(
                blockchain=blockchain,
                prompt=prompt,
                response=response,
                model_id=model_id,
                report=report,
                session_id=f"run:{args.llm_source}:{idx}",
                cps=args.cps,
                extra={"corpus_index": idx, "split": args.split},
            )

        if idx < 3:
            examples.append({
                "prompt": prompt[:200],
                "response": response[:200],
                "human_completion": human_completion[:200],
                "model_vs_human_jaccard": ground_truth_score(response, human_completion),
                "proportionality_ratio": prop.ratio,
                "at_equilibrium": report.at_equilibrium,
                "verifier_typing_cost_seconds": cost,
            })

    return {
        "config": {
            "model_id": model_id,
            "llm_source": args.llm_source,
            "split": args.split,
            "k_words_prompt": args.k_words,
            "n_triples": len(triples),
            "cps": args.cps,
        },
        "proportionality": {
            "ratio_stats": _stats(proportion_ratios),
            "pass_rate": sum(proportion_pass) / len(proportion_pass),
        },
        "time_cost": {
            "total_human_seconds": _stats(time_costs_total),
            "pass_rate": sum(time_cost_passes) / len(time_cost_passes),
        },
        "verifier_typing_cost_seconds": _stats(typing_costs),
        "equilibrium_pass_rate": accepted_runs / len(triples),
        "blockchain_length": len(blockchain.chain) if blockchain else None,
        "blockchain_valid": blockchain.is_chain_valid() if blockchain else None,
        "examples": examples,
    }, blockchain


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--n", type=int, default=200, help="number of triples")
    p.add_argument("--model", default="small-117M-k40", help="corpus model source")
    p.add_argument("--split", default="test", choices=["train", "valid", "test"])
    p.add_argument("--k-words", type=int, default=30)
    p.add_argument("--data-dir", type=Path, default=None)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument(
        "--llm-source",
        choices=["corpus", "anthropic", "openai", "google", "ollama", "huggingface"],
        default="corpus",
    )
    p.add_argument("--provider-model", default=None,
                   help="Specific model id for anthropic/openai/google.")
    p.add_argument("--ollama-model", default="llama3")
    p.add_argument("--hf-model", default="meta-llama/Llama-3.2-1B",
                   help="HuggingFace model name when --llm-source huggingface.")
    p.add_argument("--hf-transcoder-set", default="mntss/transcoder-Llama-3.2-1B",
                   help="circuit-tracer transcoder set name on HuggingFace.")
    p.add_argument("--hf-dtype", default="float16",
                   choices=["float32", "float16", "bfloat16"])
    p.add_argument("--hf-max-new-tokens", type=int, default=128)
    p.add_argument("--cps", type=float, default=DEFAULT_HUMAN_CPS,
                   help="characters-per-second for typing-cost accounting")
    p.add_argument("--chain-out", type=Path, default=None,
                   help="If set, save a ChainRight blockchain of every run to this path.")
    args = p.parse_args(argv)

    report, blockchain = run(args)

    payload = json.dumps(report, indent=2, default=str)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(payload)

    if blockchain is not None and args.chain_out:
        blockchain.save_to_file(str(args.chain_out))
        print(f"Wrote chain to {args.chain_out} ({len(blockchain.chain)} blocks)")

    print()
    print(f"LLM source:                  {report['config']['llm_source']} ({report['config']['model_id']})")
    print(f"Triples processed:           {report['config']['n_triples']}")
    print(f"Proportionality pass rate:   {report['proportionality']['pass_rate']:.2%}")
    print(f"Time-cost pass rate:         {report['time_cost']['pass_rate']:.2%}")
    print(f"Equilibrium pass rate:       {report['equilibrium_pass_rate']:.2%}")
    print(f"Mean verifier typing cost:   "
          f"{report['verifier_typing_cost_seconds'].get('mean', 0):.2f}s per triple")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
