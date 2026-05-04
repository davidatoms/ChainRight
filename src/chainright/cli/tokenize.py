#!/usr/bin/env python3
"""CLI command for comparing tokenizations of the same text."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

import click

from chainright.tokenization import build_tokenization_report
from chainright.blockchain import Blockchain


def _build_genesis_data() -> str:
    """Build genesis block data from pretraining dataset and model info.
    
    Returns a JSON string containing dataset metadata and model configuration.
    """
    genesis_info = {
        "type": "TOKENIZER_CHAIN",
        "purpose": "Pretraining dataset and trained model genesis block",
        "created": date.today().isoformat(),
        "dataset": {
            "name": "chainright-pretraining-corpus",
            "sources": [
                "gpt-2-output-dataset",
                "monolith-pretrain-data",
                "user-contributed-content"
            ],
            "total_tokens_estimated": 0,  # Will be updated during training
            "encoding": "utf-8"
        },
        "model": {
            "architecture": "transformer-based",
            "vocab_size": 50257,
            "hidden_size": 768,
            "num_layers": 12,
            "num_heads": 12,
            "training_steps": 0,
            "learning_rate": 5e-4
        }
    }
    return json.dumps(genesis_info)


def _get_tokenizer_blockchain() -> Blockchain:
    """Load or create the tokenizer blockchain."""
    ledger_path = Path.home() / ".chainright" / "tokenizer_chain.json"
    
    if ledger_path.exists():
        return Blockchain.load_from_file(str(ledger_path))
    else:
        genesis_data = _build_genesis_data()
        blockchain = Blockchain(difficulty=1, genesis_data=genesis_data)
        return blockchain


def _save_tokenizer_blockchain(blockchain: Blockchain) -> None:
    """Save the tokenizer blockchain to disk."""
    ledger_path = Path.home() / ".chainright" / "tokenizer_chain.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    blockchain.save_to_file(str(ledger_path))
from chainright.blockchain import Blockchain


def _print_tokenization_report(report, as_json: bool, blockchain: Optional[Blockchain] = None) -> None:
    """Print a tokenization report in the specified format and optionally store to chain."""
    if as_json:
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        click.echo(f"Input text ({report.character_count} chars, {report.byte_count} bytes):")
        click.echo(report.text)
        click.echo("")

        for view in report.views:
            click.echo(f"{view.name} ({view.count} tokens):")
            if view.name.startswith("tiktoken:"):
                click.echo("  " + ", ".join(view.tokens))
            elif view.count <= 32:
                click.echo("  " + " | ".join(view.tokens))
            else:
                preview = " | ".join(view.tokens[:32])
                click.echo(f"  {preview} | ... ({view.count - 32} more)")
            click.echo("")

    # Store to blockchain if provided
    if blockchain is not None:
        # Add tokenization summary as data to the blockchain
        summary = f"Tokenization of '{report.text[:50]}{'...' if len(report.text) > 50 else ''}': "
        summary += " | ".join([f"{v.name}={v.count}" for v in report.views])
        blockchain.add_data(summary)
        
        # Mine a block and show confirmation
        result = blockchain.mine_pending_data()
        block_index = result["block"].index
        click.echo(f"  [✓ Stored to chain: block #{block_index}]")


@click.command()
@click.argument("text", required=False)
@click.option("--file", "file_path", type=click.Path(path_type=Path, exists=True, dir_okay=False), help="Read text from a file instead of the argument.")
@click.option("--model", default="cl100k_base", show_default=True, help="Optional tiktoken model name if tiktoken is installed.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON instead of a human-readable report.")
@click.option("--interactive", "-i", is_flag=True, help="Enter interactive mode (loop until Ctrl+D).")
@click.option("--no-chain", is_flag=True, help="Do not store tokenizations to the blockchain.")
def tokenize(text: Optional[str], file_path: Optional[Path], model: str, as_json: bool, interactive: bool, no_chain: bool) -> None:
    """Tokenize input text in multiple ways and compare the outputs.
    
    In interactive mode, the tool loops asking for input repeatedly.
    Each tokenization is stored to a local blockchain unless --no-chain is used.
    """
    if file_path is not None:
        text = file_path.read_text(encoding="utf-8")

    # Load blockchain unless disabled
    blockchain = None if no_chain else _get_tokenizer_blockchain()

    # If text is provided, process it once
    if text is not None:
        report = build_tokenization_report(text, model=model)
        _print_tokenization_report(report, as_json, blockchain)
        if blockchain is not None:
            _save_tokenizer_blockchain(blockchain)
        return

    # No text provided: enter interactive mode
    if interactive or (not text and not file_path):
        click.echo("Interactive tokenizer (Ctrl+D or type 'quit' to exit)")
        if blockchain is not None:
            click.echo(f"  [Storing tokenizations to chain: {Path.home() / '.chainright' / 'tokenizer_chain.json'}]")
        click.echo("")
        
        while True:
            try:
                user_input = click.prompt("Enter text to tokenize", default="")
                if user_input.lower() in ("quit", "exit", "q"):
                    click.echo("Goodbye!")
                    break
                if not user_input:
                    continue
                
                report = build_tokenization_report(user_input, model=model)
                _print_tokenization_report(report, as_json, blockchain)
                click.echo("")
            except EOFError:
                click.echo("\nGoodbye!")
                break
            except KeyboardInterrupt:
                click.echo("\n\nInterrupted.")
                break
        
        # Save blockchain at exit
        if blockchain is not None:
            _save_tokenizer_blockchain(blockchain)
