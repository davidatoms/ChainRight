#!/usr/bin/env python3
"""
Multi-Provider Blockchain CLI
Interactive command line interface supporting multiple AI providers.
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
from .global_conversation_blockchain import GlobalConversationBlockchain

# Initialize colorama
init(autoreset=True)


class MultiProviderCLI:
    """CLI for interacting with multiple AI providers with blockchain hashing."""
    
    def __init__(self, config_path: str = "config/providers.json", difficulty: int = 2):
        load_dotenv()
        self.config = self.load_config(config_path)
        self.difficulty = difficulty
        self.global_blockchain = GlobalConversationBlockchain(difficulty=difficulty)
        
        self.user_id = self.get_or_create_user_id()
        self.session_id = self.generate_session_id()
        self.conversation_context = []
        
        # Selection state
        self.provider = None
        self.model = None
        self.api_key = None
        
    def load_config(self, path: str) -> Dict:
        """Load provider configuration."""
        if not os.path.exists(path):
            print(f"{Fore.RED}Error: Config file not found at {path}")
            sys.exit(1)
        with open(path, 'r') as f:
            return json.load(f)

    def get_or_create_user_id(self) -> str:
        """Get or create user ID."""
        user_id_file = ".user_id"
        if os.path.exists(user_id_file):
            with open(user_id_file, 'r') as f:
                return f.read().strip()
        
        user_id = f"user_{int(time.time())}_{os.getpid()}"
        with open(user_id_file, 'w') as f:
            f.write(user_id)
        return user_id

    def generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]

    def select_provider_and_model(self):
        """Interactive selection of provider and model."""
        print(f"\n{Fore.CYAN}Available AI Providers:")
        print(f"{Fore.CYAN}{'='*50}")
        
        providers = self.config['providers']
        for i, p in enumerate(providers):
            print(f"{Fore.GREEN}[{i+1}] {p['name']} ({p['company']})")
        
        while True:
            try:
                p_choice = input(f"\n{Fore.YELLOW}Select provider (1-{len(providers)}): ").strip()
                p_idx = int(p_choice) - 1
                if 0 <= p_idx < len(providers):
                    self.provider = providers[p_idx]
                    break
                print(f"{Fore.RED}Invalid choice.")
            except (ValueError, IndexError):
                print(f"{Fore.RED}Please enter a valid number.")

        print(f"\n{Fore.CYAN}Available Models for {self.provider['name']}:")
        print(f"{Fore.CYAN}{'='*50}")
        models = self.provider['models']
        for i, m in enumerate(models):
            print(f"{Fore.GREEN}[{i+1}] {m['display_name']}")
            print(f"{Fore.WHITE}    {m['description']}")
            
        while True:
            try:
                m_choice = input(f"\n{Fore.YELLOW}Select model (1-{len(models)}): ").strip()
                m_idx = int(m_choice) - 1
                if 0 <= m_idx < len(models):
                    self.model = models[m_idx]
                    break
                print(f"{Fore.RED}Invalid choice.")
            except (ValueError, IndexError):
                print(f"{Fore.RED}Please enter a valid number.")

        # Check for API key
        env_var = self.provider['api_env_var']
        self.api_key = os.getenv(env_var)
        
        if not self.api_key:
            print(f"\n{Fore.RED}Warning: {env_var} not found in environment.")
            self.api_key = input(f"{Fore.CYAN}Enter API key for {self.provider['name']}: ").strip()
            if not self.api_key:
                print(f"{Fore.RED}No API key provided. Exiting.")
                sys.exit(1)
            os.environ[env_var] = self.api_key

        print(f"\n{Fore.GREEN}Active Provider: {self.provider['name']}")
        print(f"{Fore.GREEN}Active Model: {self.model['display_name']} ({self.model['id']})")

    def call_api(self, user_input: str) -> str:
        """Call the selected provider's API."""
        provider_name = self.provider['name'].lower()
        
        if provider_name == "anthropic":
            return self._call_anthropic(user_input)
        elif provider_name == "google":
            return self._call_google(user_input)
        else:
            # Most others (OpenAI, Groq, Mistral, DeepSeek) are OpenAI-compatible
            return self._call_openai_compatible(user_input)

    def _call_anthropic(self, user_input: str) -> str:
        messages = []
        for entry in self.conversation_context[-5:]:
            messages.append({"role": "user", "content": entry["user"]})
            messages.append({"role": "assistant", "content": entry["ai"]})
        messages.append({"role": "user", "content": user_input})

        payload = {
            "model": self.model['id'],
            "max_tokens": 1024,
            "messages": messages,
            "system": "You are a helpful AI assistant. Be concise and accurate."
        }

        headers = [
            "-H", f"x-api-key: {self.api_key}",
            "-H", "content-type: application/json",
            "-H", "anthropic-version: 2023-06-01"
        ]
        
        return self._execute_curl(self.provider['base_url'], payload, headers, "content[0].text")

    def _call_openai_compatible(self, user_input: str) -> str:
        messages = [{"role": "system", "content": "You are a helpful AI assistant."}]
        for entry in self.conversation_context[-5:]:
            messages.append({"role": "user", "content": entry["user"]})
            messages.append({"role": "assistant", "content": entry["ai"]})
        messages.append({"role": "user", "content": user_input})

        payload = {
            "model": self.model['id'],
            "messages": messages,
            "max_tokens": 1024
        }

        headers = [
            "-H", f"Authorization: Bearer {self.api_key}",
            "-H", "Content-Type: application/json"
        ]
        
        return self._execute_curl(self.provider['base_url'], payload, headers, "choices[0].message.content")

    def _call_google(self, user_input: str) -> str:
        # Simplified Google Gemini call (v1beta)
        url = f"{self.provider['base_url']}{self.model['id']}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": user_input}]}]
        }
        
        headers = ["-H", "Content-Type: application/json"]
        
        return self._execute_curl(url, payload, headers, "candidates[0].content.parts[0].text")

    def _execute_curl(self, url: str, payload: Dict, headers: List[str], response_path: str) -> str:
        try:
            cmd = ["curl", "-s", "-X", "POST", url] + headers + ["-d", json.dumps(payload)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return f"Error: {result.stderr}"
            
            data = json.loads(result.stdout)
            
            # Simple path traversal for JSON response
            parts = response_path.replace('[', '.').replace(']', '').split('.')
            val = data
            for part in parts:
                if part.isdigit():
                    val = val[int(part)]
                else:
                    val = val[part]
            return val
        except Exception as e:
            return f"Error: {str(e)}\nResponse: {result.stdout if 'result' in locals() else 'No response'}"

    def run(self):
        """Main loop."""
        from .device_awareness import DeviceAwareness
        device = DeviceAwareness.classify_device()
        
        print(f"{Fore.CYAN}ChainRight Multi-Provider Blockchain CLI")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.MAGENTA}Node Classification: {device['type']}")
        print(f"{Fore.MAGENTA}P2P Handshake Ready: {'YES (T)' if device['p2p_status'] else 'NO (F)'}")
        print(f"{Fore.WHITE}System Specs: {device['metrics']['cpus']} CPUs, {device['metrics']['ram_gb']}GB RAM")
        print(f"{Fore.CYAN}{'='*60}")
        
        self.select_provider_and_model()
        
        print(f"\n{Fore.WHITE}System ready. Commands: /stats, /model, /quit")
        
        while True:
            try:
                user_input = input(f"\n{Fore.BLUE}You: ").strip()
                if not user_input: continue
                
                if user_input.startswith('/'):
                    if user_input == '/quit': break
                    if user_input == '/model': 
                        self.select_provider_and_model()
                        continue
                    if user_input == '/stats':
                        self.global_blockchain.display_stats()
                        continue
                
                # 1. Hash and Add User Input
                user_block = self.global_blockchain.add_conversation_entry(
                    self.user_id, user_input, "user_input", self.session_id,
                    metadata={"provider": self.provider['name'], "model": self.model['id']}
                )
                print(f"{Fore.CYAN}[Block {user_block.index}] Hashed User Input")
                
                # 2. Get AI Response with Latency Tracking
                print(f"{Fore.YELLOW}Requesting {self.provider['name']}...")
                start_time = time.time()
                ai_response = self.call_api(user_input)
                latency_ms = (time.time() - start_time) * 1000
                
                # 3. Hash and Add AI Response with Latency/Hops
                ai_block = self.global_blockchain.add_conversation_entry(
                    self.provider['name'].lower(), ai_response, "ai_response", self.session_id,
                    latency_ms=latency_ms,
                    metadata={
                        "model": self.model['id'],
                        "internal_hops": 1, # Default for direct API call
                        "latency_ms": latency_ms
                    }
                )
                print(f"{Fore.CYAN}[Block {ai_block.index}] Hashed AI Response (Latency: {latency_ms:.2f}ms)")
                
                # 4. Display
                print(f"\n{Fore.GREEN}{self.provider['name']}: {ai_response}")
                
                # 5. Update context
                self.conversation_context.append({"user": user_input, "ai": ai_response})
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"{Fore.RED}Error: {e}")
        
        print(f"\n{Fore.GREEN}Goodbye!")


def main():
    cli = MultiProviderCLI()
    cli.run()

if __name__ == "__main__":
    main()
