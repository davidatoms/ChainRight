import hashlib
import json
import time
from typing import List, Dict, Any
from datetime import datetime
from .geometrics import LLMGeometrics
from .device_awareness import DeviceAwareness

# Load static settings and apply dynamic overrides
try:
    with open('config/settings.json', 'r') as f:
        SETTINGS = json.load(f)
except:
    SETTINGS = {
        "base_difficulty": 2,
        "max_difficulty_clamp": 6,
        "surgery_threshold": 7,
        "ledger_prefix": "ledgers/chain_"
    }

# Apply Device Awareness Overrides
device_config = DeviceAwareness.get_edge_case_config()
SETTINGS.update(device_config)


class Block:
    """Represents a single block in the blockchain."""
    
    def __init__(self, index: int, data: str, previous_hash: str, timestamp: float = None, 
                 difficulty: int = 4, parent_chain: str = None, node_type: str = "COMPUTE_NODE"):
        self.index = index
        self.data = data
        self.previous_hash = previous_hash
        self.timestamp = timestamp or time.time()
        self.nonce = 0
        self.difficulty = difficulty
        self.parent_chain = parent_chain 
        self.node_type = node_type # Record the device signature
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate the hash of the block."""
        block_string = json.dumps({
            'index': self.index,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'difficulty': self.difficulty,
            'parent_chain': self.parent_chain,
            'node_type': self.node_type
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty: int = None) -> None:
        """Mine the block with proof of work."""
        if difficulty is not None:
            self.difficulty = difficulty
            
        target = '0' * self.difficulty
        
        while self.hash[:self.difficulty] != target:
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
            'hash': self.hash,
            'difficulty': self.difficulty,
            'parent_chain': self.parent_chain,
            'node_type': self.node_type
        }
    
    @classmethod
    def from_dict(cls, block_dict: Dict[str, Any]) -> 'Block':
        """Create a block from dictionary."""
        block = cls(
            index=block_dict['index'],
            data=block_dict['data'],
            previous_hash=block_dict['previous_hash'],
            timestamp=block_dict['timestamp'],
            difficulty=block_dict.get('difficulty', 4),
            parent_chain=block_dict.get('parent_chain'),
            node_type=block_dict.get('node_type', 'COMPUTE_NODE')
        )
        block.nonce = block_dict['nonce']
        block.hash = block_dict['hash']
        return block


class Blockchain:
    """A simple blockchain implementation with Ricci Flow Surgery and Device Awareness."""
    
    def __init__(self, difficulty: int = None, parent_chain: str = None):
        self.chain: List[Block] = []
        self.base_difficulty = difficulty if difficulty is not None else SETTINGS["base_difficulty"]
        self.parent_chain = parent_chain
        self.node_type = SETTINGS["device_signature"]
        self.pending_data: List[str] = []
        
        # Create the genesis block
        self.create_genesis_block()
    
    def create_genesis_block(self) -> None:
        """Create the first block in the chain."""
        genesis_data = f"Genesis Block (Node: {self.node_type})"
        if self.parent_chain:
            genesis_data = f"Genesis Block (Surgery Link to {self.parent_chain})"
            
        genesis_block = Block(0, genesis_data, "0", 
                              difficulty=self.base_difficulty,
                              parent_chain=self.parent_chain,
                              node_type=self.node_type)
        genesis_block.mine_block()
        self.chain.append(genesis_block)
    
    def get_latest_block(self) -> Block:
        """Get the most recent block in the chain."""
        return self.chain[-1]
    
    def add_data(self, data: str) -> None:
        """Add data to the pending transactions."""
        self.pending_data.append(data)
    
    def mine_pending_data(self, latency_ms: float = 0) -> Dict[str, Any]:
        """Mine all pending data into a new block using relativistic difficulty."""
        if not self.pending_data:
            raise ValueError("No pending data to mine")
        
        # Create a new block with all pending data
        block_data = json.dumps(self.pending_data)
        
        # Calculate relativistic metrics
        raw_difficulty = LLMGeometrics.score_difficulty(
            block_data, 
            base_difficulty=self.base_difficulty,
            latency_ms=latency_ms
        )
        
        surgery_info = {"performed": False, "archive_name": None}
        
        # Check for Ricci Flow Surgery
        if raw_difficulty >= SETTINGS["surgery_threshold"]:
            parent_hash = self.get_latest_block().hash
            short_hash = parent_hash[:12]
            archive_name = f"manifold_{short_hash}_archived.json"
            
            print(f"\n\033[91m[RICCI FLOW SURGERY PERFORMED]\033[0m")
            print(f"\033[93mMaximum Temperature Reached. Curvature too extreme for current manifold.\033[0m")
            print(f"\033[92mArchiving current manifold to: {archive_name}\033[0m")
            print(f"\033[96mSymbolic Link Established to Hash: {short_hash}...\033[0m")
            
            # Save current chain before surgery
            self.save_to_file(archive_name)
            
            # Reset the chain but keep the reference
            self.parent_chain = archive_name
            self.chain = []
            self.create_genesis_block()
            
            # Clamp the difficulty for the new genesis transition
            raw_difficulty = SETTINGS["max_difficulty_clamp"]
            surgery_info = {
                "performed": True, 
                "archive_name": archive_name,
                "parent_hash": parent_hash,
                "new_active_name": f"manifold_{short_hash}_active.json"
            }
            
        # Clamp difficulty for standard mining based on DEVICE capability
        clamped_difficulty = min(raw_difficulty, SETTINGS["max_difficulty_clamp"])
        
        new_block = Block(
            index=len(self.chain),
            data=block_data,
            previous_hash=self.get_latest_block().hash,
            difficulty=clamped_difficulty,
            parent_chain=self.parent_chain,
            node_type=self.node_type
        )
        
        # Mine the block
        new_block.mine_block()
        
        # Add to chain
        self.chain.append(new_block)
        
        # Clear pending data
        self.pending_data = []
        
        return {
            "block": new_block,
            "surgery": surgery_info
        }
    
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
