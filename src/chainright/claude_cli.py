#!/usr/bin/env python3
"""
Claude CLI with Blockchain Hashing
Interactive command line interface that shows how user input and Claude responses are being hashed.
"""

import hashlib
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import sys
import os

# Import the blockchain classes
from .blockchain import Block, Blockchain


class ClaudeCLI:
    """Interactive CLI for Claude with blockchain hashing visualization."""
    
    def __init__(self, difficulty: int = 2):
        self.blockchain = Blockchain(difficulty=difficulty)
        self.conversation_history = []
        self.session_id = self.generate_session_id()
        
    def generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = str(time.time())
        return hashlib.sha256(timestamp.encode()).hexdigest()[:8]
    
    def hash_string(self, text: str) -> str:
        """Hash a string using SHA-256."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def add_to_blockchain(self, data: str, data_type: str) -> Block:
        """Add data to the blockchain and return the mined block."""
        # Create a structured data entry
        structured_data = {
            "type": data_type,
            "content": data,
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id
        }
        
        # Add to blockchain
        self.blockchain.add_data(json.dumps(structured_data))
        return self.blockchain.mine_pending_data()
    
    def simulate_claude_response(self, user_input: str) -> str:
        """Simulate Claude's response (in a real implementation, this would call Claude's API)."""
        # This is a simple simulation - in reality, you'd call Claude's API here
        responses = [
            f"I understand you said: '{user_input}'. That's an interesting point about blockchain technology.",
            f"Based on your input '{user_input}', I can see you're exploring cryptographic hashing. Let me explain how this works...",
            f"Your message '{user_input}' has been processed. The blockchain ensures the integrity of our conversation.",
            f"Thank you for your input: '{user_input}'. The hash you see below proves this conversation is immutable.",
            f"I've analyzed your statement: '{user_input}'. The blockchain will preserve this exchange forever."
        ]
        
        # Use the hash of the input to deterministically select a response
        input_hash = self.hash_string(user_input)
        response_index = int(input_hash[:2], 16) % len(responses)
        return responses[response_index]
    
    def display_hash_info(self, text: str, text_type: str, block: Block = None):
        """Display hash information for text."""
        hash_value = self.hash_string(text)
        
        print(f"\n{'='*60}")
        print(f"{text_type.upper()} HASHING INFO:")
        print(f"{'='*60}")
        print(f"Text: {text}")
        print(f"SHA-256 Hash: {hash_value}")
        print(f"Hash Length: {len(hash_value)} characters")
        
        if block:
            print(f"Block Index: {block.index}")
            print(f"Block Hash: {block.hash}")
            print(f"Nonce: {block.nonce}")
            print(f"Mining Difficulty: {self.blockchain.difficulty}")
            print(f"Timestamp: {datetime.fromtimestamp(block.timestamp)}")
        
        print(f"{'='*60}")
    
    def display_blockchain_status(self):
        """Display current blockchain status."""
        print(f"\n{'='*60}")
        print(f"BLOCKCHAIN STATUS:")
        print(f"{'='*60}")
        print(f"Session ID: {self.session_id}")
        print(f"Total Blocks: {len(self.blockchain.chain)}")
        print(f"Chain Valid: {self.blockchain.is_chain_valid()}")
        print(f"Mining Difficulty: {self.blockchain.difficulty}")
        print(f"Pending Data: {len(self.blockchain.pending_data)} items")
        print(f"{'='*60}")
    
    def display_full_chain(self):
        """Display the entire blockchain."""
        print(f"\n{'='*60}")
        print(f"FULL BLOCKCHAIN:")
        print(f"{'='*60}")
        
        for i, block in enumerate(self.blockchain.chain):
            print(f"\nBlock {i}:")
            print(f"  Index: {block.index}")
            print(f"  Data: {block.data}")
            print(f"  Previous Hash: {block.previous_hash[:20]}...")
            print(f"  Hash: {block.hash}")
            print(f"  Nonce: {block.nonce}")
            print(f"  Timestamp: {datetime.fromtimestamp(block.timestamp)}")
            print(f"  {'-'*40}")
    
    def run(self):
        """Run the interactive CLI."""
        print("Claude CLI with Blockchain Hashing")
        print("=" * 50)
        print("Type your messages to interact with Claude.")
        print("Each message and response will be hashed and added to the blockchain.")
        print("Commands:")
        print("  /status - Show blockchain status")
        print("  /chain - Display full blockchain")
        print("  /save <filename> - Save blockchain to file")
        print("  /load <filename> - Load blockchain from file")
        print("  /quit or /exit - Exit the program")
        print("=" * 50)
        
        while True:
            try:
                # Get user input
                user_input = input("\nYou: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    self.handle_command(user_input)
                    continue
                
                # Hash and display user input
                print(f"\nProcessing your input...")
                user_block = self.add_to_blockchain(user_input, "user_input")
                self.display_hash_info(user_input, "USER INPUT", user_block)
                
                # Generate Claude's response
                print(f"\nGenerating Claude's response...")
                claude_response = self.simulate_claude_response(user_input)
                
                # Hash and display Claude's response
                claude_block = self.add_to_blockchain(claude_response, "claude_response")
                self.display_hash_info(claude_response, "CLAUDE RESPONSE", claude_block)
                
                # Display Claude's response
                print(f"\nClaude: {claude_response}")
                
                # Add to conversation history
                self.conversation_history.append({
                    "user_input": user_input,
                    "claude_response": claude_response,
                    "user_hash": self.hash_string(user_input),
                    "claude_hash": self.hash_string(claude_response),
                    "timestamp": datetime.now().isoformat()
                })
                
            except KeyboardInterrupt:
                print(f"\n\nExiting...")
                break
            except Exception as e:
                print(f"\nError: {e}")
    
    def handle_command(self, command: str):
        """Handle CLI commands."""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == '/status':
            self.display_blockchain_status()
        
        elif cmd == '/chain':
            self.display_full_chain()
        
        elif cmd == '/save':
            if len(parts) < 2:
                print("Usage: /save <filename>")
                return
            filename = parts[1]
            try:
                self.blockchain.save_to_file(filename)
                print(f"Blockchain saved to {filename}")
            except Exception as e:
                print(f"Error saving blockchain: {e}")
        
        elif cmd == '/load':
            if len(parts) < 2:
                print("Usage: /load <filename>")
                return
            filename = parts[1]
            try:
                self.blockchain = Blockchain.load_from_file(filename)
                print(f"Blockchain loaded from {filename}")
            except Exception as e:
                print(f"Error loading blockchain: {e}")
        
        elif cmd in ['/quit', '/exit']:
            print("Goodbye!")
            sys.exit(0)
        
        else:
            print(f"Unknown command: {cmd}")
            print("Available commands: /status, /chain, /save, /load, /quit, /exit")


def main():
    """Main function to run the Claude CLI."""
    print("Starting Claude CLI with Blockchain Hashing...")
    
    # Set mining difficulty (lower for faster mining during demo)
    difficulty = 2
    
    cli = ClaudeCLI(difficulty=difficulty)
    cli.run()


if __name__ == "__main__":
    main()
