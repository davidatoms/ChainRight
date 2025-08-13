#!/usr/bin/env python3
"""
Simple test script to demonstrate blockchain functionality.
"""

from blockchain import Blockchain, create_string_blockchain


def test_basic_functionality():
    """Test basic blockchain functionality."""
    print("Testing Basic Blockchain Functionality")
    print("=" * 40)
    
    # Test 1: Create blockchain with input string
    input_string = "My important data that needs to be stored securely"
    print(f"Input string: '{input_string}'")
    
    blockchain = create_string_blockchain(input_string, difficulty=2)
    print(f"Blockchain created with {len(blockchain.chain)} blocks")
    print(f"Chain valid: {blockchain.is_chain_valid()}")
    
    # Test 2: Add more data
    print("\nAdding more data...")
    blockchain.add_data("Additional data point 1")
    blockchain.add_data("Additional data point 2")
    blockchain.mine_pending_data()
    
    print(f"Chain length after adding data: {len(blockchain.chain)}")
    print(f"Chain still valid: {blockchain.is_chain_valid()}")
    
    # Test 3: Display chain structure
    print("\nBlockchain Structure:")
    for i, block in enumerate(blockchain.chain):
        print(f"\nBlock {i}:")
        print(f"  Index: {block.index}")
        print(f"  Data: {block.data}")
        print(f"  Hash: {block.hash}")
        print(f"  Previous Hash: {block.previous_hash}")
        print(f"  Nonce: {block.nonce}")
    
    return blockchain


def test_validation():
    """Test blockchain validation."""
    print("\n\nTesting Blockchain Validation")
    print("=" * 35)
    
    # Create a valid blockchain
    blockchain = Blockchain(difficulty=1)
    blockchain.add_data("Test data 1")
    blockchain.mine_pending_data()
    blockchain.add_data("Test data 2")
    blockchain.mine_pending_data()
    
    print(f"Original chain valid: {blockchain.is_chain_valid()}")
    
    # Try to tamper with the data (this should make it invalid)
    if len(blockchain.chain) > 1:
        # Modify the data in the second block
        blockchain.chain[1].data = "Tampered data"
        print(f"After tampering, chain valid: {blockchain.is_chain_valid()}")
    
    return blockchain


def test_persistence():
    """Test saving and loading blockchain."""
    print("\n\nTesting Persistence")
    print("=" * 20)
    
    # Create blockchain
    blockchain = Blockchain(difficulty=2)
    blockchain.add_data("Persistent data 1")
    blockchain.add_data("Persistent data 2")
    blockchain.mine_pending_data()
    
    # Save to file
    filename = "test_blockchain.json"
    blockchain.save_to_file(filename)
    print(f"Blockchain saved to {filename}")
    
    # Load from file
    loaded_blockchain = Blockchain.load_from_file(filename)
    print(f"Blockchain loaded from {filename}")
    print(f"Loaded chain valid: {loaded_blockchain.is_chain_valid()}")
    print(f"Loaded chain length: {len(loaded_blockchain.chain)}")
    
    return loaded_blockchain


if __name__ == "__main__":
    print("Blockchain Test Suite")
    print("=" * 50)
    
    # Run all tests
    test_basic_functionality()
    test_validation()
    test_persistence()
    
    print("\n\nAll tests completed!")
