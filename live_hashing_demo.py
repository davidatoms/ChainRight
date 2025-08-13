#!/usr/bin/env python3
"""
Live Hashing Demo - Real-time blockchain interaction with Claude
Shows live hashing of user input and Claude responses as they happen.
"""

import hashlib
import time
import json
import os
from datetime import datetime, date
from typing import Dict, Any
from ownership_blockchain import OwnershipBlockchain, OwnedSentence
from input_output_tokens import ClaudeInteractionManager


class LiveHashingDemo:
    """Live demonstration of blockchain hashing with Claude interactions."""
    
    def __init__(self, api_key: str = None):
        self.manager = ClaudeInteractionManager(api_key)
        self.blockchain = self.manager.blockchain
        self.session_id = f"session_{int(time.time())}"
        self.interaction_count = 0
        
    def show_hash_info(self, text: str, author: str, block_type: str = "sentence", model: str = None) -> str:
        """Show detailed hash information for a piece of text."""
        # Create hash
        hash_input = f"{text}{author}{time.time()}"
        hash_result = hashlib.sha256(hash_input.encode()).hexdigest()
        
        # Format display
        hash_display = f"\n{'='*80}\n"
        hash_display += f"LIVE HASHING - {block_type.upper()}\n"
        hash_display += f"{'='*80}\n"
        hash_display += f"Author: {author}\n"
        if model:
            hash_display += f"Model: {model}\n"
        hash_display += f"Timestamp: {datetime.now()}\n"
        hash_display += f"Text Length: {len(text)} characters\n"
        hash_display += f"Text Preview: {text[:100]}{'...' if len(text) > 100 else ''}\n"
        hash_display += f"Hash Input: {hash_input[:50]}...\n"
        hash_display += f"SHA-256 Hash: {hash_result}\n"
        hash_display += f"Hash (first 16): {hash_result[:16]}\n"
        hash_display += f"{'='*80}\n"
        
        return hash_display, hash_result
    
    def show_block_info(self, block) -> str:
        """Show detailed information about a mined block."""
        block_info = f"\n{'='*80}\n"
        block_info += f"BLOCK MINED - BLOCK #{block.index}\n"
        block_info += f"{'='*80}\n"
        block_info += f"Block Index: {block.index}\n"
        block_info += f"Date: {block.date_str}\n"
        block_info += f"Previous Hash: {block.previous_hash[:16]}...\n"
        block_info += f"Current Hash: {block.hash}\n"
        block_info += f"Nonce: {block.nonce}\n"
        block_info += f"Timestamp: {datetime.fromtimestamp(block.timestamp)}\n"
        block_info += f"Sentences in Block: {len(block.sentences)}\n"
        
        # Show sentences in this block
        block_info += f"\nSentences in this block:\n"
        block_info += f"{'-'*40}\n"
        for i, sentence in enumerate(block.sentences, 1):
            block_info += f"{i}. [{sentence.author}] {sentence.text[:60]}{'...' if len(sentence.text) > 60 else ''}\n"
        
        block_info += f"{'='*80}\n"
        return block_info
    
    def show_chain_status(self) -> str:
        """Show current blockchain status."""
        status = f"\n{'='*60}\n"
        status += f"BLOCKCHAIN STATUS\n"
        status += f"{'='*60}\n"
        status += f"Total Blocks: {len(self.blockchain.chain)}\n"
        status += f"Total Sentences: {sum(len(block.sentences) for block in self.blockchain.chain)}\n"
        status += f"Pending Sentences: {len(self.blockchain.pending_sentences)}\n"
        status += f"Chain Valid: {self.blockchain.is_chain_valid()}\n"
        status += f"All Authors: {', '.join(self.blockchain.get_all_authors())}\n"
        status += f"{'='*60}\n"
        return status
    
    def interactive_conversation(self):
        """Interactive conversation with live hashing display."""
        print("Live Hashing Demo - Interactive Claude Conversation")
        print("=" * 70)
        print("This demo shows real-time hashing of your input and Claude's responses.")
        print("Every sentence is cryptographically secured in the blockchain.")
        print()
        
        # Check for API key
        api_key = os.getenv('CLAUDE_API_KEY')
        if not api_key:
            print("No CLAUDE_API_KEY found. Running in mock mode.")
            print("Set CLAUDE_API_KEY for real Claude interactions.")
            print()
        
        # Get user name
        user_name = input("Enter your name: ").strip()
        if not user_name:
            user_name = "User"
        
        print(f"\nWelcome, {user_name}! Let's start the conversation.")
        print("Type 'status' to see blockchain status")
        print("Type 'quit' to end the conversation")
        print("Type 'help' for commands")
        
        while True:
            print(f"\n{'='*50}")
            user_input = input(f"{user_name}: ").strip()
            
            if not user_input:
                continue
            elif user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'status':
                print(self.show_chain_status())
                continue
            elif user_input.lower() == 'help':
                self.show_help()
                continue
            
            self.interaction_count += 1
            print(f"\n--- Interaction #{self.interaction_count} ---")
            
            # Show hash of user input
            user_hash_display, user_hash = self.show_hash_info(user_input, user_name, "USER INPUT")
            print(user_hash_display)
            
            # Add user input to blockchain
            print(f"Adding your input to pending sentences...")
            self.blockchain.add_sentence(user_input, user_name)
            
            # Interact with Claude
            print(f"Interacting with Claude...")
            result = self.manager.interact_with_claude(user_input, user_name)
            
            if result['success']:
                claude_response = result['claude_response']
                claude_model = self.manager.client.model
                
                # Show hash of Claude's response
                claude_hash_display, claude_hash = self.show_hash_info(claude_response, "claude", "CLAUDE RESPONSE", claude_model)
                print(claude_hash_display)
                
                # Show block mining process
                print(f"Mining block with both sentences...")
                block = self.blockchain.mine_pending_sentences()
                
                # Show mined block information
                block_info = self.show_block_info(block)
                print(block_info)
                
                # Show Claude's response
                print(f"Claude: {claude_response}")
                
            else:
                print(f"Error: {result['error']}")
                # Still mine the block with just user input
                print(f"Mining block with your input only...")
                block = self.blockchain.mine_pending_sentences()
                block_info = self.show_block_info(block)
                print(block_info)
        
        # Final status
        print(self.show_chain_status())
        print("Conversation ended. Blockchain saved.")
        
        # Save blockchain
        blockchain_file = self.manager.save_blockchain()
        print(f"Blockchain saved to: {blockchain_file}")
    
    def show_help(self):
        """Show help information."""
        help_text = f"""
{'='*60}
HELP - Live Hashing Demo Commands
{'='*60}

Commands:
- Just type your message to chat with Claude
- 'status' - Show current blockchain status
- 'help' - Show this help message
- 'quit' - End the conversation

What you'll see:
1. Hash of your input (SHA-256)
2. Hash of Claude's response (SHA-256)
3. Block mining process with nonce
4. Complete block information
5. Blockchain status updates

Each interaction creates:
- Your sentence (hashed and timestamped)
- Claude's response (hashed and timestamped)
- A new block containing both sentences
- Cryptographic proof of the conversation

The blockchain provides:
- Immutable record of all conversations
- Proof of who said what and when
- Cryptographic verification of data integrity
- Complete audit trail of information flow
{'='*60}
"""
        print(help_text)
    
    def demo_without_api(self):
        """Demo without API key showing mock interactions."""
        print("Live Hashing Demo - Mock Mode")
        print("=" * 50)
        print("No API key found. Running with mock Claude responses.")
        print("This shows the hashing process without real API calls.")
        print()
        
        user_name = input("Enter your name: ").strip()
        if not user_name:
            user_name = "User"
        
        print(f"\nWelcome, {user_name}! Let's see the hashing in action.")
        print("Type 'quit' to end the demo")
        
        while True:
            print(f"\n{'='*50}")
            user_input = input(f"{user_name}: ").strip()
            
            if not user_input:
                continue
            elif user_input.lower() == 'quit':
                break
            
            self.interaction_count += 1
            print(f"\n--- Mock Interaction #{self.interaction_count} ---")
            
            # Show hash of user input
            user_hash_display, user_hash = self.show_hash_info(user_input, user_name, "USER INPUT")
            print(user_hash_display)
            
            # Add user input to blockchain
            print(f"Adding your input to pending sentences...")
            self.blockchain.add_sentence(user_input, user_name)
            
            # Mock Claude response
            mock_response = f"This is a mock response to: '{user_input[:30]}{'...' if len(user_input) > 30 else ''}'"
            
            # Show hash of mock response
            claude_hash_display, claude_hash = self.show_hash_info(mock_response, "claude", "MOCK CLAUDE RESPONSE", "claude-3-5-sonnet-20241022")
            print(claude_hash_display)
            
            # Add mock response
            self.blockchain.add_sentence(mock_response, "claude")
            
            # Mine block
            print(f"Mining block with both sentences...")
            block = self.blockchain.mine_pending_sentences()
            
            # Show mined block information
            block_info = self.show_block_info(block)
            print(block_info)
            
            print(f"Mock Claude: {mock_response}")
        
        # Final status
        print(self.show_chain_status())
        print("Mock demo ended. Blockchain saved.")
        
        # Save blockchain
        blockchain_file = self.manager.save_blockchain()
        print(f"Blockchain saved to: {blockchain_file}")


def show_demo_menu():
    """Show demo menu."""
    print("Live Hashing Demo - Real-time Blockchain Interaction")
    print("=" * 60)
    print()
    print("This demo shows:")
    print("1. Real-time hashing of your input")
    print("2. Real-time hashing of Claude's responses")
    print("3. Block mining process with nonce")
    print("4. Complete blockchain status")
    print("5. Cryptographic verification of all data")
    print()
    
    api_key = os.getenv('CLAUDE_API_KEY')
    if api_key:
        print("Claude API key found - real interactions available!")
        print("1. Interactive conversation with real Claude")
        print("2. Mock conversation (no API calls)")
    else:
        print("No Claude API key found - mock mode only")
        print("1. Mock conversation (no API calls)")
        print("2. Set CLAUDE_API_KEY for real interactions")
    
    print("3. Exit")
    print()
    
    choice = input("Enter choice: ").strip()
    
    if choice == "1":
        demo = LiveHashingDemo(api_key)
        if api_key:
            demo.interactive_conversation()
        else:
            demo.demo_without_api()
    elif choice == "2":
        demo = LiveHashingDemo()
        demo.demo_without_api()
    elif choice == "3":
        print("Demo ended.")
    else:
        print("Invalid choice. Running mock demo...")
        demo = LiveHashingDemo()
        demo.demo_without_api()


if __name__ == "__main__":
    show_demo_menu()
