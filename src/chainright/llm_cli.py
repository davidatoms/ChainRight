#!/usr/bin/env python3
"""
LLM CLI with Blockchain Hashing
Provider-agnostic interactive CLI. Pass --provider and --model to select
any supported LLM; defaults to Anthropic / claude-3-5-sonnet-20241022.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
from colorama import init, Fore, Style

from .blockchain import Block, Blockchain

init(autoreset=True)

# Default config path relative to where the process runs
_DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), "..", "..", "config", "providers.json")


class LLMCli:
    """
    Provider-agnostic CLI that hashes every exchange into a blockchain.

    Parameters
    ----------
    provider : str
        Provider name matching an entry in providers.json (e.g. "anthropic").
        Case-insensitive.
    model : str, optional
        Model ID to use. Defaults to the first model listed for the provider.
    difficulty : int
        Proof-of-work mining difficulty (default 2).
    config_path : str
        Path to providers.json. Falls back to the bundled config.
    """

    def __init__(
        self,
        provider: str = "anthropic",
        model: Optional[str] = None,
        difficulty: int = 2,
        config_path: str = _DEFAULT_CONFIG,
    ):
        load_dotenv()

        self.blockchain = Blockchain(difficulty=difficulty)
        self.conversation_context: List[Dict] = []
        self.session_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]

        self.provider_config, self.model_config = self._resolve_provider(
            config_path, provider, model
        )
        self.api_key = self._resolve_api_key()
        self.provider_label = self.provider_config["name"]

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _resolve_provider(
        self, config_path: str, provider_name: str, model_id: Optional[str]
    ) -> tuple:
        """Load provider and model config from providers.json."""
        if not os.path.exists(config_path):
            print(f"{Fore.RED}Config not found: {config_path}")
            sys.exit(1)

        with open(config_path) as f:
            config = json.load(f)

        providers = config.get("providers", [])
        match = next(
            (p for p in providers if p["name"].lower() == provider_name.lower()), None
        )
        if match is None:
            available = [p["name"] for p in providers]
            print(f"{Fore.RED}Unknown provider '{provider_name}'. Available: {available}")
            sys.exit(1)

        models = match.get("models", [])
        if model_id:
            model = next((m for m in models if m["id"] == model_id), None)
            if model is None:
                available = [m["id"] for m in models]
                print(f"{Fore.RED}Unknown model '{model_id}'. Available: {available}")
                sys.exit(1)
        else:
            model = models[0] if models else {"id": provider_name, "display_name": provider_name}

        return match, model

    def _resolve_api_key(self) -> Optional[str]:
        """Read the API key from the environment variable named in the provider config."""
        env_var = self.provider_config.get("api_env_var", "")
        key = os.getenv(env_var) if env_var else None
        if not key:
            print(f"{Fore.YELLOW}Warning: {env_var} not set. Set it in .env or as an environment variable.")
        return key

    # ------------------------------------------------------------------
    # Blockchain helpers
    # ------------------------------------------------------------------

    def _mine(self, content: str, role: str) -> Block:
        entry = {
            "role": role,
            "provider": self.provider_label,
            "model": self.model_config["id"],
            "content": content,
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.blockchain.add_data(json.dumps(entry))
        return self.blockchain.mine_pending_data()

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # API dispatch
    # ------------------------------------------------------------------

    def _call_llm(self, user_input: str) -> str:
        """Route to the correct API implementation based on provider name."""
        name = self.provider_config["name"].lower()
        if name == "anthropic":
            return self._call_anthropic(user_input)
        elif name == "google":
            return self._call_google(user_input)
        else:
            return self._call_openai_compatible(user_input)

    def _build_messages(self, user_input: str) -> List[Dict]:
        messages = []
        for entry in self.conversation_context[-10:]:
            messages.append({"role": "user", "content": entry["user"]})
            messages.append({"role": "assistant", "content": entry["llm"]})
        messages.append({"role": "user", "content": user_input})
        return messages

    def _call_anthropic(self, user_input: str) -> str:
        payload = {
            "model": self.model_config["id"],
            "max_tokens": 1024,
            "messages": self._build_messages(user_input),
            "system": "You are a helpful AI assistant. Be concise and accurate.",
        }
        headers = [
            "-H", f"x-api-key: {self.api_key}",
            "-H", "content-type: application/json",
            "-H", "anthropic-version: 2023-06-01",
        ]
        return self._curl(self.provider_config["base_url"], payload, headers, "content.0.text")

    def _call_openai_compatible(self, user_input: str) -> str:
        messages = [{"role": "system", "content": "You are a helpful AI assistant."}]
        messages += self._build_messages(user_input)
        payload = {
            "model": self.model_config["id"],
            "messages": messages,
            "max_tokens": 1024,
        }
        headers = [
            "-H", f"Authorization: Bearer {self.api_key}",
            "-H", "Content-Type: application/json",
        ]
        return self._curl(self.provider_config["base_url"], payload, headers, "choices.0.message.content")

    def _call_google(self, user_input: str) -> str:
        url = f"{self.provider_config['base_url']}{self.model_config['id']}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": user_input}]}]}
        headers = ["-H", "Content-Type: application/json"]
        return self._curl(url, payload, headers, "candidates.0.content.parts.0.text")

    def _curl(self, url: str, payload: Dict, headers: List[str], path: str) -> str:
        """Execute a curl POST and extract a value by dot-path from the JSON response."""
        if not self.api_key and "key=" not in url:
            return "Error: no API key configured."
        try:
            cmd = ["curl", "-s", "-X", "POST", url] + headers + ["-d", json.dumps(payload)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return f"Error: {result.stderr}"
            data = json.loads(result.stdout)
            # Walk the dot-path (supports numeric indices)
            val = data
            for part in path.split("."):
                val = val[int(part)] if part.isdigit() else val[part]
            return str(val)
        except subprocess.TimeoutExpired:
            return "Error: request timed out."
        except (KeyError, IndexError, TypeError) as e:
            return f"Error: unexpected response shape ({e}). Raw: {result.stdout[:200]}"
        except json.JSONDecodeError:
            return f"Error: invalid JSON response. Raw: {result.stdout[:200]}"
        except Exception as e:
            return f"Error: {e}"

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def _print_block(self, block: Block, content: str, role: str):
        content_hash = self._hash(content)
        tag = "You" if role == "user" else self.provider_label
        print(f"{Fore.CYAN}[Block #{block.index}] {tag}")
        print(f"{Fore.WHITE}  Hash:   {content_hash[:32]}...")
        print(f"{Fore.WHITE}  Nonce:  {block.nonce} | Difficulty: {self.blockchain.difficulty}")

    def _print_status(self):
        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"  Provider : {self.provider_label}")
        print(f"  Model    : {self.model_config['id']}")
        print(f"  Session  : {self.session_id}")
        print(f"  Blocks   : {len(self.blockchain.chain)}")
        print(f"  Valid    : {self.blockchain.is_chain_valid()}")
        print(f"  Pending  : {len(self.blockchain.pending_data)}")
        print(f"{Fore.CYAN}{'='*50}")

    def _print_chain(self):
        print(f"\n{Fore.CYAN}{'='*50} CHAIN")
        for block in self.blockchain.chain:
            print(f"\n{Fore.GREEN}Block {block.index}")
            try:
                items = json.loads(block.data)
                for raw in items:
                    entry = json.loads(raw)
                    snippet = entry.get("content", "")[:80]
                    print(f"  [{entry.get('role','?')}] {snippet}")
            except Exception:
                print(f"  {block.data[:80]}")
            print(f"  hash: {block.hash[:32]}...")

    # ------------------------------------------------------------------
    # Command handling
    # ------------------------------------------------------------------

    def _handle_command(self, cmd: str):
        parts = cmd.strip().split(maxsplit=1)
        keyword = parts[0].lower()

        if keyword == "/status":
            self._print_status()
        elif keyword == "/chain":
            self._print_chain()
        elif keyword == "/clear":
            self.conversation_context.clear()
            print(f"{Fore.GREEN}Conversation context cleared.")
        elif keyword == "/save":
            if len(parts) < 2:
                print("Usage: /save <filename>")
                return
            try:
                self.blockchain.save_to_file(parts[1])
                print(f"{Fore.GREEN}Saved to {parts[1]}")
            except Exception as e:
                print(f"{Fore.RED}Save failed: {e}")
        elif keyword == "/load":
            if len(parts) < 2:
                print("Usage: /load <filename>")
                return
            try:
                self.blockchain = Blockchain.load_from_file(parts[1])
                print(f"{Fore.GREEN}Loaded from {parts[1]}")
            except Exception as e:
                print(f"{Fore.RED}Load failed: {e}")
        elif keyword in ("/quit", "/exit"):
            print(f"{Fore.GREEN}Goodbye!")
            sys.exit(0)
        else:
            print(f"Unknown command: {keyword}")
            print("Commands: /status, /chain, /save <file>, /load <file>, /clear, /quit")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        """Start the interactive session."""
        print(f"{Fore.CYAN}ChainRight LLM CLI")
        print(f"{Fore.CYAN}{'='*50}")
        print(f"  Provider : {Fore.GREEN}{self.provider_label}")
        print(f"  Model    : {Fore.GREEN}{self.model_config['id']}")
        print(f"  Session  : {Fore.WHITE}{self.session_id}")
        print(f"{Fore.CYAN}{'='*50}")
        print(f"{Fore.WHITE}Commands: /status  /chain  /save <f>  /load <f>  /clear  /quit\n")

        while True:
            try:
                user_input = input(f"{Fore.BLUE}You: ").strip()
                if not user_input:
                    continue

                if user_input.startswith("/"):
                    self._handle_command(user_input)
                    continue

                # Mine user input
                user_block = self._mine(user_input, "user")
                self._print_block(user_block, user_input, "user")

                # Call the LLM
                print(f"{Fore.YELLOW}  → {self.provider_label}...")
                start = time.time()
                response = self._call_llm(user_input)
                elapsed = time.time() - start

                # Mine LLM response
                llm_block = self._mine(response, "assistant")
                self._print_block(llm_block, response, "assistant")
                print(f"{Fore.WHITE}  Latency: {elapsed*1000:.0f}ms")

                # Display response
                print(f"\n{Fore.GREEN}{self.provider_label}: {response}\n")

                # Update context
                self.conversation_context.append({"user": user_input, "llm": response})

            except KeyboardInterrupt:
                print(f"\n{Fore.GREEN}Goodbye!")
                break
            except Exception as e:
                print(f"{Fore.RED}Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="ChainRight LLM CLI — blockchain-hashed conversations with any LLM"
    )
    parser.add_argument(
        "--provider",
        default=os.getenv("CHAINRIGHT_PROVIDER", "anthropic"),
        help="Provider name from providers.json (default: anthropic)",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("CHAINRIGHT_MODEL"),
        help="Model ID (default: first model for the provider)",
    )
    parser.add_argument(
        "--difficulty",
        type=int,
        default=2,
        help="Proof-of-work mining difficulty (default: 2)",
    )
    parser.add_argument(
        "--config",
        default=_DEFAULT_CONFIG,
        help="Path to providers.json",
    )
    args = parser.parse_args()

    cli = LLMCli(
        provider=args.provider,
        model=args.model,
        difficulty=args.difficulty,
        config_path=args.config,
    )
    cli.run()


if __name__ == "__main__":
    main()
