# Getting Started

## Installation

```bash
pip install chainright
```

Or install from source:

```bash
git clone https://github.com/davidatoms/ChainRight
cd ChainRight
pip install -e .
```

## Quick Start

```python
from chainright import Blockchain, GlobalConversationBlockchain

# Create a simple blockchain
bc = Blockchain()
bc.add_block("Hello, ChainRight!")
print(bc.is_valid())  # True

# Start a conversation blockchain
conv = GlobalConversationBlockchain(user_id="alice")
conv.add_conversation_block(
    prompt="What is a blockchain?",
    response="A blockchain is an immutable, distributed ledger..."
)
```

## CLI Tools

After installation, four commands are available:

| Command | Description |
|---------|-------------|
| `chainright-cli` | Interactive Claude CLI with blockchain hashing |
| `chainright-demo` | Global conversation blockchain demo |
| `chainright-train` | Personal AI trainer |
| `chainright-multi` | Multi-provider LLM CLI |

## Configuration

Copy `.env.example` to `.env` and add your API keys:

```bash
ANTHROPIC_API_KEY=your_key_here
```

See the [Guides](guides/claude-cli) for provider-specific setup.
