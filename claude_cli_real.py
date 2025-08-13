#!/usr/bin/env python3
"""
Claude CLI with Blockchain Hashing - Real API Version
Interactive command line interface that shows how user input and Claude responses are being hashed.
Uses real Claude API calls via curl.
"""

import hashlib
import json
import time
import subprocess
import sys
import os
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

# Import the blockchain classes
from blockchain import Block, Blockchain


class ClaudeCLIReal:
    """Interactive CLI for Claude with blockchain hashing visualization using real API."""
    
    def __init__(self, difficulty: int = 2, api_key: str = None, model: str = "claude-3-5-sonnet-20241022"):
        # Load environment variables from .env file
        load_dotenv()
        
        self.blockchain = Blockchain(difficulty=difficulty)
        self.conversation_history = []
        self.session_id = self.generate_session_id()
        self.api_key = api_key or os.getenv('CLAUDE_API_KEY')
        self.model = model
        self.conversation_context = []
        
        if not self.api_key:
            print("Warning: No Claude API key found!")
            print("Please set CLAUDE_API_KEY in .env file, environment variable, or provide it as parameter")
            print("You can get your API key from: https://console.anthropic.com/")
        
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
    
    def call_claude_api(self, user_input: str) -> str:
        """Call the real Claude API using curl."""
        if not self.api_key:
            return "Error: No API key configured. Please set CLAUDE_API_KEY environment variable."
        
        # Prepare the conversation context
        messages = []
        
        # Add conversation history for context
        for entry in self.conversation_context[-10:]:  # Last 10 exchanges for context
            messages.append({"role": "user", "content": entry["user"]})
            messages.append({"role": "assistant", "content": entry["claude"]})
        
        # Add current user input
        messages.append({"role": "user", "content": user_input})
        
        # Prepare the API request
        api_request = {
            "model": self.model,
            "max_tokens": 1000,
            "messages": messages,
            "system": "You are Claude, an AI assistant. Respond naturally and helpfully to the user's questions. Keep responses concise but informative."
        }
        
        try:
            # Make the API call using curl
            curl_command = [
                "curl", "-s", "-X", "POST", "https://api.anthropic.com/v1/messages",
                "-H", f"x-api-key: {self.api_key}",
                "-H", "content-type: application/json",
                "-H", "anthropic-version: 2023-06-01",
                "-d", json.dumps(api_request)
            ]
            
            result = subprocess.run(curl_command, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return f"Error calling Claude API: {result.stderr}"
            
            # Parse the response
            response_data = json.loads(result.stdout)
            
            if "content" in response_data and len(response_data["content"]) > 0:
                claude_response = response_data["content"][0]["text"]
                
                # Add to conversation context
                self.conversation_context.append({
                    "user": user_input,
                    "claude": claude_response,
                    "timestamp": datetime.now().isoformat()
                })
                
                return claude_response
            else:
                return f"Error: Unexpected API response format: {response_data}"
                
        except subprocess.TimeoutExpired:
            return "Error: API call timed out"
        except json.JSONDecodeError:
            return f"Error: Invalid JSON response from API: {result.stdout}"
        except Exception as e:
            return f"Error calling Claude API: {str(e)}"
    
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
        print(f"API Key Configured: {'Yes' if self.api_key else 'No'}")
        print(f"Model: {self.model}")
        print(f"{'='*60}")
    
    def display_full_chain(self):
        """Display the entire blockchain."""
        print(f"\n{'='*60}")
        print(f"FULL BLOCKCHAIN:")
        print(f"{'='*60}")
        
        for i, block in enumerate(self.blockchain.chain):
            print(f"\nBlock {i}:")
            print(f"  Index: {block.index}")
            
            # Parse and display the data more clearly
            try:
                data_list = json.loads(block.data)
                for data_item in data_list:
                    data_obj = json.loads(data_item)
                    print(f"  Type: {data_obj.get('type', 'unknown')}")
                    print(f"  Content: {data_obj.get('content', '')[:100]}{'...' if len(data_obj.get('content', '')) > 100 else ''}")
                    print(f"  Timestamp: {data_obj.get('timestamp', '')}")
            except:
                print(f"  Data: {block.data}")
            
            print(f"  Previous Hash: {block.previous_hash[:20]}...")
            print(f"  Hash: {block.hash}")
            print(f"  Nonce: {block.nonce}")
            print(f"  Timestamp: {datetime.fromtimestamp(block.timestamp)}")
            print(f"  {'-'*40}")
    
    def run(self):
        """Run the interactive CLI."""
        print("Claude CLI with Blockchain Hashing - Real API Version")
        print("=" * 60)
        print("Type your messages to interact with Claude.")
        print("Each message and response will be hashed and added to the blockchain.")
        print("Commands:")
        print("  /status - Show blockchain status")
        print("  /chain - Display full blockchain")
        print("  /save <filename> - Save blockchain to file")
        print("  /load <filename> - Load blockchain from file")
        print("  /clear - Clear conversation context")
        print("  /quit or /exit - Exit the program")
        print("=" * 60)
        
        if not self.api_key:
            print("\nWARNING: No API key configured!")
            print("Please set CLAUDE_API_KEY environment variable or restart with API key parameter")
            print("Example: export CLAUDE_API_KEY='your-api-key-here'")
        
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
                
                # Call Claude API
                print(f"\nCalling Claude API...")
                claude_response = self.call_claude_api(user_input)
                
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
        
        elif cmd == '/clear':
            self.conversation_context = []
            print("Conversation context cleared")
        
        elif cmd in ['/quit', '/exit']:
            print("Goodbye!")
            sys.exit(0)
        
        else:
            print(f"Unknown command: {cmd}")
            print("Available commands: /status, /chain, /save, /load, /clear, /quit, /exit")


def main():
    """Main function to run the Claude CLI."""
    print("Starting Claude CLI with Real API Integration...")
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Check for API key
    api_key = os.getenv('CLAUDE_API_KEY')
    if not api_key:
        print("No CLAUDE_API_KEY found in .env file or environment variables.")
        api_key = input("Enter your Claude API key (or press Enter to skip): ").strip()
        if api_key:
            os.environ['CLAUDE_API_KEY'] = api_key
    
    # Set mining difficulty (lower for faster mining during demo)
    difficulty = 2
    
    cli = ClaudeCLIReal(difficulty=difficulty, api_key=api_key)
    cli.run()


if __name__ == "__main__":
    main()
