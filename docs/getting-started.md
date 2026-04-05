# Getting Started

ChainRight records AI conversations onto an immutable blockchain so every message has a permanent, verifiable author and timestamp. This guide gets you from install to your first mined block.

## Requirements

- Python 3.8 or higher
- An Anthropic API key (for Claude-backed CLI tools)

## Installation

```bash
pip install chainright
```

Install from source (latest development version):

```bash
git clone https://github.com/davidatoms/ChainRight
cd ChainRight
pip install -e .
```

## Set your API key

Create a `.env` file in your project root:

```
ANTHROPIC_API_KEY=sk-ant-...
```

ChainRight loads this automatically via `python-dotenv`.

---

## Core concept: the chain

Every message you send and every AI response you receive becomes a **Block**. Each block contains:

- The content (hashed with SHA-256)
- A timestamp
- A link to the previous block's hash
- A proof-of-work nonce

Changing any block breaks every block after it — that's what makes the record immutable.

---

## Your first blockchain (Python API)

```python
from chainright import Blockchain

bc = Blockchain()

# Mine some data into the chain
bc.add_block("First message: Hello, ChainRight!")
bc.add_block("Second message: This is now permanent.")

# Verify the chain is intact
print(bc.is_valid())  # True
print(f"Chain length: {len(bc.chain)} blocks")
```

---

## Record a conversation

```python
from chainright import GlobalConversationBlockchain

ledger = GlobalConversationBlockchain(user_id="alice")

ledger.add_conversation_block(
    prompt="What is proof-of-work?",
    response="Proof-of-work is a mechanism that requires computational effort..."
)

# Verify alice's message is in the chain
result = ledger.verify_message_ownership(
    user_id="alice",
    message="What is proof-of-work?"
)
print(result)  # {'verified': True, 'block_index': 1, ...}
```

---

## CLI tools

Four commands are installed automatically:

| Command | What it does |
|---------|-------------|
| `chainright-llm` | Chat with any LLM — provider and model are arguments |
| `chainright-cli` | Claude-only shortcut for `chainright-llm --provider anthropic` |
| `chainright-multi` | Interactive menu to pick provider and model, with `/model` mid-session |
| `chainright-demo` | Launches the global conversation blockchain with a full CLI |
| `chainright-train` | Extracts your conversation history and exports it as a training dataset |

### Quick start with the CLI

```bash
# any provider
chainright-llm --provider anthropic
chainright-llm --provider openai --model gpt-4o
```

Type any message and press Enter. ChainRight will:
1. Hash your input with SHA-256
2. Call the Claude API
3. Hash the response
4. Mine both into a new block
5. Print the block index and hash

Type `/help` for available commands, `/exit` to quit.

---

## Save and reload a chain

```python
from chainright import Blockchain

bc = Blockchain()
bc.add_block("Important data")
bc.save("my_chain.json")

# Later...
bc2 = Blockchain()
bc2.load("my_chain.json")
print(bc2.is_valid())  # True
```

---

## Next steps

- [Ownership Blockchain](guides/ownership) — attribute sentences to specific authors
- [Multi-Provider CLI](guides/claude-cli) — switch between AI providers mid-session
- [Export Training Data](guides/real-api) — turn your conversation history into a fine-tuning dataset
- [Research Tools](guides/research) — use blockchain snapshots for linguistic research
