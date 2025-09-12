#!/usr/bin/env python3
"""
Example script demonstrating how to create a blockchain with input strings.
"""

from src.chainright.blockchain import Blockchain, create_string_blockchain
from datetime import datetime


def interactive_blockchain():
    """Interactive blockchain creation with user input."""
    print("String Blockchain Creator")
    print("=" * 50)
    
    # Get user input
    user_string = input("Enter a string to store in the blockchain: ")
    
    # Get difficulty level
    try:
        difficulty = int(input("Enter mining difficulty (1-6, higher = slower): "))
        difficulty = max(1, min(6, difficulty))  # Clamp between 1 and 6
    except ValueError:
        difficulty = 2
        print("Using default difficulty: 2")
    
    print(f"\nCreating blockchain with difficulty {difficulty}...")
    
    # Create blockchain
    blockchain = create_string_blockchain(user_string, difficulty)
    
    print(f"Blockchain created successfully!")
    print(f"Chain length: {len(blockchain.chain)}")
    print(f"Chain valid: {blockchain.is_chain_valid()}")
    
    # Display the created block
    block = blockchain.get_latest_block()
    print(f"\nBlock details:")
    print(f"  Index: {block.index}")
    print(f"  Data: {block.data}")
    print(f"  Hash: {block.hash}")
    print(f"  Previous Hash: {block.previous_hash}")
    print(f"  Nonce: {block.nonce}")
    print(f"  Timestamp: {datetime.fromtimestamp(block.timestamp)}")
    
    # Ask if user wants to add more data
    while True:
        add_more = input("\nAdd more data to the blockchain? (y/n): ").lower()
        if add_more in ['y', 'yes']:
            new_data = input("Enter new data: ")
            blockchain.add_data(new_data)
            blockchain.mine_pending_data()
            print(f"Added new block! Chain length: {len(blockchain.chain)}")
        elif add_more in ['n', 'no']:
            break
        else:
            print("Please enter 'y' or 'n'")
    
    # Save blockchain
    save_choice = input("\nSave blockchain to file? (y/n): ").lower()
    if save_choice in ['y', 'yes']:
        filename = input("Enter filename (default: blockchain.json): ").strip()
        if not filename:
            filename = "blockchain.json"
        blockchain.save_to_file(filename)
        print(f"Blockchain saved to {filename}")
    
    return blockchain


def simple_example():
    """Simple example with predefined strings."""
    print("Simple Blockchain Example")
    print("=" * 30)
    
    # Create blockchain with multiple strings
    blockchain = Blockchain(difficulty=2)
    
    strings = [
        "First string in the blockchain",
        "Second string with more data",
        "Third string for demonstration",
        "Fourth string to show chain growth"
    ]
    
    for i, string in enumerate(strings, 1):
        print(f"\nAdding string {i}: '{string}'")
        blockchain.add_data(string)
        blockchain.mine_pending_data()
        print(f"Block {i} mined! Hash: {blockchain.get_latest_block().hash[:16]}...")
    
    print(f"\nFinal blockchain:")
    print(f"Chain length: {len(blockchain.chain)}")
    print(f"Chain valid: {blockchain.is_chain_valid()}")
    
    # Display all blocks
    for i, block in enumerate(blockchain.chain):
        print(f"\nBlock {i}:")
        print(f"  Data: {block.data}")
        print(f"  Hash: {block.hash}")
        print(f"  Previous: {block.previous_hash[:16]}...")
    
    return blockchain


if __name__ == "__main__":
    print("Choose an example:")
    print("1. Interactive blockchain creation")
    print("2. Simple predefined example")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        interactive_blockchain()
    elif choice == "2":
        simple_example()
    else:
        print("Invalid choice, running simple example...")
        simple_example()
