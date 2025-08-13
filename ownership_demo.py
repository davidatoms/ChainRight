#!/usr/bin/env python3
"""
Quick demonstration of sentence ownership features.
Shows how multiple people can mine blocks with their own sentences on the same day.
"""

from ownership_blockchain import OwnershipBlockchain, OwnedSentence
from datetime import date


def demonstrate_ownership():
    """Demonstrate the key ownership features."""
    print("Sentence Ownership Blockchain - Key Features Demo")
    print("=" * 60)
    
    # Create blockchain
    blockchain = OwnershipBlockchain(difficulty=1)
    today = date.today().isoformat()
    blockchain.create_genesis_block(today)
    
    print(f"Created blockchain for {today}")
    print("\n" + "="*60)
    
    # Scenario 1: Multiple authors contribute to the same block
    print("SCENARIO 1: Multiple Authors on Same Day")
    print("=" * 40)
    
    print("Alice, Bob, and Carol all write sentences on the same day...")
    
    # Alice's sentences
    blockchain.add_sentence("Hello, this is my first sentence in the blockchain!", "Alice")
    blockchain.add_sentence("I'm excited to be part of this project.", "Alice")
    
    # Bob's sentences  
    blockchain.add_sentence("Greetings from Bob! I'm also contributing today.", "Bob")
    blockchain.add_sentence("This ownership tracking feature is really useful.", "Bob")
    
    # Carol's sentences
    blockchain.add_sentence("Hi everyone, Carol here. Happy to join!", "Carol")
    blockchain.add_sentence("I think this will be great for collaborative writing.", "Carol")
    
    # Mine the block with ALL sentences from multiple authors
    print("\nMining block with sentences from Alice, Bob, and Carol...")
    block1 = blockchain.mine_pending_sentences(today)
    
    print(f"✓ Block 1 mined! Hash: {block1.hash[:16]}...")
    print(f"✓ Authors in this block: {block1.get_authors()}")
    print(f"✓ Total sentences in block: {len(block1.sentences)}")
    
    print("\n" + "="*60)
    
    # Scenario 2: More authors join later
    print("SCENARIO 2: More Authors Join Later")
    print("=" * 40)
    
    print("David and Eve join later on the same day...")
    
    # David's sentences
    blockchain.add_sentence("David here! Just discovered this blockchain.", "David")
    blockchain.add_sentence("The ownership feature is exactly what I needed.", "David")
    
    # Eve's sentences
    blockchain.add_sentence("Eve joining the conversation!", "Eve")
    blockchain.add_sentence("This is really innovative technology.", "Eve")
    
    # Mine another block
    print("\nMining second block with sentences from David and Eve...")
    block2 = blockchain.mine_pending_sentences(today)
    
    print(f"✓ Block 2 mined! Hash: {block2.hash[:16]}...")
    print(f"✓ Authors in this block: {block2.get_authors()}")
    print(f"✓ Total sentences in block: {len(block2.sentences)}")
    
    print("\n" + "="*60)
    
    # Show ownership information
    print("OWNERSHIP ANALYSIS")
    print("=" * 40)
    
    # All authors
    all_authors = blockchain.get_all_authors()
    print(f"All authors who contributed: {', '.join(all_authors)}")
    
    # Authors by date
    date_authors = blockchain.get_authors_by_date(today)
    print(f"Authors who contributed on {today}: {', '.join(date_authors)}")
    
    # Sentences by author
    print(f"\nSentences by Author:")
    for author in all_authors:
        if author != "system":  # Skip system genesis
            sentences = blockchain.get_sentences_by_author(author)
            print(f"  {author}: {len(sentences)} sentences")
            for i, sentence in enumerate(sentences, 1):
                print(f"    {i}. '{sentence.text}'")
    
    # All sentences by date
    print(f"\nAll sentences from {today}:")
    date_sentences = blockchain.get_sentences_by_date(today)
    for i, sentence in enumerate(date_sentences, 1):
        if sentence.author != "system":  # Skip system genesis
            print(f"  {i}. [{sentence.author}] '{sentence.text}'")
    
    print("\n" + "="*60)
    
    # Answer the key questions
    print("ANSWERING YOUR QUESTIONS")
    print("=" * 40)
    
    print("Q: Does it show who that sentence belongs to?")
    print("A: YES! Each sentence is clearly attributed to its author.")
    print("   Example: '[Alice] Hello, this is my first sentence in the blockchain!'")
    
    print("\nQ: Could multiple people have ownership of sentences on one day?")
    print("A: YES! Multiple people can contribute sentences on the same day.")
    print("   Example: Alice, Bob, and Carol all contributed on 2025-08-13")
    
    print("\nQ: What if that is what they mined when they wrote it?")
    print("A: YES! Multiple authors can mine blocks containing their sentences.")
    print("   Each block can contain sentences from multiple authors.")
    print("   Each author's contribution is cryptographically verified.")
    
    print("\n" + "="*60)
    
    # Show blockchain structure
    print("BLOCKCHAIN STRUCTURE")
    print("=" * 40)
    
    for i, block in enumerate(blockchain.chain):
        print(f"\nBlock {i}:")
        print(f"  Index: {block.index}")
        print(f"  Date: {block.date_str}")
        print(f"  Authors: {block.get_authors()}")
        print(f"  Sentences: {len(block.sentences)}")
        print(f"  Hash: {block.hash[:16]}...")
        
        if i > 0:  # Skip genesis block details
            print(f"  Sentences in this block:")
            for j, sentence in enumerate(block.sentences, 1):
                print(f"    {j}. [{sentence.author}] {sentence.text}")
    
    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETE!")
    print("=" * 60)
    
    return blockchain


if __name__ == "__main__":
    demonstrate_ownership()
