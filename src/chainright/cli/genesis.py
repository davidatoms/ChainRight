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


if __name__ == "__main__":
    genesis()
