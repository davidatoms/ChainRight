import hashlib
import json
import time
from typing import List, Dict, Any
from datetime import datetime


class Block:
    """Represents a single block in the blockchain."""
    
    def __init__(self, index: int, data: str, previous_hash: str, timestamp: float = None):
        self.index = index
        self.data = data
        self.previous_hash = previous_hash
        self.timestamp = timestamp or time.time()
        self.nonce = 0
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate the hash of the block."""
        block_string = json.dumps({
            'index': self.index,
            'data': self.data,
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
            'data': self.data,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'hash': self.hash
        }
    
    @classmethod
    def from_dict(cls, block_dict: Dict[str, Any]) -> 'Block':
        """Create a block from dictionary."""
        block = cls(
            index=block_dict['index'],
            data=block_dict['data'],
            previous_hash=block_dict['previous_hash'],
            timestamp=block_dict['timestamp']
        )
        block.nonce = block_dict['nonce']
        block.hash = block_dict['hash']
        return block


class Blockchain:
    """A simple blockchain implementation."""
    
    def __init__(self, difficulty: int = 4):
        self.chain: List[Block] = []
        self.difficulty = difficulty
        self.pending_data: List[str] = []
        
        # Create the genesis block
        self.create_genesis_block()
    
    def create_genesis_block(self) -> None:
        """Create the first block in the chain."""
        genesis_block = Block(0, "Genesis Block", "0")
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
    
    def get_latest_block(self) -> Block:
        """Get the most recent block in the chain."""
        return self.chain[-1]
    
    def add_data(self, data: str) -> None:
        """Add data to the pending transactions."""
        self.pending_data.append(data)
    
    def mine_pending_data(self) -> Block:
        """Mine all pending data into a new block."""
        if not self.pending_data:
            raise ValueError("No pending data to mine")
        
        # Create a new block with all pending data
        block_data = json.dumps(self.pending_data)
        new_block = Block(
            index=len(self.chain),
            data=block_data,
            previous_hash=self.get_latest_block().hash
        )
        
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
    
    def get_block_by_index(self, index: int) -> Block:
        """Get a specific block by its index."""
        if 0 <= index < len(self.chain):
            return self.chain[index]
        raise IndexError(f"Block index {index} out of range")
    
    def get_block_by_hash(self, hash_value: str) -> Block:
        """Get a specific block by its hash."""
        for block in self.chain:
            if block.hash == hash_value:
                return block
        raise ValueError(f"Block with hash {hash_value} not found")
    
    def replace_chain(self, new_chain: List[Dict[str, Any]]) -> bool:
        """Replace the current chain with a new one if it's valid and longer."""
        new_blockchain = []
        
        for block_dict in new_chain:
            new_blockchain.append(Block.from_dict(block_dict))
        
        if len(new_blockchain) > len(self.chain) and self.is_chain_valid():
            self.chain = new_blockchain
            return True
        return False
    
    def save_to_file(self, filename: str) -> None:
        """Save the blockchain to a JSON file."""
        with open(filename, 'w') as f:
            json.dump({
                'chain': self.get_chain(),
                'pending_data': self.pending_data,
                'difficulty': self.difficulty
            }, f, indent=2)
    
    @classmethod
    def load_from_file(cls, filename: str) -> 'Blockchain':
        """Load a blockchain from a JSON file."""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        blockchain = cls(difficulty=data['difficulty'])
        blockchain.chain = [Block.from_dict(block_dict) for block_dict in data['chain']]
        blockchain.pending_data = data['pending_data']
        
        return blockchain


def create_string_blockchain(input_string: str, difficulty: int = 4) -> Blockchain:
    """Create a blockchain with the given input string."""
    blockchain = Blockchain(difficulty=difficulty)
    blockchain.add_data(input_string)
    blockchain.mine_pending_data()
    return blockchain


def demo_blockchain():
    """Demonstrate the blockchain functionality."""
    print("Creating a blockchain with input string...")
    
    # Create blockchain with a sample string
    input_string = "Hello, this is my first blockchain data!"
    blockchain = create_string_blockchain(input_string, difficulty=2)
    
    print(f"Blockchain created with input: '{input_string}'")
    print(f"Chain length: {len(blockchain.chain)}")
    print(f"Chain valid: {blockchain.is_chain_valid()}")
    
    # Add more data
    blockchain.add_data("Second piece of data")
    blockchain.add_data("Third piece of data")
    blockchain.mine_pending_data()
    
    print(f"After adding more data, chain length: {len(blockchain.chain)}")
    
    # Display the chain
    print("\nBlockchain contents:")
    for i, block in enumerate(blockchain.chain):
        print(f"\nBlock {i}:")
        print(f"  Index: {block.index}")
        print(f"  Data: {block.data}")
        print(f"  Previous Hash: {block.previous_hash}")
        print(f"  Hash: {block.hash}")
        print(f"  Nonce: {block.nonce}")
        print(f"  Timestamp: {datetime.fromtimestamp(block.timestamp)}")
    
    return blockchain


if __name__ == "__main__":
    demo_blockchain()
