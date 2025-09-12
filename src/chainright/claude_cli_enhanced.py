#!/usr/bin/env python3
"""
Claude CLI with Blockchain Hashing - Enhanced Version
Interactive command line interface with colors and easy model selection.
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
from colorama import init, Fore, Back, Style

# Import the blockchain classes
from .blockchain import Block, Blockchain

# Initialize colorama for cross-platform color support
init(autoreset=True)


class ClaudeCLIEnhanced:
    """Enhanced CLI for Claude with blockchain hashing, colors, and model selection."""
    
    # Available Claude models
    AVAILABLE_MODELS = {
        "1": {
            "name": "claude-3-5-sonnet-20241022",
            "description": "Most capable, balanced performance",
            "color": Fore.CYAN
        },
        "2": {
            "name": "claude-3-5-haiku-20241022", 
            "description": "Fastest, most affordable",
            "color": Fore.GREEN
        },
        "3": {
            "name": "claude-3-opus-20240229",
            "description": "Most capable, most expensive",
            "color": Fore.MAGENTA
        },
        "4": {
            "name": "claude-3-haiku-20240307",
            "description": "Fast and efficient",
            "color": Fore.YELLOW
        }
    }
    
    def __init__(self, difficulty: int = 2, api_key: str = None, model: str = None):
        # Load environment variables from .env file
        load_dotenv()
        
        self.blockchain = Blockchain(difficulty=difficulty)
        self.conversation_history = []
        self.session_id = self.generate_session_id()
        self.api_key = api_key or os.getenv('CLAUDE_API_KEY')
        self.model = model or self.select_model()
        self.conversation_context = []
        
        if not self.api_key:
            print(f"{Fore.RED}Warning: No Claude API key found!")
            print(f"{Fore.YELLOW}Please set CLAUDE_API_KEY in .env file, environment variable, or provide it as parameter")
            print(f"{Fore.CYAN}You can get your API key from: https://console.anthropic.com/")
        
    def select_model(self) -> str:
        """Let user select a Claude model."""
        print(f"\n{Fore.CYAN}Available Claude Models:")
        print(f"{Fore.CYAN}{'='*50}")
        
        for key, model_info in self.AVAILABLE_MODELS.items():
            color = model_info["color"]
            print(f"{color}[{key}] {model_info['name']}")
            print(f"{Fore.WHITE}    {model_info['description']}")
        
        while True:
            try:
                choice = input(f"\n{Fore.GREEN}Select model (1-4, default=1): ").strip()
                if not choice:
                    choice = "1"
                
                if choice in self.AVAILABLE_MODELS:
                    selected_model = self.AVAILABLE_MODELS[choice]["name"]
                    color = self.AVAILABLE_MODELS[choice]["color"]
                    print(f"{color}Selected: {selected_model}")
                    return selected_model
                else:
                    print(f"{Fore.RED}Invalid choice. Please select 1-4.")
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Using default model: claude-3-5-sonnet-20241022")
                return "claude-3-5-sonnet-20241022"
        
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
            return f"{Fore.RED}Error: No API key configured. Please set CLAUDE_API_KEY environment variable."
        
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
                return f"{Fore.RED}Error calling Claude API: {result.stderr}"
            
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
                return f"{Fore.RED}Error: Unexpected API response format: {response_data}"
                
        except subprocess.TimeoutExpired:
            return f"{Fore.RED}Error: API call timed out"
        except json.JSONDecodeError:
            return f"{Fore.RED}Error: Invalid JSON response from API: {result.stdout}"
        except Exception as e:
            return f"{Fore.RED}Error calling Claude API: {str(e)}"
    
    def display_hash_info(self, text: str, text_type: str, block: Block = None):
        """Display hash information for text with colors."""
        hash_value = self.hash_string(text)
        
        # Choose color based on type
        if text_type == "USER INPUT":
            color = Fore.BLUE
            border_color = Fore.CYAN
        else:  # CLAUDE RESPONSE
            color = Fore.GREEN
            border_color = Fore.YELLOW
        
        print(f"\n{border_color}{'='*60}")
        print(f"{color}{text_type.upper()} HASHING INFO:")
        print(f"{border_color}{'='*60}")
        print(f"{Fore.WHITE}Text: {text}")
        print(f"{Fore.CYAN}SHA-256 Hash: {hash_value}")
        print(f"{Fore.WHITE}Hash Length: {len(hash_value)} characters")
        
        if block:
            print(f"{Fore.MAGENTA}Block Index: {block.index}")
            print(f"{Fore.CYAN}Block Hash: {block.hash}")
            print(f"{Fore.YELLOW}Nonce: {block.nonce}")
            print(f"{Fore.WHITE}Mining Difficulty: {self.blockchain.difficulty}")
            print(f"{Fore.GREEN}Timestamp: {datetime.fromtimestamp(block.timestamp)}")
        
        print(f"{border_color}{'='*60}")
    
    def display_blockchain_status(self):
        """Display current blockchain status with colors."""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}BLOCKCHAIN STATUS:")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.GREEN}Session ID: {self.session_id}")
        print(f"{Fore.WHITE}Total Blocks: {len(self.blockchain.chain)}")
        print(f"{Fore.GREEN if self.blockchain.is_chain_valid() else Fore.RED}Chain Valid: {self.blockchain.is_chain_valid()}")
        print(f"{Fore.YELLOW}Mining Difficulty: {self.blockchain.difficulty}")
        print(f"{Fore.MAGENTA}Pending Data: {len(self.blockchain.pending_data)} items")
        print(f"{Fore.GREEN if self.api_key else Fore.RED}API Key Configured: {'Yes' if self.api_key else 'No'}")
        
        # Show model with color
        for key, model_info in self.AVAILABLE_MODELS.items():
            if model_info["name"] == self.model:
                color = model_info["color"]
                print(f"{color}Model: {self.model}")
                break
        else:
            print(f"{Fore.WHITE}Model: {self.model}")
        
        print(f"{Fore.CYAN}{'='*60}")
    
    def display_full_chain(self):
        """Display the entire blockchain with colors."""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}FULL BLOCKCHAIN:")
        print(f"{Fore.CYAN}{'='*60}")
        
        for i, block in enumerate(self.blockchain.chain):
            print(f"\n{Fore.MAGENTA}Block {i}:")
            print(f"{Fore.WHITE}  Index: {block.index}")
            
            # Parse and display the data more clearly
            try:
                data_list = json.loads(block.data)
                for data_item in data_list:
                    data_obj = json.loads(data_item)
                    data_type = data_obj.get('type', 'unknown')
                    
                    if data_type == "user_input":
                        type_color = Fore.BLUE
                        content_color = Fore.WHITE
                    elif data_type == "claude_response":
                        type_color = Fore.GREEN
                        content_color = Fore.WHITE
                    else:
                        type_color = Fore.YELLOW
                        content_color = Fore.WHITE
                    
                    print(f"{type_color}  Type: {data_type}")
                    content = data_obj.get('content', '')
                    print(f"{content_color}  Content: {content[:100]}{'...' if len(content) > 100 else ''}")
                    print(f"{Fore.CYAN}  Timestamp: {data_obj.get('timestamp', '')}")
            except:
                print(f"{Fore.WHITE}  Data: {block.data}")
            
            print(f"{Fore.CYAN}  Previous Hash: {block.previous_hash[:20]}...")
            print(f"{Fore.GREEN}  Hash: {block.hash}")
            print(f"{Fore.YELLOW}  Nonce: {block.nonce}")
            print(f"{Fore.WHITE}  Timestamp: {datetime.fromtimestamp(block.timestamp)}")
            print(f"{Fore.CYAN}{'  '+'-'*38}")
    
    def run(self):
        """Run the interactive CLI."""
        print(f"{Fore.CYAN}Claude CLI with Blockchain Hashing - Enhanced Version")
        print(f"{Fore.CYAN}{'=' * 60}")
        print(f"{Fore.WHITE}Type your messages to interact with Claude.")
        print(f"{Fore.WHITE}Each message and response will be hashed and added to the blockchain.")
        print(f"{Fore.YELLOW}Commands:")
        print(f"{Fore.GREEN}  /status - Show blockchain status")
        print(f"{Fore.GREEN}  /chain - Display full blockchain")
        print(f"{Fore.GREEN}  /save <filename> - Save blockchain to file")
        print(f"{Fore.GREEN}  /load <filename> - Load blockchain from file")
        print(f"{Fore.GREEN}  /clear - Clear conversation context")
        print(f"{Fore.GREEN}  /model - Change Claude model")
        print(f"{Fore.GREEN}  /quit or /exit - Exit the program")
        print(f"{Fore.CYAN}{'=' * 60}")
        
        if not self.api_key:
            print(f"\n{Fore.RED}WARNING: No API key configured!")
            print(f"{Fore.YELLOW}Please set CLAUDE_API_KEY environment variable or restart with API key parameter")
            print(f"{Fore.CYAN}Example: export CLAUDE_API_KEY='your-api-key-here'")
        
        while True:
            try:
                # Get user input
                user_input = input(f"\n{Fore.BLUE}You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    self.handle_command(user_input)
                    continue
                
                # Hash and display user input
                print(f"\n{Fore.CYAN}Processing your input...")
                user_block = self.add_to_blockchain(user_input, "user_input")
                self.display_hash_info(user_input, "USER INPUT", user_block)
                
                # Call Claude API
                print(f"\n{Fore.GREEN}Calling Claude API...")
                claude_response = self.call_claude_api(user_input)
                
                # Hash and display Claude's response
                claude_block = self.add_to_blockchain(claude_response, "claude_response")
                self.display_hash_info(claude_response, "CLAUDE RESPONSE", claude_block)
                
                # Display Claude's response
                print(f"\n{Fore.GREEN}Claude: {claude_response}")
                
                # Add to conversation history
                self.conversation_history.append({
                    "user_input": user_input,
                    "claude_response": claude_response,
                    "user_hash": self.hash_string(user_input),
                    "claude_hash": self.hash_string(claude_response),
                    "timestamp": datetime.now().isoformat()
                })
                
            except KeyboardInterrupt:
                print(f"\n\n{Fore.YELLOW}Exiting...")
                break
            except Exception as e:
                print(f"\n{Fore.RED}Error: {e}")
    
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
                print(f"{Fore.RED}Usage: /save <filename>")
                return
            filename = parts[1]
            try:
                self.blockchain.save_to_file(filename)
                print(f"{Fore.GREEN}Blockchain saved to {filename}")
            except Exception as e:
                print(f"{Fore.RED}Error saving blockchain: {e}")
        
        elif cmd == '/load':
            if len(parts) < 2:
                print(f"{Fore.RED}Usage: /load <filename>")
                return
            filename = parts[1]
            try:
                self.blockchain = Blockchain.load_from_file(filename)
                print(f"{Fore.GREEN}Blockchain loaded from {filename}")
            except Exception as e:
                print(f"{Fore.RED}Error loading blockchain: {e}")
        
        elif cmd == '/clear':
            self.conversation_context = []
            print(f"{Fore.YELLOW}Conversation context cleared")
        
        elif cmd == '/model':
            print(f"{Fore.CYAN}Current model: {self.model}")
            self.model = self.select_model()
        
        elif cmd in ['/quit', '/exit']:
            print(f"{Fore.GREEN}Goodbye!")
            sys.exit(0)
        
        else:
            print(f"{Fore.RED}Unknown command: {cmd}")
            print(f"{Fore.YELLOW}Available commands: /status, /chain, /save, /load, /clear, /model, /quit, /exit")


def main():
    """Main function to run the Claude CLI."""
    print(f"{Fore.CYAN}Starting Claude CLI with Enhanced Features...")
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Check for API key
    api_key = os.getenv('CLAUDE_API_KEY')
    if not api_key:
        print(f"{Fore.YELLOW}No CLAUDE_API_KEY found in .env file or environment variables.")
        api_key = input(f"{Fore.CYAN}Enter your Claude API key (or press Enter to skip): ").strip()
        if api_key:
            os.environ['CLAUDE_API_KEY'] = api_key
    
    # Set mining difficulty (lower for faster mining during demo)
    difficulty = 2
    
    cli = ClaudeCLIEnhanced(difficulty=difficulty, api_key=api_key)
    cli.run()


if __name__ == "__main__":
    main()
