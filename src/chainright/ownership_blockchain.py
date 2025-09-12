#!/usr/bin/env python3
"""
Enhanced blockchain system with sentence ownership tracking.
Supports multiple authors mining blocks with their own sentences on the same day.
"""

import hashlib
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from collections import defaultdict


class OwnedSentence:
    """Represents a sentence with ownership information."""
    
    def __init__(self, text: str, author: str, timestamp: float = None):
        self.text = text
        self.author = author
        self.timestamp = timestamp or time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'text': self.text,
            'author': self.author,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OwnedSentence':
        """Create from dictionary."""
        return cls(
            text=data['text'],
            author=data['author'],
            timestamp=data['timestamp']
        )


class OwnershipBlock:
    """Represents a block containing owned sentences."""
    
    def __init__(self, index: int, sentences: List[OwnedSentence], date_str: str, 
                 previous_hash: str, timestamp: float = None):
        self.index = index
        self.sentences = sentences
        self.date_str = date_str
        self.previous_hash = previous_hash
        self.timestamp = timestamp or time.time()
        self.nonce = 0
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate the hash of the block."""
        block_string = json.dumps({
            'index': self.index,
            'sentences': [s.to_dict() for s in self.sentences],
            'date_str': self.date_str,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'nonce': self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty: int) -> None:
        """Mine the block with proof of work."""
        target = '0' * difficulty
        
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
    
    def get_authors(self) -> List[str]:
        """Get list of authors in this block."""
        return list(set(sentence.author for sentence in self.sentences))
    
    def get_sentences_by_author(self, author: str) -> List[OwnedSentence]:
        """Get all sentences by a specific author."""
        return [s for s in self.sentences if s.author == author]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary for serialization."""
        return {
            'index': self.index,
            'sentences': [s.to_dict() for s in self.sentences],
            'date_str': self.date_str,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'hash': self.hash
        }
    
    @classmethod
    def from_dict(cls, block_dict: Dict[str, Any]) -> 'OwnershipBlock':
        """Create a block from dictionary."""
        sentences = [OwnedSentence.from_dict(s) for s in block_dict['sentences']]
        block = cls(
            index=block_dict['index'],
            sentences=sentences,
            date_str=block_dict['date_str'],
            previous_hash=block_dict['previous_hash'],
            timestamp=block_dict['timestamp']
        )
        block.nonce = block_dict['nonce']
        block.hash = block_dict['hash']
        return block


class OwnershipBlockchain:
    """A blockchain that tracks sentence ownership."""
    
    def __init__(self, difficulty: int = 4):
        self.chain: List[OwnershipBlock] = []
        self.difficulty = difficulty
        self.pending_sentences: List[OwnedSentence] = []
    
    def create_genesis_block(self, date_str: str) -> None:
        """Create the genesis block."""
        genesis_sentences = [
            OwnedSentence("Genesis block created", "system", time.time())
        ]
        genesis_block = OwnershipBlock(0, genesis_sentences, date_str, "0")
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
    
    def add_sentence(self, text: str, author: str) -> None:
        """Add a sentence with ownership information."""
        sentence = OwnedSentence(text, author)
        self.pending_sentences.append(sentence)
        print(f"Added sentence by {author}: '{text[:50]}{'...' if len(text) > 50 else ''}'")
    
    def mine_pending_sentences(self, date_str: str = None) -> OwnershipBlock:
        """Mine all pending sentences into a new block."""
        if not self.pending_sentences:
            raise ValueError("No pending sentences to mine")
        
        if date_str is None:
            date_str = date.today().isoformat()
        
        new_block = OwnershipBlock(
            index=len(self.chain),
            sentences=self.pending_sentences.copy(),
            date_str=date_str,
            previous_hash=self.get_latest_block().hash if self.chain else "0"
        )
        
        # Mine the block
        new_block.mine_block(self.difficulty)
        
        # Add to chain
        self.chain.append(new_block)
        
        # Clear pending sentences
        self.pending_sentences = []
        
        return new_block
    
    def get_latest_block(self) -> OwnershipBlock:
        """Get the most recent block in the chain."""
        return self.chain[-1]
    
    def is_chain_valid(self) -> bool:
        """Validate the entire blockchain."""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Check if current block's hash is valid
            if current_block.hash != current_block.calculate_hash():
                return False
            
            # Check if previous hash matches
            if current_block.previous_hash != previous_block.hash:
                return False
        
        return True
    
    def get_all_authors(self) -> List[str]:
        """Get all authors who have contributed to the blockchain."""
        authors = set()
        for block in self.chain:
            authors.update(block.get_authors())
        return sorted(list(authors))
    
    def get_sentences_by_author(self, author: str) -> List[OwnedSentence]:
        """Get all sentences by a specific author."""
        sentences = []
        for block in self.chain:
            sentences.extend(block.get_sentences_by_author(author))
        return sentences
    
    def get_authors_by_date(self, date_str: str) -> List[str]:
        """Get all authors who contributed on a specific date."""
        authors = set()
        for block in self.chain:
            if block.date_str == date_str:
                authors.update(block.get_authors())
        return sorted(list(authors))
    
    def get_sentences_by_date(self, date_str: str) -> List[OwnedSentence]:
        """Get all sentences from a specific date."""
        sentences = []
        for block in self.chain:
            if block.date_str == date_str:
                sentences.extend(block.sentences)
        return sentences
    
    def get_ownership_summary(self) -> Dict[str, Any]:
        """Get a summary of ownership information."""
        summary = {
            'total_blocks': len(self.chain),
            'total_sentences': sum(len(block.sentences) for block in self.chain),
            'authors': self.get_all_authors(),
            'author_stats': {},
            'date_stats': defaultdict(list)
        }
        
        # Author statistics
        for author in summary['authors']:
            author_sentences = self.get_sentences_by_author(author)
            summary['author_stats'][author] = {
                'sentence_count': len(author_sentences),
                'first_contribution': min(s.timestamp for s in author_sentences),
                'last_contribution': max(s.timestamp for s in author_sentences)
            }
        
        # Date statistics
        for block in self.chain:
            summary['date_stats'][block.date_str].extend([
                {'text': s.text, 'author': s.author} for s in block.sentences
            ])
        
        return summary
    
    def save_to_file(self, filename: str) -> None:
        """Save the blockchain to a JSON file."""
        with open(filename, 'w') as f:
            json.dump({
                'chain': [block.to_dict() for block in self.chain],
                'pending_sentences': [s.to_dict() for s in self.pending_sentences],
                'difficulty': self.difficulty
            }, f, indent=2)
    
    @classmethod
    def load_from_file(cls, filename: str) -> 'OwnershipBlockchain':
        """Load a blockchain from a JSON file."""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        blockchain = cls(difficulty=data['difficulty'])
        blockchain.chain = [OwnershipBlock.from_dict(block_dict) for block_dict in data['chain']]
        blockchain.pending_sentences = [OwnedSentence.from_dict(s) for s in data['pending_sentences']]
        
        return blockchain


def demo_ownership_blockchain():
    """Demonstrate the ownership blockchain functionality."""
    print("Ownership Blockchain Demonstration")
    print("=" * 50)
    
    # Create blockchain
    blockchain = OwnershipBlockchain(difficulty=2)
    today = date.today().isoformat()
    blockchain.create_genesis_block(today)
    
    print(f"Created blockchain for {today}")
    
    # Multiple authors add sentences on the same day
    print(f"\nAdding sentences from multiple authors...")
    
    # Alice's sentences
    blockchain.add_sentence("Hello, this is my first sentence in the blockchain!", "Alice")
    blockchain.add_sentence("I'm excited to be part of this project.", "Alice")
    blockchain.add_sentence("Blockchain technology is fascinating.", "Alice")
    
    # Bob's sentences
    blockchain.add_sentence("Greetings from Bob! I'm also contributing today.", "Bob")
    blockchain.add_sentence("This ownership tracking feature is really useful.", "Bob")
    
    # Carol's sentences
    blockchain.add_sentence("Hi everyone, Carol here. Happy to join!", "Carol")
    blockchain.add_sentence("I think this will be great for collaborative writing.", "Carol")
    blockchain.add_sentence("Can't wait to see how this develops.", "Carol")
    
    # Mine the block with all sentences
    print(f"\nMining block with all sentences...")
    new_block = blockchain.mine_pending_sentences(today)
    
    print(f"Block mined! Hash: {new_block.hash}")
    print(f"Authors in this block: {new_block.get_authors()}")
    
    # Add more sentences from different authors
    print(f"\nAdding more sentences...")
    
    # David joins later
    blockchain.add_sentence("David here! Just discovered this blockchain.", "David")
    blockchain.add_sentence("The ownership feature is exactly what I needed.", "David")
    
    # Alice adds more
    blockchain.add_sentence("Great to see more people joining!", "Alice")
    
    # Mine another block
    new_block2 = blockchain.mine_pending_sentences(today)
    
    print(f"Second block mined! Hash: {new_block2.hash}")
    print(f"Authors in second block: {new_block2.get_authors()}")
    
    # Display ownership information
    print(f"\n{'='*60}")
    print("OWNERSHIP SUMMARY")
    print(f"{'='*60}")
    
    summary = blockchain.get_ownership_summary()
    
    print(f"Total blocks: {summary['total_blocks']}")
    print(f"Total sentences: {summary['total_sentences']}")
    print(f"All authors: {', '.join(summary['authors'])}")
    
    print(f"\nAuthor Statistics:")
    for author, stats in summary['author_stats'].items():
        print(f"  {author}: {stats['sentence_count']} sentences")
    
    print(f"\nSentences by Author:")
    for author in summary['authors']:
        sentences = blockchain.get_sentences_by_author(author)
        print(f"\n  {author} ({len(sentences)} sentences):")
        for i, sentence in enumerate(sentences, 1):
            print(f"    {i}. '{sentence.text}'")
    
    print(f"\nSentences by Date ({today}):")
    date_sentences = blockchain.get_sentences_by_date(today)
    for i, sentence in enumerate(date_sentences, 1):
        print(f"  {i}. [{sentence.author}] '{sentence.text}'")
    
    # Save blockchain
    filename = f"ownership_blockchain_{today}.json"
    blockchain.save_to_file(filename)
    print(f"\nBlockchain saved to {filename}")
    
    return blockchain


def interactive_ownership_demo():
    """Interactive demonstration of ownership features."""
    print("Interactive Ownership Blockchain Demo")
    print("=" * 50)
    
    blockchain = OwnershipBlockchain(difficulty=1)
    today = date.today().isoformat()
    blockchain.create_genesis_block(today)
    
    print(f"Created blockchain for {today}")
    print("You can add sentences as different authors.")
    print("Type 'mine' to mine a block, 'quit' to exit.")
    
    while True:
        print(f"\nPending sentences: {len(blockchain.pending_sentences)}")
        if blockchain.pending_sentences:
            print("Recent sentences:")
            for s in blockchain.pending_sentences[-3:]:
                print(f"  [{s.author}] {s.text[:50]}{'...' if len(s.text) > 50 else ''}")
        
        command = input("\nEnter command (add/mine/status/authors/quit): ").strip().lower()
        
        if command == 'quit':
            break
        elif command == 'add':
            author = input("Enter author name: ").strip()
            text = input("Enter sentence: ").strip()
            if author and text:
                blockchain.add_sentence(text, author)
        elif command == 'mine':
            if blockchain.pending_sentences:
                new_block = blockchain.mine_pending_sentences(today)
                print(f"Block mined! Authors: {new_block.get_authors()}")
            else:
                print("No pending sentences to mine.")
        elif command == 'status':
            print(f"Chain length: {len(blockchain.chain)}")
            print(f"Total sentences: {sum(len(b.sentences) for b in blockchain.chain)}")
            print(f"All authors: {', '.join(blockchain.get_all_authors())}")
        elif command == 'authors':
            authors = blockchain.get_all_authors()
            if authors:
                print("Authors and their sentence counts:")
                for author in authors:
                    sentences = blockchain.get_sentences_by_author(author)
                    print(f"  {author}: {len(sentences)} sentences")
            else:
                print("No authors yet.")
        else:
            print("Unknown command. Use: add, mine, status, authors, or quit")


if __name__ == "__main__":
    print("Ownership Blockchain System")
    print("=" * 40)
    
    print("Choose mode:")
    print("1. Demo with multiple authors")
    print("2. Interactive demo")
    
    choice = input("Enter choice (1-2): ").strip()
    
    if choice == "1":
        demo_ownership_blockchain()
    elif choice == "2":
        interactive_ownership_demo()
    else:
        print("Invalid choice, running demo...")
        demo_ownership_blockchain()
