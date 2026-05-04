#!/usr/bin/env python3
"""
Genesis CLI Command

Commands for building and managing the Genesis Block from pretraining corpus.

Usage:
    chainright genesis init --sources "library/"
    chainright genesis show --source "CLRS"
    chainright genesis search "sorting"
    chainright genesis cite concept_id
    chainright genesis check "my text"
"""

import json
import click
from pathlib import Path
from typing import Optional

from chainright.genesis_builder import GenesisBuilder
from chainright.knowledge_hierarchy import Metalocation
from chainright.blockchain import Blockchain


@click.group()
def genesis():
    """Genesis Block management - pretraining corpus with metalocation."""
    pass


@genesis.command()
@click.option('--sources', '-s', required=True, 
              help='Path to directory with source files (PDFs, JSONs, etc.)')
@click.option('--output', '-o', default='.chainright/genesis',
              help='Output directory for genesis data')
def init(sources: str, output: str) -> None:
    """
    Initialize Genesis Block from pretraining corpus.
    
    Loads books, papers, and other sources and creates hierarchical
    objects with complete metalocation tracking.
    
    Usage:
        chainright genesis init --sources ~/library
        chainright genesis init -s books/ -o .genesis_output
    """
    sources_path = Path(sources)
    
    if not sources_path.exists():
        click.echo(f"❌ Source directory not found: {sources}")
        return
    
    builder = GenesisBuilder(output_path=output)
    
    click.echo(f"\n📚 Initializing Genesis Block from: {sources}\n")
    
    # Find JSON files (for demo, would support PDFs, EPUBs, etc.)
    json_files = list(sources_path.glob("*.json"))
    
    if not json_files:
        click.echo("⚠ No JSON files found (demo supports JSON)")
        return
    
    # Load and process each file
    with click.progressbar(json_files, label="Processing sources") as bar:
        for json_file in bar:
            try:
                with open(json_file) as f:
                    data = json.load(f)
                
                if data.get("type") == "book":
                    builder.add_book_from_dict(data)
                elif data.get("type") == "paper":
                    builder.add_paper_from_dict(data)
            except Exception as e:
                click.echo(f"⚠ Error processing {json_file.name}: {e}")
    
    # Extract concepts
    click.echo("\n🔍 Extracting concepts...")
    for isbn in builder.hierarchy.books.keys():
        builder.extract_concepts(isbn)
    
    # Build merkle tree
    click.echo("🌳 Building Merkle tree...")
    merkle_root = builder.build_merkle_tree()
    
    # Create genesis block
    click.echo("⛓ Creating Genesis Block...")
    genesis_block = builder.create_genesis_block()
    
    # Save
    click.echo("💾 Saving to disk...")
    files = builder.save_to_files()
    
    # Show summary
    summary = builder.get_summary()
    
    click.echo(f"\n✅ Genesis Block created!\n")
    click.echo(f"  Block Hash: {genesis_block.hash[:16]}...")
    click.echo(f"  Merkle Root: {merkle_root[:16]}...")
    click.echo(f"  \n  📊 Statistics:")
    click.echo(f"    Sources: {summary['total_sources']}")
    click.echo(f"    Concepts: {summary['total_concepts']:,}")
    click.echo(f"    Books: {summary['total_books']}")
    click.echo(f"    Chapters: {summary['total_chapters']}")
    click.echo(f"    Sections: {summary['total_sections']}")
    click.echo(f"    Paragraphs: {summary['total_paragraphs']}")
    click.echo(f"    Sentences: {summary['total_sentences']}")
    
    click.echo(f"\n  💾 Files saved to: {Path(output).absolute()}")
    for file_type, file_path in files.items():
        click.echo(f"    - {file_type}: {file_path}")


@genesis.command()
@click.option('--source', '-s', default=None, help='Filter by source (ISBN/author)')
@click.option('--limit', '-l', default=10, help='Max items to show')
def show(source: Optional[str], limit: int) -> None:
    """
    Show contents of Genesis Block.
    
    Usage:
        chainright genesis show
        chainright genesis show --source "CLRS"
        chainright genesis show --source "arXiv" --limit 20
    """
    genesis_path = Path.home() / ".chainright" / "genesis" / "hierarchy.json"
    
    if not genesis_path.exists():
        click.echo("Genesis Block not found. Run 'chainright genesis init' first.")
        return
    
    with open(genesis_path) as f:
        hierarchy = json.load(f)
    
    click.echo(f"\n📚 Genesis Block Contents\n")
    
    books = hierarchy.get("books", [])
    
    if source:
        books = [b for b in books if source.lower() in b["title"].lower() or
                                     source.lower() in b["author"].lower()]
    
    for i, book in enumerate(books[:limit], 1):
        click.echo(f"{i}. {book['title']}")
        click.echo(f"   Author: {book.get('author', 'Unknown')}")
        click.echo(f"   ISBN: {book.get('isbn', 'N/A')}")
        click.echo(f"   Year: {book.get('year', '?')}")
        click.echo(f"   Chapters: {book.get('chapter_count', 0)}")
        click.echo(f"   Concepts: {book.get('concept_count', 0):,}")
        click.echo()


@genesis.command()
@click.argument('query')
@click.option('--limit', '-l', default=10, help='Max results')
def search(query: str, limit: int) -> None:
    """
    Search Genesis concepts.
    
    Usage:
        chainright genesis search "sorting"
        chainright genesis search "algorithm" --limit 20
    """
    concepts_path = Path.home() / ".chainright" / "genesis" / "concepts.json"
    
    if not concepts_path.exists():
        click.echo("Genesis Block not found. Run 'chainright genesis init' first.")
        return
    
    with open(concepts_path) as f:
        concepts = json.load(f)
    
    # Search in text and keywords
    results = []
    for concept in concepts:
        if (query.lower() in concept["text"].lower() or
            any(query.lower() in k.lower() for k in concept.get("keywords", []))):
            results.append(concept)
    
    if not results:
        click.echo(f"No concepts found matching '{query}'")
        return
    
    click.echo(f"\n🔍 Found {len(results)} concept(s) matching '{query}':\n")
    
    for i, concept in enumerate(results[:limit], 1):
        metaloc = concept["metalocation"]
        click.echo(f"{i}. {concept['text']}")
        click.echo(f"   Source: {metaloc['source_title']} ({metaloc['source_year']})")
        click.echo(f"   Location: {metaloc['section_title']}, "
                  f"Para {metaloc['paragraph_number']}")
        click.echo(f"   Keywords: {', '.join(concept.get('keywords', [])[:5])}")
        click.echo()


@genesis.command()
@click.argument('concept_id')
@click.option('--style', '-s', type=click.Choice(['APA', 'MLA', 'Chicago', 'BibTeX']),
              default='APA', help='Citation format')
def cite(concept_id: str, style: str) -> None:
    """
    Generate citation for a Genesis concept.
    
    Usage:
        chainright genesis cite concept_123
        chainright genesis cite concept_456 --style MLA
    """
    concepts_path = Path.home() / ".chainright" / "genesis" / "concepts.json"
    
    if not concepts_path.exists():
        click.echo("Genesis Block not found.")
        return
    
    with open(concepts_path) as f:
        concepts = json.load(f)
    
    concept = next((c for c in concepts if c["id"] == concept_id), None)
    if not concept:
        click.echo(f"Concept {concept_id} not found")
        return
    
    metaloc = concept["metalocation"]
    
    click.echo(f"\n📖 Citation for: {concept['text'][:60]}...\n")
    
    author = metaloc["source_author"]
    title = metaloc["source_title"]
    year = metaloc["source_year"]
    page = metaloc["page_number"]
    
    if style == "APA":
        citation = (f"{author} ({year}). {title}. "
                   f"p. {page}.")
    elif style == "MLA":
        citation = (f"{author}. \"{title}.\" {year}. "
                   f"p. {page}.")
    elif style == "Chicago":
        citation = (f"{author}. {title}. {year}. "
                   f"Accessed at p. {page}.")
    else:  # BibTeX
        citation = (f"@book{{{concept_id},\n"
                   f"  author = {{{author}}},\n"
                   f"  title = {{{title}}},\n"
                   f"  year = {{{year}}},\n"
                   f"  page = {{{page}}}\n}}")
    
    click.echo(f"[{style}]")
    click.echo(citation)
    click.echo()


@genesis.command()
@click.argument('text')
@click.option('--threshold', '-t', default=0.85, help='Plagiarism threshold')
def check(text: str, threshold: float) -> None:
    """
    Check text against Genesis Block for plagiarism/derivation.
    
    Compares new text against pretraining corpus and calculates
    similarity scores to detect:
    - Exact copies (> 0.95)
    - Paraphrases (0.70-0.95)
    - Novel work (< 0.70)
    
    Usage:
        chainright genesis check "An algorithm is a procedure..."
        chainright genesis check "my text" --threshold 0.80
    """
    concepts_path = Path.home() / ".chainright" / "genesis" / "concepts.json"
    
    if not concepts_path.exists():
        click.echo("Genesis Block not found.")
        return
    
    with open(concepts_path) as f:
        concepts = json.load(f)
    
    # Simple similarity check (would use embedding distance with Monolith)
    from difflib import SequenceMatcher
    
    matches = []
    for concept in concepts:
        ratio = SequenceMatcher(None, text.lower(), 
                               concept["text"].lower()).ratio()
        if ratio > 0.6:  # Lower threshold for demo
            matches.append((concept, ratio))
    
    matches.sort(key=lambda x: x[1], reverse=True)
    
    click.echo(f"\n🔎 Checking text against Genesis Block\n")
    
    if not matches:
        click.echo("✅ No significant matches found (likely novel)")
        return
    
    highest_match = matches[0]
    similarity = highest_match[1]
    concept = highest_match[0]
    
    if similarity > threshold:
        click.echo(f"⚠️ PLAGIARISM DETECTED")
        click.echo(f"  Similarity: {similarity:.1%}")
        click.echo(f"  Matches: {concept['text'][:80]}...")
        click.echo(f"  Source: {concept['metalocation']['source_title']}")
    elif similarity > 0.70:
        click.echo(f"📝 DERIVATION DETECTED")
        click.echo(f"  Similarity: {similarity:.1%}")
        click.echo(f"  Needs citation: {concept['text'][:80]}...")
        click.echo(f"  Source: {concept['metalocation']['source_title']}")
    else:
        click.echo(f"✅ LIKELY NOVEL")
        click.echo(f"  Max similarity: {similarity:.1%}")
        click.echo(f"  (Below threshold of {threshold:.0%})")
    
    click.echo()


@genesis.command()
def status() -> None:
    """Show Genesis Block status and statistics."""
    stats_path = Path.home() / ".chainright" / "genesis" / "statistics.json"
    
    if not stats_path.exists():
        click.echo("Genesis Block not initialized.")
        return
    
    with open(stats_path) as f:
        stats = json.load(f)
    
    click.echo(f"\n📊 Genesis Block Status\n")
    click.echo(f"  Total Books: {stats.get('total_books', 0)}")
    click.echo(f"  Total Chapters: {stats.get('total_chapters', 0)}")
    click.echo(f"  Total Sections: {stats.get('total_sections', 0)}")
    click.echo(f"  Total Paragraphs: {stats.get('total_paragraphs', 0)}")
    click.echo(f"  Total Sentences: {stats.get('total_sentences', 0)}")
    click.echo(f"  Total Concepts: {stats.get('total_concepts', 0):,}")
    click.echo(f"  Avg Concepts/Book: {stats.get('avg_concepts_per_book', 0):.0f}")
    click.echo()


@genesis.command(name="inspect-chain")
@click.option("--chain", type=str, default="tokenizer_chain.json", help="Chain file to inspect (relative to ~/.chainright/).")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON instead of pretty-printed.")
def inspect_chain(chain: str, as_json: bool) -> None:
    """Inspect the genesis block of a blockchain (dataset + model metadata)."""
    chain_path = Path.home() / ".chainright" / chain
    
    if not chain_path.exists():
        click.echo(f"Error: Blockchain file not found at {chain_path}", err=True)
        return
    
    blockchain = Blockchain.load_from_file(str(chain_path))
    
    if not blockchain.chain:
        click.echo("Error: Blockchain is empty", err=True)
        return
    
    genesis_block = blockchain.chain[0]
    
    # Try to parse the data as JSON (dataset + model info)
    try:
        genesis_data = json.loads(genesis_block.data)
        
        if as_json:
            click.echo(json.dumps(genesis_data, indent=2))
        else:
            click.echo(f"\n=== Genesis Block (Blockchain) #{genesis_block.index} ===")
            click.echo(f"Hash: {genesis_block.hash}")
            click.echo(f"Timestamp: {genesis_block.timestamp}")
            click.echo(f"Difficulty: {genesis_block.difficulty}")
            click.echo("")
            
            if isinstance(genesis_data, dict):
                if "type" in genesis_data:
                    click.echo(f"Type: {genesis_data['type']}")
                if "purpose" in genesis_data:
                    click.echo(f"Purpose: {genesis_data['purpose']}")
                if "created" in genesis_data:
                    click.echo(f"Created: {genesis_data['created']}")
                
                if "dataset" in genesis_data:
                    dataset = genesis_data["dataset"]
                    click.echo("")
                    click.echo("[Dataset]")
                    click.echo(f"  Name: {dataset.get('name', 'N/A')}")
                    click.echo(f"  Sources: {', '.join(dataset.get('sources', []))}")
                    click.echo(f"  Total Tokens: {dataset.get('total_tokens_estimated', 0):,}")
                    click.echo(f"  Encoding: {dataset.get('encoding', 'N/A')}")
                
                if "model" in genesis_data:
                    model = genesis_data["model"]
                    click.echo("")
                    click.echo("[Model]")
                    click.echo(f"  Architecture: {model.get('architecture', 'N/A')}")
                    click.echo(f"  Vocab Size: {model.get('vocab_size', 'N/A'):,}")
                    click.echo(f"  Hidden Size: {model.get('hidden_size', 'N/A')}")
                    click.echo(f"  Num Layers: {model.get('num_layers', 'N/A')}")
                    click.echo(f"  Num Heads: {model.get('num_heads', 'N/A')}")
                    click.echo(f"  Training Steps: {model.get('training_steps', 0):,}")
                    click.echo(f"  Learning Rate: {model.get('learning_rate', 'N/A')}")
                    if "checkpoint_hash" in model:
                        click.echo(f"  Checkpoint Hash: {model['checkpoint_hash']}")
            else:
                click.echo(json.dumps(genesis_data, indent=2))
            click.echo()
    
    except json.JSONDecodeError:
        # If not JSON, just show as plain text
        if as_json:
            click.echo(json.dumps({"error": "Genesis data is not JSON"}, indent=2))
        else:
            click.echo(f"\n=== Genesis Block (Blockchain) #{genesis_block.index} ===")
            click.echo(f"Hash: {genesis_block.hash}")
            click.echo(f"Data: {genesis_block.data}")
            click.echo()


@genesis.command(name="update-chain")
@click.option("--chain", type=str, default="tokenizer_chain.json", help="Chain file to update (relative to ~/.chainright/).")
@click.option("--total-tokens", type=int, help="Update total tokens in dataset.")
@click.option("--training-steps", type=int, help="Update training steps for model.")
@click.option("--learning-rate", type=float, help="Update learning rate for model.")
@click.option("--source", type=str, multiple=True, help="Add a new data source (can be used multiple times).")
@click.option("--checkpoint-hash", type=str, help="Add model checkpoint hash.")
def update_chain(
    chain: str,
    total_tokens: Optional[int],
    training_steps: Optional[int],
    learning_rate: Optional[float],
    source: tuple[str, ...],
    checkpoint_hash: Optional[str]
) -> None:
    """Update genesis block metadata (dataset and model info).
    
    This creates a new blockchain with the updated genesis block.
    Note: This replaces the genesis block, so the chain hash will change.
    
    Usage:
        chainright genesis update-chain --total-tokens 1000000000
        chainright genesis update-chain --training-steps 50000 --learning-rate 0.0001
        chainright genesis update-chain --source "additional-dataset" --checkpoint-hash "abc123"
    """
    chain_path = Path.home() / ".chainright" / chain
    
    if not chain_path.exists():
        click.echo(f"Error: Blockchain file not found at {chain_path}", err=True)
        return
    
    blockchain = Blockchain.load_from_file(str(chain_path))
    
    if not blockchain.chain:
        click.echo("Error: Blockchain is empty", err=True)
        return
    
    genesis_block = blockchain.chain[0]
    
    # Parse current genesis data
    try:
        genesis_data = json.loads(genesis_block.data)
    except json.JSONDecodeError:
        click.echo("Error: Genesis data is not valid JSON", err=True)
        return
    
    click.echo(f"\n🔄 Updating genesis block...\n")
    
    # Update values
    if total_tokens is not None:
        if "dataset" in genesis_data:
            genesis_data["dataset"]["total_tokens_estimated"] = total_tokens
            click.echo(f"✓ Updated total_tokens to {total_tokens:,}")
    
    if training_steps is not None:
        if "model" in genesis_data:
            genesis_data["model"]["training_steps"] = training_steps
            click.echo(f"✓ Updated training_steps to {training_steps:,}")
    
    if learning_rate is not None:
        if "model" in genesis_data:
            genesis_data["model"]["learning_rate"] = learning_rate
            click.echo(f"✓ Updated learning_rate to {learning_rate}")
    
    if source:
        if "dataset" in genesis_data:
            current_sources = genesis_data["dataset"].get("sources", [])
            for new_source in source:
                if new_source not in current_sources:
                    current_sources.append(new_source)
                    click.echo(f"✓ Added data source: {new_source}")
            genesis_data["dataset"]["sources"] = current_sources
    
    if checkpoint_hash is not None:
        if "model" in genesis_data:
            genesis_data["model"]["checkpoint_hash"] = checkpoint_hash
            click.echo(f"✓ Added checkpoint_hash: {checkpoint_hash}")
    
    # Serialize updated genesis data
    updated_genesis_str = json.dumps(genesis_data)
    
    # Create new blockchain with updated genesis
    new_blockchain = Blockchain(difficulty=blockchain.base_difficulty, genesis_data=updated_genesis_str)
    
    # Save updated blockchain
    new_blockchain.save_to_file(str(chain_path))
    click.echo(f"\n✓ Genesis block updated and saved to {chain_path}")
    click.echo(f"New genesis hash: {new_blockchain.chain[0].hash}\n")


if __name__ == "__main__":
    genesis()
