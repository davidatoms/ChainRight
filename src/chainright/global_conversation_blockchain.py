#!/usr/bin/env python3
"""
Global Conversation Blockchain
A system for creating one massive blockchain of all conversations with permanent attribution.
"""

import hashlib
import json
import time
import subprocess
import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from colorama import init, Fore, Back, Style

# Import the blockchain classes
from .blockchain import Block, Blockchain

# Initialize colorama
init(autoreset=True)


class GlobalConversationBlockchain:
    """Global blockchain for tracking all conversations with permanent attribution."""
    
    def __init__(self, blockchain_file: str = "global_conversations.json", difficulty: int = 2):
        self.blockchain_file = blockchain_file
        self.difficulty = difficulty
        self.blockchain = self.load_or_create_blockchain()
        self.current_session = None
        
    def load_or_create_blockchain(self) -> Blockchain:
        """Load existing global blockchain or create new one."""
        if os.path.exists(self.blockchain_file):
            try:
                blockchain = Blockchain.load_from_file(self.blockchain_file)
                print(f"{Fore.GREEN}Loaded existing global blockchain with {len(blockchain.chain)} blocks")
                return blockchain
            except Exception as e:
                print(f"{Fore.YELLOW}Error loading existing blockchain: {e}")
                print(f"{Fore.CYAN}Creating new global blockchain...")
        
        # Create new blockchain
        blockchain = Blockchain(difficulty=self.difficulty)
        print(f"{Fore.GREEN}Created new global conversation blockchain")
        return blockchain
    
    def save_blockchain(self):
        """Save the global blockchain to file."""
        try:
            self.blockchain.save_to_file(self.blockchain_file)
            print(f"{Fore.GREEN}Global blockchain saved to {self.blockchain_file}")
        except Exception as e:
            print(f"{Fore.RED}Error saving blockchain: {e}")
    
    def add_conversation_entry(self, user_id: str, message: str, message_type: str, 
                              session_id: str, metadata: Dict = None) -> Block:
        """Add a conversation entry to the global blockchain."""
        
        # Create comprehensive metadata
        entry_data = {
            "user_id": user_id,
            "message": message,
            "message_type": message_type,  # "user_input" or "claude_response"
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "message_hash": hashlib.sha256(message.encode('utf-8')).hexdigest(),
            "user_hash": hashlib.sha256(user_id.encode('utf-8')).hexdigest(),
            "metadata": metadata or {}
        }
        
        # Add to blockchain
        self.blockchain.add_data(json.dumps(entry_data))
        block = self.blockchain.mine_pending_data()
        
        return block
    
    def verify_message_ownership(self, message: str, user_id: str = None) -> List[Dict]:
        """Verify who owns a specific message."""
        message_hash = hashlib.sha256(message.encode('utf-8')).hexdigest()
        results = []
        
        for block in self.blockchain.chain:
            try:
                data_list = json.loads(block.data)
                for data_item in data_list:
                    entry = json.loads(data_item)
                    
                    if entry.get("message_hash") == message_hash:
                        # Found the message
                        result = {
                            "block_index": block.index,
                            "user_id": entry.get("user_id"),
                            "message_type": entry.get("message_type"),
                            "timestamp": entry.get("timestamp"),
                            "session_id": entry.get("session_id"),
                            "block_hash": block.hash,
                            "is_owner": user_id is None or entry.get("user_id") == user_id
                        }
                        results.append(result)
                        
            except (json.JSONDecodeError, KeyError):
                continue
        
        return results
    
    def search_user_conversations(self, user_id: str) -> List[Dict]:
        """Search all conversations by a specific user."""
        conversations = []
        
        for block in self.blockchain.chain:
            try:
                data_list = json.loads(block.data)
                for data_item in data_list:
                    entry = json.loads(data_item)
                    
                    if entry.get("user_id") == user_id:
                        conversation = {
                            "block_index": block.index,
                            "message": entry.get("message"),
                            "message_type": entry.get("message_type"),
                            "timestamp": entry.get("timestamp"),
                            "session_id": entry.get("session_id"),
                            "block_hash": block.hash
                        }
                        conversations.append(conversation)
                        
            except (json.JSONDecodeError, KeyError):
                continue
        
        return conversations
    
    def search_message_content(self, search_term: str) -> List[Dict]:
        """Search for messages containing specific content."""
        results = []
        search_term_lower = search_term.lower()
        
        for block in self.blockchain.chain:
            try:
                data_list = json.loads(block.data)
                for data_item in data_list:
                    entry = json.loads(data_item)
                    message = entry.get("message", "")
                    
                    if search_term_lower in message.lower():
                        result = {
                            "block_index": block.index,
                            "user_id": entry.get("user_id"),
                            "message": message,
                            "message_type": entry.get("message_type"),
                            "timestamp": entry.get("timestamp"),
                            "session_id": entry.get("session_id"),
                            "block_hash": block.hash
                        }
                        results.append(result)
                        
            except (json.JSONDecodeError, KeyError):
                continue
        
        return results
    
    def get_blockchain_stats(self) -> Dict:
        """Get comprehensive blockchain statistics."""
        total_messages = 0
        user_messages = 0
        claude_messages = 0
        unique_users = set()
        unique_sessions = set()
        
        for block in self.blockchain.chain:
            try:
                data_list = json.loads(block.data)
                for data_item in data_list:
                    entry = json.loads(data_item)
                    total_messages += 1
                    
                    user_id = entry.get("user_id")
                    if user_id:
                        unique_users.add(user_id)
                    
                    session_id = entry.get("session_id")
                    if session_id:
                        unique_sessions.add(session_id)
                    
                    if entry.get("message_type") == "user_input":
                        user_messages += 1
                    elif entry.get("message_type") == "claude_response":
                        claude_messages += 1
                        
            except (json.JSONDecodeError, KeyError):
                continue
        
        return {
            "total_blocks": len(self.blockchain.chain),
            "total_messages": total_messages,
            "user_messages": user_messages,
            "claude_messages": claude_messages,
            "unique_users": len(unique_users),
            "unique_sessions": len(unique_sessions),
            "chain_valid": self.blockchain.is_chain_valid(),
            "difficulty": self.blockchain.difficulty
        }
    
    def display_stats(self):
        """Display blockchain statistics with colors."""
        stats = self.get_blockchain_stats()
        
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}GLOBAL CONVERSATION BLOCKCHAIN STATISTICS")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.GREEN}Total Blocks: {stats['total_blocks']}")
        print(f"{Fore.WHITE}Total Messages: {stats['total_messages']}")
        print(f"{Fore.BLUE}User Messages: {stats['user_messages']}")
        print(f"{Fore.GREEN}Claude Messages: {stats['claude_messages']}")
        print(f"{Fore.MAGENTA}Unique Users: {stats['unique_users']}")
        print(f"{Fore.YELLOW}Unique Sessions: {stats['unique_sessions']}")
        print(f"{Fore.GREEN if stats['chain_valid'] else Fore.RED}Chain Valid: {stats['chain_valid']}")
        print(f"{Fore.CYAN}Mining Difficulty: {stats['difficulty']}")
        print(f"{Fore.CYAN}{'='*60}")


class GlobalConversationCLI:
    """CLI for the global conversation blockchain system."""
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id or self.get_user_id()
        self.global_blockchain = GlobalConversationBlockchain()
        self.session_id = self.generate_session_id()
        self.api_key = os.getenv('CLAUDE_API_KEY')
        
    def get_user_id(self) -> str:
        """Get or create user ID."""
        user_id_file = ".user_id"
        
        if os.path.exists(user_id_file):
            with open(user_id_file, 'r') as f:
                return f.read().strip()
        
        # Create new user ID
        user_id = f"user_{int(time.time())}_{os.getpid()}"
        with open(user_id_file, 'w') as f:
            f.write(user_id)
        
        print(f"{Fore.GREEN}Created new user ID: {user_id}")
        return user_id
    
    def generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = str(time.time())
        return hashlib.sha256(timestamp.encode()).hexdigest()[:8]
    
    def call_claude_api(self, user_input: str) -> str:
        """Call Claude API."""
        if not self.api_key:
            return f"{Fore.RED}Error: No API key configured."
        
        api_request = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": user_input}]
        }
        
        try:
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
            
            response_data = json.loads(result.stdout)
            
            if "content" in response_data and len(response_data["content"]) > 0:
                return response_data["content"][0]["text"]
            else:
                return f"{Fore.RED}Error: Unexpected API response format"
                
        except Exception as e:
            return f"{Fore.RED}Error calling Claude API: {str(e)}"
    
    def run(self):
        """Run the global conversation CLI."""
        print(f"{Fore.CYAN}Global Conversation Blockchain CLI")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.WHITE}User ID: {self.user_id}")
        print(f"{Fore.WHITE}Session ID: {self.session_id}")
        print(f"{Fore.YELLOW}Commands:")
        print(f"{Fore.GREEN}  /stats - Show blockchain statistics")
        print(f"{Fore.GREEN}  /verify <message> - Verify message ownership")
        print(f"{Fore.GREEN}  /search <term> - Search message content")
        print(f"{Fore.GREEN}  /my-conversations - Show your conversations")
        print(f"{Fore.GREEN}  /save - Save blockchain")
        print(f"{Fore.GREEN}  /quit or /exit - Exit")
        print(f"{Fore.CYAN}{'='*60}")
        
        while True:
            try:
                user_input = input(f"\n{Fore.BLUE}You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.startswith('/'):
                    self.handle_command(user_input)
                    continue
                
                # Add user message to global blockchain
                print(f"\n{Fore.CYAN}Adding your message to global blockchain...")
                user_block = self.global_blockchain.add_conversation_entry(
                    self.user_id, user_input, "user_input", self.session_id
                )
                print(f"{Fore.GREEN}User message added to block {user_block.index}")
                
                # Get Claude response
                print(f"\n{Fore.GREEN}Getting Claude response...")
                claude_response = self.call_claude_api(user_input)
                
                # Add Claude response to global blockchain
                claude_block = self.global_blockchain.add_conversation_entry(
                    "claude", claude_response, "claude_response", self.session_id
                )
                print(f"{Fore.GREEN}Claude response added to block {claude_block.index}")
                
                # Display response
                print(f"\n{Fore.GREEN}Claude: {claude_response}")
                
            except KeyboardInterrupt:
                print(f"\n\n{Fore.YELLOW}Exiting...")
                self.global_blockchain.save_blockchain()
                break
            except Exception as e:
                print(f"\n{Fore.RED}Error: {e}")
    
    def handle_command(self, command: str):
        """Handle CLI commands."""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == '/stats':
            self.global_blockchain.display_stats()
        
        elif cmd == '/verify':
            if len(parts) < 2:
                print(f"{Fore.RED}Usage: /verify <message>")
                return
            message = ' '.join(parts[1:])
            results = self.global_blockchain.verify_message_ownership(message)
            
            if results:
                print(f"\n{Fore.CYAN}Message ownership verification:")
                for result in results:
                    owner_color = Fore.GREEN if result["is_owner"] else Fore.RED
                    print(f"{owner_color}Block {result['block_index']}: {result['user_id']} ({result['message_type']}) - {result['timestamp']}")
            else:
                print(f"{Fore.YELLOW}Message not found in blockchain")
        
        elif cmd == '/search':
            if len(parts) < 2:
                print(f"{Fore.RED}Usage: /search <term>")
                return
            search_term = ' '.join(parts[1:])
            results = self.global_blockchain.search_message_content(search_term)
            
            if results:
                print(f"\n{Fore.CYAN}Search results for '{search_term}':")
                for result in results[:10]:  # Show first 10 results
                    print(f"{Fore.WHITE}Block {result['block_index']}: {result['user_id']} - {result['message'][:100]}...")
                if len(results) > 10:
                    print(f"{Fore.YELLOW}... and {len(results) - 10} more results")
            else:
                print(f"{Fore.YELLOW}No messages found containing '{search_term}'")
        
        elif cmd == '/my-conversations':
            conversations = self.global_blockchain.search_user_conversations(self.user_id)
            
            if conversations:
                print(f"\n{Fore.CYAN}Your conversations:")
                for conv in conversations[-20:]:  # Show last 20
                    color = Fore.BLUE if conv["message_type"] == "user_input" else Fore.GREEN
                    print(f"{color}Block {conv['block_index']}: {conv['message'][:100]}...")
            else:
                print(f"{Fore.YELLOW}No conversations found for your user ID")
        
        elif cmd == '/save':
            self.global_blockchain.save_blockchain()
        
        elif cmd in ['/quit', '/exit']:
            print(f"{Fore.GREEN}Goodbye!")
            self.global_blockchain.save_blockchain()
            sys.exit(0)
        
        else:
            print(f"{Fore.RED}Unknown command: {cmd}")
            print(f"{Fore.YELLOW}Available commands: /stats, /verify, /search, /my-conversations, /save, /quit, /exit")


def main():
    """Main function."""
    print(f"{Fore.CYAN}Starting Global Conversation Blockchain...")
    
    # Load environment variables
    load_dotenv()
    
    cli = GlobalConversationCLI()
    cli.run()


if __name__ == "__main__":
    main()
