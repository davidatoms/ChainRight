#!/usr/bin/env python3
"""
Demo script for Claude CLI with Blockchain Hashing
This script demonstrates the hashing functionality without requiring manual input.
"""

import sys
import time
from claude_cli import ClaudeCLI


def demo_interaction():
    """Demonstrate the Claude CLI interaction with sample messages."""
    
    print("Claude CLI with Blockchain Hashing - Demo Mode")
    print("=" * 60)
    
    # Create CLI instance
    cli = ClaudeCLI(difficulty=2)
    
    # Sample conversation
    sample_messages = [
        "Hello Claude, how does blockchain hashing work?",
        "Can you explain SHA-256 to me?",
        "What makes a blockchain immutable?",
        "How does proof of work function?",
        "Thank you for the explanation!"
    ]
    
    print("Starting automated conversation demo...")
    print("Each message will be hashed and added to the blockchain.")
    print("=" * 60)
    
    for i, message in enumerate(sample_messages, 1):
        print(f"\n--- Conversation Turn {i} ---")
        
        # Process user input
        print(f"\nUser Input: {message}")
        user_block = cli.add_to_blockchain(message, "user_input")
        cli.display_hash_info(message, "USER INPUT", user_block)
        
        # Generate Claude response
        claude_response = cli.simulate_claude_response(message)
        print(f"\nClaude Response: {claude_response}")
        
        claude_block = cli.add_to_blockchain(claude_response, "claude_response")
        cli.display_hash_info(claude_response, "CLAUDE RESPONSE", claude_block)
        
        # Add to conversation history
        cli.conversation_history.append({
            "user_input": message,
            "claude_response": claude_response,
            "user_hash": cli.hash_string(message),
            "claude_hash": cli.hash_string(claude_response),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        print(f"\n{'='*60}")
        time.sleep(1)  # Brief pause for readability
    
    # Display final blockchain status
    print(f"\n--- Final Blockchain Status ---")
    cli.display_blockchain_status()
    
    # Display full chain
    print(f"\n--- Full Blockchain ---")
    cli.display_full_chain()
    
    # Save the blockchain
    filename = f"claude_conversation_{int(time.time())}.json"
    cli.blockchain.save_to_file(filename)
    print(f"\nBlockchain saved to: {filename}")
    
    print(f"\nDemo completed! You can now run 'python claude_cli.py' for interactive mode.")


if __name__ == "__main__":
    demo_interaction()
