import hashlib
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import os


class WordListBlock:
    """Represents a block containing a word list with date information."""
    
    def __init__(self, index: int, word_list: List[str], date_str: str, previous_hash: str, timestamp: float = None):
        self.index = index
        self.word_list = word_list
        self.date_str = date_str
        self.previous_hash = previous_hash
        self.timestamp = timestamp or time.time()
        self.nonce = 0
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate the hash of the block."""
        block_string = json.dumps({
            'index': self.index,
            'word_list': self.word_list,
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary for serialization."""
        return {
            'index': self.index,
            'word_list': self.word_list,
            'date_str': self.date_str,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'hash': self.hash
        }
    
    @classmethod
    def from_dict(cls, block_dict: Dict[str, Any]) -> 'WordListBlock':
        """Create a block from dictionary."""
        block = cls(
            index=block_dict['index'],
            word_list=block_dict['word_list'],
            date_str=block_dict['date_str'],
            previous_hash=block_dict['previous_hash'],
            timestamp=block_dict['timestamp']
        )
        block.nonce = block_dict['nonce']
        block.hash = block_dict['hash']
        return block


class WordListBlockchain:
    """A blockchain that uses word lists as genesis blocks."""
    
    def __init__(self, difficulty: int = 4):
        self.chain: List[WordListBlock] = []
        self.difficulty = difficulty
        self.pending_data: List[str] = []
    
    def create_word_list_genesis_block(self, word_list: List[str], date_str: str) -> None:
        """Create the genesis block with a word list."""
        genesis_block = WordListBlock(0, word_list, date_str, "0")
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
    
    def get_latest_block(self) -> WordListBlock:
        """Get the most recent block in the chain."""
        return self.chain[-1]
    
    def add_data(self, data: str) -> None:
        """Add data to the pending transactions."""
        self.pending_data.append(data)
    
    def mine_pending_data(self) -> WordListBlock:
        """Mine all pending data into a new block."""
        if not self.pending_data:
            raise ValueError("No pending data to mine")
        
        # Create a new block with all pending data
        block_data = json.dumps(self.pending_data)
        new_block = WordListBlock(
            index=len(self.chain),
            word_list=[],  # Empty for non-genesis blocks
            date_str="",   # Empty for non-genesis blocks
            previous_hash=self.get_latest_block().hash
        )
        new_block.word_list = self.pending_data  # Store data in word_list field for consistency
        
        # Mine the block
        new_block.mine_block(self.difficulty)
        
        # Add to chain
        self.chain.append(new_block)
        
        # Clear pending data
        self.pending_data = []
        
        return new_block
    
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
    
    def get_chain(self) -> List[Dict[str, Any]]:
        """Get the entire chain as a list of dictionaries."""
        return [block.to_dict() for block in self.chain]
    
    def save_to_file(self, filename: str) -> None:
        """Save the blockchain to a JSON file."""
        with open(filename, 'w') as f:
            json.dump({
                'chain': self.get_chain(),
                'pending_data': self.pending_data,
                'difficulty': self.difficulty
            }, f, indent=2)
    
    @classmethod
    def load_from_file(cls, filename: str) -> 'WordListBlockchain':
        """Load a blockchain from a JSON file."""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        blockchain = cls(difficulty=data['difficulty'])
        blockchain.chain = [WordListBlock.from_dict(block_dict) for block_dict in data['chain']]
        blockchain.pending_data = data['pending_data']
        
        return blockchain


def get_english_words() -> List[str]:
    """Get a list of English words from a reliable source."""
    # Try to get words from a common word list
    word_sources = [
        "/usr/share/dict/words",  # Unix/Linux
        "/usr/dict/words",        # Some Unix systems
        "words.txt"               # Local file
    ]
    
    for source in word_sources:
        if os.path.exists(source):
            try:
                with open(source, 'r') as f:
                    words = [word.strip().lower() for word in f.readlines() if word.strip().isalpha()]
                return words[:10000]  # Limit to first 10,000 words for performance
            except Exception:
                continue
    
    # Fallback: Use a basic English word list
    fallback_words = [
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
        "this", "but", "his", "by", "from", "they", "we", "say", "her", "she", "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
        "so", "up", "out", "if", "about", "who", "get", "which", "go", "me", "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
        "people", "into", "year", "your", "good", "some", "could", "them", "see", "other", "than", "then", "now", "look", "only", "come", "its", "over",
        "think", "also", "back", "after", "use", "two", "how", "our", "work", "first", "well", "way", "even", "new", "want", "because", "any", "these",
        "give", "day", "most", "us", "water", "been", "call", "oil", "sit", "now", "find", "down", "day", "did", "get", "come", "made", "may", "part"
    ]
    
    return fallback_words


def create_word_list_blockchain(date_str: str = None, difficulty: int = 4) -> WordListBlockchain:
    """Create a blockchain with English words as the genesis block."""
    if date_str is None:
        date_str = date.today().isoformat()
    
    # Get English words
    words = get_english_words()
    
    # Create blockchain
    blockchain = WordListBlockchain(difficulty=difficulty)
    blockchain.create_word_list_genesis_block(words, date_str)
    
    return blockchain


def demo_word_list_blockchain():
    """Demonstrate the word list blockchain functionality."""
    print("Creating a blockchain with English words as genesis block...")
    
    # Create blockchain with today's date
    today = date.today().isoformat()
    blockchain = create_word_list_blockchain(today, difficulty=2)
    
    print(f"Blockchain created with date: {today}")
    print(f"Genesis block contains {len(blockchain.chain[0].word_list)} English words")
    print(f"Chain length: {len(blockchain.chain)}")
    print(f"Chain valid: {blockchain.is_chain_valid()}")
    
    # Display genesis block info
    genesis = blockchain.chain[0]
    print(f"\nGenesis Block Details:")
    print(f"  Index: {genesis.index}")
    print(f"  Date: {genesis.date_str}")
    print(f"  Word Count: {len(genesis.word_list)}")
    print(f"  First 10 words: {genesis.word_list[:10]}")
    print(f"  Hash: {genesis.hash}")
    print(f"  Nonce: {genesis.nonce}")
    print(f"  Timestamp: {datetime.fromtimestamp(genesis.timestamp)}")
    
    # Add some additional data
    blockchain.add_data("Additional data after word list")
    blockchain.add_data("More blockchain data")
    blockchain.mine_pending_data()
    
    print(f"\nAfter adding data, chain length: {len(blockchain.chain)}")
    
    # Save to file
    filename = f"wordlist_blockchain_{today}.json"
    blockchain.save_to_file(filename)
    print(f"Blockchain saved to {filename}")
    
    return blockchain


if __name__ == "__main__":
    demo_word_list_blockchain()
