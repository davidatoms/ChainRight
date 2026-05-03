#!/usr/bin/env python3
"""
Genesis System Example - End-to-End Demonstration

This example shows how to:
1. Build a Genesis Block from pretraining corpus
2. Extract concepts with metalocation
3. Search and cite concepts
4. Check text for plagiarism

Run this example:
    python examples/genesis_example.py
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chainright.genesis_builder import GenesisBuilder
from chainright.knowledge_hierarchy import Metalocation


def main():
    print("\n" + "="*70)
    print("ChainRight Genesis System - Complete Example")
    print("="*70 + "\n")
    
    # Step 1: Load sample corpus
    print("📚 Step 1: Load Sample Corpus")
    print("-" * 70)
    
    corpus_file = Path(__file__).parent / "sample_corpus.json"
    
    if not corpus_file.exists():
        print(f"❌ Sample corpus not found at {corpus_file}")
        return
    
    with open(corpus_file) as f:
        corpus = json.load(f)
    
    print(f"✓ Loaded corpus with {len(corpus)} sources")
    for source in corpus:
        print(f"  - {source['title']} ({source['year']})")
    print()
    
    # Step 2: Build Genesis
    print("🏗️  Step 2: Build Genesis Block")
    print("-" * 70)
    
    output_path = ".chainright/genesis_example"
    builder = GenesisBuilder(output_path=output_path)
    
    print(f"Building genesis in: {output_path}")
    
    # Process each source
    for i, source in enumerate(corpus, 1):
        try:
            if source.get("type") == "book":
                print(f"  [{i}/{len(corpus)}] Adding book: {source['title']}")
                builder.add_book_from_dict(source)
            elif source.get("type") == "paper":
                print(f"  [{i}/{len(corpus)}] Adding paper: {source['title']}")
                builder.add_paper_from_dict(source)
        except Exception as e:
            print(f"  ⚠ Error processing {source['title']}: {e}")
    
    print()
    
    # Step 3: Extract Concepts
    print("🔍 Step 3: Extract Concepts")
    print("-" * 70)
    
    total_concepts = 0
    for isbn in builder.hierarchy.books.keys():
        book = builder.hierarchy.books[isbn]
        num_concepts = len(builder.extract_concepts(isbn))
        total_concepts += num_concepts
        print(f"  Extracted {num_concepts} concepts from: {book.title}")
    
    print(f"✓ Total concepts extracted: {total_concepts}")
    print()
    
    # Step 4: Build Merkle Tree
    print("🌳 Step 4: Build Merkle Tree")
    print("-" * 70)
    
    merkle_root = builder.build_merkle_tree()
    print(f"✓ Merkle root: {merkle_root[:32]}...")
    print()
    
    # Step 5: Create Genesis Block
    print("⛓️  Step 5: Create Genesis Block")
    print("-" * 70)
    
    genesis_block = builder.create_genesis_block()
    print(f"✓ Genesis block created")
    print(f"  Hash: {genesis_block.hash[:32]}...")
    print(f"  Timestamp: {genesis_block.timestamp}")
    print()
    
    # Step 6: Save to Files
    print("💾 Step 6: Save to Disk")
    print("-" * 70)
    
    files = builder.save_to_files()
    for file_type, file_path in files.items():
        file_size = Path(file_path).stat().st_size
        print(f"  ✓ {file_type}: {file_path} ({file_size:,} bytes)")
    print()
    
    # Step 7: Load and Display Summary
    print("📊 Step 7: Genesis Summary")
    print("-" * 70)
    
    summary = builder.get_summary()
    print(f"  Sources: {summary['total_sources']}")
    print(f"  Books: {summary['total_books']}")
    print(f"  Chapters: {summary['total_chapters']}")
    print(f"  Sections: {summary['total_sections']}")
    print(f"  Paragraphs: {summary['total_paragraphs']}")
    print(f"  Sentences: {summary['total_sentences']}")
    print(f"  Concepts: {summary['total_concepts']:,}")
    print(f"  Avg concepts per book: {summary['concepts_per_book']:.0f}")
    print()
    
    # Step 8: Show Sample Concepts
    print("📖 Step 8: Sample Concepts from Genesis")
    print("-" * 70)
    
    concepts_file = Path(output_path) / "concepts.json"
    if concepts_file.exists():
        with open(concepts_file) as f:
            concepts = json.load(f)
        
        print(f"Showing first 5 concepts:\n")
        for i, concept in enumerate(concepts[:5], 1):
            metaloc = concept["metalocation"]
            print(f"{i}. {concept['text'][:70]}...")
            print(f"   Source: {metaloc['source_title']} ({metaloc['source_year']})")
            print(f"   Location: {metaloc['section_title']}, Para {metaloc['paragraph_number']}")
            print()
    
    # Step 9: Search Example
    print("🔎 Step 9: Search Example")
    print("-" * 70)
    
    search_terms = ["algorithm", "sorting", "quicksort"]
    for term in search_terms:
        matches = [c for c in concepts 
                  if term.lower() in c["text"].lower() or
                     any(term.lower() in k.lower() for k in c.get("keywords", []))]
        print(f"  '{term}': {len(matches)} matches")
    print()
    
    # Step 10: Plagiarism Check Example
    print("🔐 Step 10: Plagiarism Detection Example")
    print("-" * 70)
    
    test_texts = [
        "An algorithm is a well-defined computational procedure",
        "A novel approach to distributed sorting using GPU acceleration",
        "Quicksort is an efficient sorting algorithm",
    ]
    
    from difflib import SequenceMatcher
    
    for i, text in enumerate(test_texts, 1):
        # Find best match
        best_match = None
        best_ratio = 0
        
        for concept in concepts:
            ratio = SequenceMatcher(None, text.lower(), 
                                   concept["text"].lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = concept
        
        print(f"{i}. '{text[:60]}...'")
        print(f"   Best match: {best_ratio:.0%}")
        
        if best_ratio > 0.90:
            print(f"   ⚠️ PLAGIARISM: Highly similar to genesis")
            print(f"   Source: {best_match['metalocation']['source_title']}")
        elif best_ratio > 0.70:
            print(f"   📝 DERIVATION: Needs citation")
            print(f"   Source: {best_match['metalocation']['source_title']}")
        else:
            print(f"   ✅ NOVEL: Below plagiarism threshold")
        print()
    
    print("="*70)
    print("✅ Genesis Example Complete!")
    print("="*70)
    print(f"\nGenesis files saved to: {Path(output_path).absolute()}")
    print(f"\nNext steps:")
    print(f"  1. Use genesis.json for your blockchain")
    print(f"  2. Query concepts.json for plagiarism detection")
    print(f"  3. Cite from sources.json")
    print(f"  4. Integrate with write-capture-train workflow")
    print()


if __name__ == "__main__":
    main()
