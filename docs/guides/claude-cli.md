# CLI Guide

ChainRight ships four CLI commands. This guide covers what each one does and how to use it effectively.

---

## `chainright-cli` — Claude with blockchain hashing

The primary interactive CLI. Every message you type and every Claude response is SHA-256 hashed and mined into a block before the next exchange begins.

### Start a session

```bash
chainright-cli
```

You'll see your session ID and the genesis block hash printed at startup. Type any message and press Enter to begin.

### What happens per exchange

1. Your input is hashed: `sha256(your_message)` → stored in block metadata
2. The message is sent to the Claude API with full conversation context (last 5 messages)
3. Claude's response is hashed: `sha256(response)`
4. Both hashes are mined into a new block with proof-of-work
5. Block index, hash, and mining time are printed

### In-session commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/stats` | Print chain length, valid status, unique users |
| `/verify` | Re-validate the entire chain |
| `/search <keyword>` | Search conversation history |
| `/my-conversations` | Show your messages only |
| `/save` | Save the ledger to disk |
| `/exit` | End the session |

### Example session

```
You: What is entropy in information theory?

[Block #3 mined] Hash: a3f7c2... | Nonce: 142 | Time: 0.4s

Claude: Entropy in information theory, introduced by Claude Shannon,
measures the average amount of information produced by a random source...

Your input hash:  8d3f9a2b...
Response hash:    c741e05f...
```

---

## `chainright-multi` — Multi-provider CLI

Same blockchain behavior as `chainright-cli`, but lets you select from multiple AI providers at startup.

### Supported providers

| Provider | Models available |
|----------|-----------------|
| Anthropic | claude-3-5-sonnet, claude-3-opus, claude-3-haiku |
| Google | gemini-1.5-pro, gemini-1.5-flash |
| OpenAI | gpt-4o, gpt-4-turbo, gpt-3.5-turbo |
| Groq | llama-3.1-70b, mixtral-8x7b |
| Mistral | mistral-large, mistral-medium |
| DeepSeek | deepseek-chat, deepseek-coder |

### Configuration

Provider settings live in `config/providers.json`. Set the corresponding API key in `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
OPENAI_API_KEY=sk-...
GROQ_API_KEY=...
MISTRAL_API_KEY=...
DEEPSEEK_API_KEY=...
```

### Start with a specific provider

```bash
chainright-multi
# → Prompts you to select a provider and model
```

All conversations are recorded to the same ledger regardless of which provider you use. The block metadata includes `provider` and `model` fields so you can tell which AI generated each response.

---

## `chainright-demo` — Global conversation blockchain CLI

A full-featured CLI for the shared global ledger. Multiple users can connect to the same ledger file, and every message is permanently attributed to its author.

### Start the demo

```bash
chainright-demo
```

### Commands

| Command | Description |
|---------|-------------|
| `/stats` | Chain length, unique users, total messages |
| `/verify` | Validate chain integrity |
| `/search <keyword>` | Full-text search across all blocks |
| `/my-conversations` | Filter to your user ID only |
| `/save` | Persist ledger to disk |
| `/exit` | Quit |

### Sharing a ledger between users

Point multiple users at the same `.json` ledger file by setting `CHAINRIGHT_LEDGER` in their environment:

```bash
CHAINRIGHT_LEDGER=/shared/drive/ledger.json chainright-demo
```

Each user sets their own `user_id` at startup. The chain records all contributions in order.

---

## `chainright-train` — Export your conversation history

Extracts your messages from the global ledger and exports them as a structured training dataset.

### Start the trainer

```bash
chainright-train
```

### Commands

| Command | Description |
|---------|-------------|
| `load <file>` | Load a ledger JSON file |
| `stats` | Show your message count, word count, date range |
| `export-openai` | Export as OpenAI fine-tuning JSONL |
| `export-jsonl` | Export as generic JSONL |
| `export-csv` | Export as CSV |
| `export-knowledge` | Export as a knowledge base JSON |
| `insights` | Show communication patterns and topic analysis |
| `exit` | Quit |

### Export formats

**OpenAI fine-tuning format** (`export-openai`):
```json
{"messages": [
  {"role": "user", "content": "What is proof-of-work?"},
  {"role": "assistant", "content": "Proof-of-work is..."}
]}
```

**Knowledge base format** (`export-knowledge`):
```json
{
  "user_id": "alice",
  "total_messages": 42,
  "conversations": [...],
  "topics": ["blockchain", "AI", "cryptography"]
}
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required for `chainright-cli` |
| `CHAINRIGHT_LEDGER` | `ledger.json` | Path to the shared ledger file |
| `CHAINRIGHT_USER_ID` | prompted | Your user identity in the chain |
