#!/usr/bin/env python3
"""CLI commands for copyright registration and verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from chainright.content_fingerprint import (
    ContentFingerprint,
    compute_content_hash,
    compute_text_hash,
    get_embedding_placeholder,
)
from chainright.copyright_blockchain import CopyrightBlockchain


def _parse_attributes(pairs: tuple[str, ...]) -> dict[str, str]:
    """Parse repeated key=value pairs into a dictionary."""
    attributes: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise click.BadParameter(f"Expected key=value, got: {pair}")
        key, value = pair.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise click.BadParameter(f"Empty attribute key in: {pair}")
        attributes[key] = value
    return attributes


def _get_copyright_blockchain() -> CopyrightBlockchain:
    """Load or create the copyright blockchain."""
    ledger_path = Path.home() / ".chainright" / "copyright_chain.json"
    
    if ledger_path.exists():
        return CopyrightBlockchain.load_from_file(str(ledger_path))
    else:
        return CopyrightBlockchain(difficulty=2)


def _save_copyright_blockchain(copyright_chain: CopyrightBlockchain) -> None:
    """Save copyright blockchain to disk."""
    ledger_path = Path.home() / ".chainright" / "copyright_chain.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    copyright_chain.save_to_file(str(ledger_path))


@click.group(name="copyright")
def copyright_group() -> None:
    """Manage copyrighted works and detect AI usage."""
    pass


@copyright_group.command(name="register")
@click.argument("file_path", type=click.Path(path_type=Path, exists=True, dir_okay=False))
@click.option("--title", "-t", required=True, help="Title of the work")
@click.option("--description", "-d", required=True, help="Description of the work")
@click.option("--creator", "-c", required=True, help="Creator name (e.g., 'Taylor Swift')")
@click.option("--wallet", "-w", required=True, help="Creator wallet address (public key)")
@click.option("--license", "-l", required=True, 
              type=click.Choice(["CC-BY", "CC-BY-SA", "CC-BY-NC", "MIT", "Commercial", "All-Rights-Reserved", "Public-Domain"]),
              help="License type for the work")
@click.option("--contact", required=True, help="Email or website for licensing inquiries")
@click.option("--guess", "guessed_attributes", multiple=True, help="Guessed attributes as key=value (repeatable)")
@click.option("--actual", "actual_attributes", multiple=True, help="Actual attributes as key=value (repeatable, optional)")
def register_work(file_path: Path, title: str, description: str, creator: str, wallet: str, license: str, contact: str, guessed_attributes: tuple[str, ...], actual_attributes: tuple[str, ...]) -> None:
    """Register a copyrighted work on the blockchain with licensing information.
    
    Example:
        chainright copyright register my_song.txt --title "Anti-Hero" --description "A song about self-reflection" \\
                    --creator "Taylor Swift" --wallet "0x1234..." --license "Commercial" --contact "taylor@example.com" \
                    --guess artist=Taylor Swift --guess genre=pop
    """
    try:
        guessed_attribute_map = _parse_attributes(guessed_attributes)
        actual_attribute_map = _parse_attributes(actual_attributes) if actual_attributes else {}

        # Read and fingerprint the work
        with open(file_path, "rb") as f:
            content_bytes = f.read()
        
        content_hash = compute_content_hash(file_path)
        file_size = len(content_bytes)
        
        # Determine content type
        content_type = "text" if file_path.suffix in {".txt", ".md"} else "binary"
        if file_path.suffix in {".mp3", ".wav", ".flac"}:
            content_type = "audio"
        elif file_path.suffix in {".jpg", ".png", ".gif"}:
            content_type = "image"
        
        # Get embedding (currently using placeholder)
        if content_type == "text":
            text_content = content_bytes.decode("utf-8", errors="ignore")
            embedding = get_embedding_placeholder(text_content)
        else:
            embedding = None  # For audio/image, would need specialized model
        
        # Create fingerprint
        import time
        fingerprint = ContentFingerprint(
            content_hash=content_hash,
            content_type=content_type,
            file_size=file_size,
            title=title,
            creator_wallet=wallet,
            timestamp=time.time(),
            embedding=embedding,
            embedding_model="monolith-placeholder" if embedding else None,
        )
        
        # Register on blockchain
        copyright_chain = _get_copyright_blockchain()
        record = copyright_chain.register_work(
            fingerprint,
            wallet,
            creator,
            title,
            description,
            license,
            contact,
            guessed_attributes=guessed_attribute_map,
        )

        verification_result = None
        if actual_attribute_map:
            verification_result = copyright_chain.verify_work_attributes(content_hash, actual_attribute_map)

        _save_copyright_blockchain(copyright_chain)
        
        click.echo(f"\n✅ Work registered on copyright registry!")
        click.echo(f"  Title: {title}")
        click.echo(f"  Creator: {creator}")
        click.echo(f"  License: {license}")
        click.echo(f"  Licensing Contact: {contact}")
        click.echo(f"  Content Hash: {content_hash[:16]}...")
        click.echo(f"  File Size: {file_size:,} bytes")
        click.echo(f"  Block Hash: {record.block_hash[:16]}...")
        if guessed_attribute_map:
            click.echo(f"  Guessed Attributes: {', '.join(f'{k}={v}' for k, v in guessed_attribute_map.items())}")
        if verification_result:
            click.echo(f"  Verification Score: {verification_result.score:.0%}")
            click.echo(f"  Matched: {', '.join(verification_result.matched_attributes) or 'none'}")
            click.echo(f"  Mismatched: {', '.join(verification_result.mismatched_attributes) or 'none'}")
        click.echo(f"\n📋 Anyone can now look up your work and find how to license it properly.\n")
    
    except Exception as e:
        click.echo(f"❌ Error registering work: {e}", err=True)


@copyright_group.command(name="lookup")
@click.argument("content_hash")
def lookup_work(content_hash: str) -> None:
    """Look up a work by its content hash to see licensing information.
    
    Example:
        chainright copyright lookup abc123def456...
    """
    copyright_chain = _get_copyright_blockchain()
    
    licensing_info = copyright_chain.get_licensing_info(content_hash)
    if not licensing_info:
        click.echo(f"❌ No work found with hash: {content_hash}\n")
        return
    
    click.echo(f"\n📖 Work Licensing Information\n")
    click.echo(f"Title: {licensing_info['work_title']}")
    click.echo(f"Description: {licensing_info['work_description']}")
    click.echo(f"\nCreator: {licensing_info['creator']}")
    click.echo(f"Wallet: {licensing_info['creator_wallet']}")
    click.echo(f"\nLicense Type: {licensing_info['license_type']}")
    click.echo(f"Licensing Contact: {licensing_info['licensing_contact']}")
    if licensing_info.get("guessed_attributes"):
        guessed = licensing_info["guessed_attributes"]
        click.echo(f"\nGuessed Attributes: {', '.join(f'{k}={v}' for k, v in guessed.items())}")
    if licensing_info.get("verification_result"):
        verification = licensing_info["verification_result"]
        click.echo(f"Verification Score: {verification.get('score', 0):.0%}")
        click.echo(f"Matched Attributes: {', '.join(verification.get('matched_attributes', [])) or 'none'}")
        click.echo(f"Mismatched Attributes: {', '.join(verification.get('mismatched_attributes', [])) or 'none'}")
    click.echo(f"\nRegistered: {licensing_info['registered_at_iso']}")
    click.echo(f"Content Hash: {licensing_info['content_hash']}")
    click.echo(f"Block Hash: {licensing_info['block_hash'][:16]}...")
    click.echo(f"\n✅ {licensing_info['proof']}\n")


@copyright_group.command(name="verify")
@click.argument("content_hash")
@click.option("--actual", "actual_attributes", multiple=True, required=True, help="Actual attributes as key=value (repeatable)")
def verify_work(content_hash: str, actual_attributes: tuple[str, ...]) -> None:
    """Verify guessed attributes against actual attributes and store the result on-chain."""
    copyright_chain = _get_copyright_blockchain()
    actual_attribute_map = _parse_attributes(actual_attributes)

    record = copyright_chain.lookup_by_hash(content_hash)
    if not record:
        click.echo(f"❌ No work found with hash: {content_hash}\n")
        return

    result = copyright_chain.verify_work_attributes(content_hash, actual_attribute_map)
    if result is None:
        click.echo(f"❌ Verification failed for hash: {content_hash}\n")
        return

    _save_copyright_blockchain(copyright_chain)

    click.echo(f"\n✅ Verification stored on-chain")
    click.echo(f"Work: {record.work_title}")
    click.echo(f"Score: {result.score:.0%}")
    click.echo(f"Matched: {', '.join(result.matched_attributes) or 'none'}")
    click.echo(f"Mismatched: {', '.join(result.mismatched_attributes) or 'none'}")
    click.echo(f"Lean Trace:")
    for line in result.proof_trace:
        click.echo(f"  {line}")


@copyright_group.command(name="list")
@click.option("--creator-wallet", "-w", help="Filter by creator wallet")
@click.option("--creator-name", "-c", help="Filter by creator name (substring match)")
@click.option("--license", "-l", help="Filter by license type")
def list_works(creator_wallet: Optional[str], creator_name: Optional[str], license: Optional[str]) -> None:
    """List all registered copyrighted works with licensing information."""
    copyright_chain = _get_copyright_blockchain()
    all_records = copyright_chain.get_all_records()
    
    # Apply filters
    records = all_records
    if creator_wallet:
        records = [r for r in records if r.creator_wallet == creator_wallet]
    if creator_name:
        records = [r for r in records if creator_name.lower() in r.creator_name.lower()]
    if license:
        records = [r for r in records if r.license_type == license]
    
    if not records:
        click.echo("📭 No works registered.\n")
        return
    
    click.echo(f"\n📚 Registered Works ({len(records)} total)\n")
    
    for i, record in enumerate(records, 1):
        fingerprint = record.fingerprint
        click.echo(f"{i}. {record.work_title}")
        click.echo(f"   Creator: {record.creator_name}")
        click.echo(f"   Description: {record.work_description[:60]}..." if len(record.work_description) > 60 else f"   Description: {record.work_description}")
        click.echo(f"   License: {record.license_type}")
        click.echo(f"   Contact: {record.licensing_contact}")
        click.echo(f"   Wallet: {record.creator_wallet[:12]}...")
        click.echo(f"   Hash: {fingerprint['content_hash'][:16]}...")
        click.echo(f"   Type: {fingerprint['content_type']}")
        click.echo()


@copyright_group.command(name="contact")
@click.argument("content_hash")
def show_licensing_contact(content_hash: str) -> None:
    """Show licensing contact information for a work."""
    copyright_chain = _get_copyright_blockchain()
    
    licensing_info = copyright_chain.get_licensing_info(content_hash)
    if not licensing_info:
        click.echo(f"❌ No work found with hash: {content_hash}\n")
        return
    
    click.echo(f"\n📧 Licensing Contact Information\n")
    click.echo(f"Work: {licensing_info['work_title']}")
    click.echo(f"Creator: {licensing_info['creator']}")
    click.echo(f"License Type: {licensing_info['license_type']}")
    click.echo(f"\nTo license this work, contact:")
    click.echo(f"  {licensing_info['licensing_contact']}\n")


@copyright_group.command(name="chain-status")
def chain_status() -> None:
    """Show the status of the copyright registry blockchain."""
    copyright_chain = _get_copyright_blockchain()
    status = copyright_chain.get_chain_integrity_proof()
    
    click.echo(f"\n⛓️  Copyright Registry Blockchain Status\n")
    click.echo(f"Total Blocks: {status.get('total_blocks', 0)}")
    click.echo(f"Registered Works: {status.get('total_registered_works', 0)}")
    click.echo(f"Chain Head Hash: {status.get('chain_head_hash', 'N/A')[:16]}...")
    click.echo(f"Difficulty: {status.get('difficulty', 'N/A')}")
    click.echo(f"Latest Block Timestamp: {status.get('chain_timestamp', 'N/A')}\n")
