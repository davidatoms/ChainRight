#!/usr/bin/env python3
"""
Input/Output Token Tracking with Claude API
Tracks input tokens from user and output tokens from Claude API responses,
attributing outputs to the specific curl script JSON used for the request.
"""

import json
import subprocess
import time
import hashlib
import os
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from ownership_blockchain import OwnershipBlockchain, OwnedSentence


class ClaudeAPIClient:
    """Client for interacting with Claude API via curl."""
    
    def __init__(self, api_key: str = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.getenv('CLAUDE_API_KEY')
        self.model = model
        self.base_url = "https://api.anthropic.com/v1/messages"
        
        # Don't raise error here - let the calling code handle it
    
    def create_curl_script(self, prompt: str, max_tokens: int = 1000) -> Dict[str, Any]:
        """Create a curl script JSON for the API request."""
        curl_data = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        return curl_data
    
    def execute_curl_request(self, curl_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the curl request and return the response."""
        # Convert curl data to JSON string
        json_data = json.dumps(curl_data)
        
        # Create curl command
        curl_command = [
            "curl", "-X", "POST", self.base_url,
            "-H", "Content-Type: application/json",
            "-H", f"x-api-key: {self.api_key}",
            "-H", "anthropic-version: 2023-06-01",
            "-d", json_data
        ]
        
        try:
            # Execute curl command
            result = subprocess.run(
                curl_command,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                return response
            else:
                raise Exception(f"Curl request failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise Exception("Request timed out")
        except json.JSONDecodeError:
            raise Exception(f"Invalid JSON response: {result.stdout}")
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")


class TokenTracker:
    """Tracks input and output tokens with blockchain attribution."""
    
    def __init__(self, blockchain: OwnershipBlockchain):
        self.blockchain = blockchain
        self.session_id = f"session_{int(time.time())}"
    
    def calculate_input_tokens(self, prompt: str) -> int:
        """Estimate input tokens (rough approximation)."""
        # Rough estimation: 1 token ≈ 4 characters for English text
        return len(prompt) // 4
    
    def extract_output_tokens(self, response: Dict[str, Any]) -> int:
        """Extract output tokens from Claude API response."""
        try:
            return response.get('usage', {}).get('output_tokens', 0)
        except:
            return 0
    
    def extract_input_tokens(self, response: Dict[str, Any]) -> int:
        """Extract input tokens from Claude API response."""
        try:
            return response.get('usage', {}).get('input_tokens', 0)
        except:
            return 0
    
    def create_curl_script_hash(self, curl_data: Dict[str, Any]) -> str:
        """Create a hash of the curl script for attribution."""
        json_string = json.dumps(curl_data, sort_keys=True)
        return hashlib.sha256(json_string.encode()).hexdigest()
    
    def record_interaction(self, 
                          user_prompt: str, 
                          curl_data: Dict[str, Any], 
                          api_response: Dict[str, Any],
                          user_name: str = "user") -> Dict[str, Any]:
        """Record the interaction in the blockchain."""
        
        # Extract token information
        input_tokens = self.extract_input_tokens(api_response)
        output_tokens = self.extract_output_tokens(api_response)
        curl_hash = self.create_curl_script_hash(curl_data)
        
        # Create interaction record
        interaction_data = {
            "session_id": self.session_id,
            "timestamp": time.time(),
            "user_prompt": user_prompt,
            "curl_script_hash": curl_hash,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model": curl_data.get("model", "unknown"),
            "max_tokens": curl_data.get("max_tokens", 0)
        }
        
        # Add to blockchain
        interaction_sentence = f"Claude API interaction: {input_tokens} input tokens, {output_tokens} output tokens, curl_hash: {curl_hash[:16]}..."
        self.blockchain.add_sentence(interaction_sentence, user_name)
        
        # Add detailed record
        details_sentence = f"Prompt: '{user_prompt[:100]}{'...' if len(user_prompt) > 100 else ''}', Model: {curl_data.get('model')}, Max tokens: {curl_data.get('max_tokens')}"
        self.blockchain.add_sentence(details_sentence, f"{user_name}_details")
        
        return interaction_data


class ClaudeInteractionManager:
    """Manages Claude API interactions with token tracking."""
    
    def __init__(self, api_key: str = None, blockchain: OwnershipBlockchain = None):
        self.client = ClaudeAPIClient(api_key)
        self.blockchain = blockchain or OwnershipBlockchain(difficulty=1)
        self.tracker = TokenTracker(self.blockchain)
        
        # Initialize blockchain if needed
        if len(self.blockchain.chain) == 0:
            today = date.today().isoformat()
            self.blockchain.create_genesis_block(today)
    
    def interact_with_claude(self, 
                           prompt: str, 
                           user_name: str = "user",
                           max_tokens: int = 1000) -> Dict[str, Any]:
        """Interact with Claude and track tokens."""
        
        print(f"Interacting with Claude as {user_name}...")
        print(f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        
        # Create curl script
        curl_data = self.client.create_curl_script(prompt, max_tokens)
        
        # Execute request
        try:
            response = self.client.execute_curl_request(curl_data)
            
            # Record interaction
            interaction_data = self.tracker.record_interaction(
                prompt, curl_data, response, user_name
            )
            
            # Extract Claude's response
            claude_response = ""
            if 'content' in response and len(response['content']) > 0:
                claude_response = response['content'][0].get('text', '')
            
            # Add Claude's response to blockchain
            if claude_response:
                response_sentence = f"Claude response: '{claude_response[:100]}{'...' if len(claude_response) > 100 else ''}'"
                self.blockchain.add_sentence(response_sentence, "claude")
            
            # Mine the block
            today = date.today().isoformat()
            new_block = self.blockchain.mine_pending_sentences(today)
            
            print(f"Interaction recorded in block {new_block.index}")
            print(f"Input tokens: {interaction_data['input_tokens']}")
            print(f"Output tokens: {interaction_data['output_tokens']}")
            print(f"Curl script hash: {interaction_data['curl_script_hash'][:16]}...")
            
            return {
                "success": True,
                "claude_response": claude_response,
                "interaction_data": interaction_data,
                "block_hash": new_block.hash,
                "block_index": new_block.index
            }
            
        except Exception as e:
            error_sentence = f"Claude API error: {str(e)}"
            self.blockchain.add_sentence(error_sentence, user_name)
            
            # Mine error block
            today = date.today().isoformat()
            self.blockchain.mine_pending_sentences(today)
            
            print(f"Error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "claude_response": None,
                "interaction_data": None
            }
    
    def get_token_statistics(self) -> Dict[str, Any]:
        """Get statistics about token usage."""
        all_sentences = []
        for block in self.blockchain.chain:
            all_sentences.extend(block.sentences)
        
        # Extract token information from sentences
        total_input_tokens = 0
        total_output_tokens = 0
        curl_hashes = set()
        users = set()
        
        for sentence in all_sentences:
            if "input tokens" in sentence.text and "output tokens" in sentence.text:
                # Parse token information
                parts = sentence.text.split(',')
                for part in parts:
                    if 'input tokens' in part:
                        try:
                            tokens = int(part.split()[0])
                            total_input_tokens += tokens
                        except:
                            pass
                    elif 'output tokens' in part:
                        try:
                            tokens = int(part.split()[0])
                            total_output_tokens += tokens
                        except:
                            pass
                    elif 'curl_hash' in part:
                        hash_part = part.split(':')[1].strip()
                        curl_hashes.add(hash_part)
            
            if sentence.author != "system":
                users.add(sentence.author)
        
        return {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_interactions": len([s for s in all_sentences if "input tokens" in s.text]),
            "unique_curl_scripts": len(curl_hashes),
            "unique_users": len(users),
            "users": list(users),
            "curl_hashes": list(curl_hashes)
        }
    
    def save_blockchain(self, filename: str = None) -> str:
        """Save the blockchain to a file."""
        if filename is None:
            today = date.today().isoformat()
            filename = f"claude_interactions_{today}.json"
        
        self.blockchain.save_to_file(filename)
        return filename


def demo_claude_interaction():
    """Demonstrate Claude interaction with token tracking."""
    print("Claude API Token Tracking Demo")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv('CLAUDE_API_KEY')
    if not api_key:
        print("No CLAUDE_API_KEY found in environment variables.")
        print("   Set your Claude API key: export CLAUDE_API_KEY='your-key-here'")
        print("   Or the demo will use mock data.")
        use_mock = True
    else:
        use_mock = False
    
    # Create interaction manager
    manager = ClaudeInteractionManager(api_key)
    
    # Sample interactions
    interactions = [
        {
            "user": "Alice",
            "prompt": "Explain quantum computing in simple terms."
        },
        {
            "user": "Bob", 
            "prompt": "Write a Python function to calculate fibonacci numbers."
        },
        {
            "user": "Carol",
            "prompt": "What are the main differences between Python and JavaScript?"
        }
    ]
    
    if use_mock:
        print("Using mock data for demonstration...")
        
        # Mock interactions
        for interaction in interactions:
            print(f"\n{interaction['user']}: {interaction['prompt']}")
            
            # Add mock interaction to blockchain
            mock_sentence = f"Claude API interaction: 25 input tokens, 150 output tokens, curl_hash: {hashlib.sha256(interaction['prompt'].encode()).hexdigest()[:16]}..."
            manager.blockchain.add_sentence(mock_sentence, interaction['user'])
            
            # Add mock response
            mock_response = f"Mock Claude response to: {interaction['prompt'][:50]}..."
            manager.blockchain.add_sentence(mock_response, "claude")
            
            # Mine block
            today = date.today().isoformat()
            block = manager.blockchain.mine_pending_sentences(today)
            
            print(f"Mock interaction recorded in block {block.index}")
            print(f"Input tokens: 25, Output tokens: 150")
    
    else:
        print("Using real Claude API...")
        
        # Real interactions
        for interaction in interactions:
            print(f"\n{interaction['user']}: {interaction['prompt']}")
            
            result = manager.interact_with_claude(
                interaction['prompt'], 
                interaction['user'],
                max_tokens=500
            )
            
            if result['success']:
                print(f"Claude: {result['claude_response'][:100]}...")
            else:
                print(f"Error: {result['error']}")
    
    # Show statistics
    print(f"\n{'='*50}")
    print("TOKEN USAGE STATISTICS")
    print(f"{'='*50}")
    
    stats = manager.get_token_statistics()
    
    print(f"Total input tokens: {stats['total_input_tokens']:,}")
    print(f"Total output tokens: {stats['total_output_tokens']:,}")
    print(f"Total interactions: {stats['total_interactions']}")
    print(f"Unique curl scripts: {stats['unique_curl_scripts']}")
    print(f"Unique users: {stats['unique_users']}")
    print(f"Users: {', '.join(stats['users'])}")
    
    # Save blockchain
    filename = manager.save_blockchain()
    print(f"\nBlockchain saved to: {filename}")
    
    return manager


def interactive_claude_session():
    """Interactive Claude API session with token tracking."""
    print("Interactive Claude API Session")
    print("=" * 40)
    
    # Check for API key
    api_key = os.getenv('CLAUDE_API_KEY')
    if not api_key:
        print("No CLAUDE_API_KEY found. Set it with: export CLAUDE_API_KEY='your-key-here'")
        return
    
    # Create interaction manager
    manager = ClaudeInteractionManager(api_key)
    
    print("Enter your name and prompts. Type 'quit' to exit, 'stats' for statistics.")
    
    while True:
        print(f"\n{'='*40}")
        
        # Get user name
        user_name = input("Enter your name: ").strip()
        if user_name.lower() == 'quit':
            break
        
        # Get prompt
        prompt = input("Enter your prompt: ").strip()
        if prompt.lower() == 'quit':
            break
        elif prompt.lower() == 'stats':
            stats = manager.get_token_statistics()
            print(f"\nToken Statistics:")
            print(f"  Input tokens: {stats['total_input_tokens']:,}")
            print(f"  Output tokens: {stats['total_output_tokens']:,}")
            print(f"  Interactions: {stats['total_interactions']}")
            continue
        
        if not prompt:
            continue
        
        # Interact with Claude
        result = manager.interact_with_claude(prompt, user_name)
        
        if result['success']:
            print(f"\nClaude's response:")
            print(f"{result['claude_response']}")
        else:
            print(f"\nError: {result['error']}")
    
    # Final statistics
    stats = manager.get_token_statistics()
    print(f"\n{'='*40}")
    print("FINAL STATISTICS")
    print(f"{'='*40}")
    print(f"Total input tokens: {stats['total_input_tokens']:,}")
    print(f"Total output tokens: {stats['total_output_tokens']:,}")
    print(f"Total interactions: {stats['total_interactions']}")
    
    # Save blockchain
    filename = manager.save_blockchain()
    print(f"Session saved to: {filename}")


if __name__ == "__main__":
    print("Claude API Token Tracking System")
    print("=" * 50)
    
    print("Choose mode:")
    print("1. Demo with sample interactions")
    print("2. Interactive session")
    
    choice = input("Enter choice (1-2): ").strip()
    
    if choice == "1":
        demo_claude_interaction()
    elif choice == "2":
        interactive_claude_session()
    else:
        print("Invalid choice, running demo...")
        demo_claude_interaction()
