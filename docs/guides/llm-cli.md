# LLM CLI Guide

ChainRight ships five CLI commands. `chainright-llm` is the recommended starting point — it works with any supported provider and accepts the LLM as an argument so you're not locked into one vendor.

---

## `chainright-llm` — provider-agnostic CLI

Every message you type and every LLM response is SHA-256 hashed and mined into a block before the next exchange begins. `chainright-llm` is identical in behavior to `chainright-cli` but the LLM is a parameter, not a hardcoded choice.

### Start a session

```bash
# Default: Anthropic / claude-3-5-sonnet-20241022
chainright-llm

# Specify a provider and model
chainright-llm --provider anthropic --model claude-3-opus-20240229
chainright-llm --provider google    --model gemini-1.5-pro
chainright-llm --provider openai    --model gpt-4o
chainright-llm --provider groq      --model llama-3.1-70b-versatile
```

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--provider` | `anthropic` | Provider name from `providers.json` |
| `--model` | First model for provider | Model ID |
| `--difficulty` | `2` | Proof-of-work mining difficulty |
| `--config` | `config/providers.json` | Path to provider config |

You can also set defaults via environment variables to avoid typing them every time:

```bash
export CHAINRIGHT_PROVIDER=openai
export CHAINRIGHT_MODEL=gpt-4o
chainright-llm   # picks up the env vars
```

### What happens per exchange

1. Your input is hashed: `sha256(your_message)` → stored in block metadata
2. The message is sent to the chosen LLM with full conversation context (last 10 messages)
3. The LLM response is hashed: `sha256(response)`
4. Both are mined into new blocks with proof-of-work
5. Block index, hash, nonce, and latency are printed

### In-session commands

| Command | Description |
|---------|-------------|
| `/status` | Provider, model, session ID, chain length, validity |
| `/chain` | Print every block with content snippets |
| `/save <file>` | Save the chain to a JSON file |
| `/load <file>` | Load a previously saved chain |
| `/clear` | Clear the conversation context (chain is preserved) |
| `/quit` | End the session |

### Example session

```
ChainRight LLM CLI
==================================================
  Provider : Anthropic
  Model    : claude-3-5-sonnet-20241022
  Session  : a3f7c291
==================================================

You: What is proof-of-work?

[Block #1] You
  Hash:   8d3f9a2b1c4e5f6a7b8c9d0e1f2a3b4c...
  Nonce:  87 | Difficulty: 2
  → Anthropic...
[Block #2] Anthropic
  Hash:   c741e05f2d3a4b5c6e7f8a9b0c1d2e3f...
  Nonce:  142 | Difficulty: 2
  Latency: 380ms

Anthropic: Proof-of-work is a consensus mechanism that requires
nodes to expend computational effort to add a new block...
```

---

## Supported providers

| `--provider` value | Company | Required env var |
|-------------------|---------|-----------------|
| `anthropic` | Anthropic | `ANTHROPIC_API_KEY` |
| `google` | Google | `GOOGLE_API_KEY` |
| `openai` | OpenAI | `OPENAI_API_KEY` |
| `groq` | Groq | `GROQ_API_KEY` |
| `mistral` | Mistral AI | `MISTRAL_API_KEY` |
| `deepseek` | DeepSeek | `DEEPSEEK_API_KEY` |

Provider details and model lists live in `config/providers.json`. Add any OpenAI-compatible endpoint there and it will work immediately.

---

## `chainright-cli` — Claude-only shortcut

`chainright-cli` is a lightweight alias for `chainright-llm --provider anthropic`. Use it if you only ever use Claude and want a shorter command. All behavior and in-session commands are the same.

```bash
chainright-cli
```

---

## `chainright-multi` — interactive provider selector

`chainright-multi` presents a numbered menu at startup to pick provider and model interactively, then drops you into the same chat loop. Use this when you want to compare providers in the same session with the `/model` command.

```bash
chainright-multi
```

Additional in-session command unique to `chainright-multi`:

| Command | Description |
|---------|-------------|
| `/model` | Re-open the provider/model selector mid-session |

---

## `chainright-demo` — shared global ledger

A full-featured CLI for the shared global ledger. Multiple users can point at the same ledger file, and every message is permanently attributed to its author.

```bash
chainright-demo

# Share a ledger across users
CHAINRIGHT_LEDGER=/shared/drive/ledger.json chainright-demo
```

Commands: `/stats`, `/verify`, `/search <keyword>`, `/my-conversations`, `/save`, `/exit`

---

## `chainright-train` — export conversation history

Extracts your messages from the global ledger and exports them as a structured training dataset.

```bash
chainright-train
```

See the [Training Data Export](real-api) guide for full details.

---

## Environment variables

| Variable | Used by | Description |
|----------|---------|-------------|
| `CHAINRIGHT_PROVIDER` | `chainright-llm` | Default provider |
| `CHAINRIGHT_MODEL` | `chainright-llm` | Default model ID |
| `CHAINRIGHT_LEDGER` | `chainright-demo`, `chainright-train` | Path to shared ledger file |
| `ANTHROPIC_API_KEY` | `chainright-cli`, `chainright-llm` | Anthropic API key |
| `OPENAI_API_KEY` | `chainright-llm`, `chainright-multi` | OpenAI API key |
| `GOOGLE_API_KEY` | `chainright-llm`, `chainright-multi` | Google API key |
| `GROQ_API_KEY` | `chainright-llm`, `chainright-multi` | Groq API key |
| `MISTRAL_API_KEY` | `chainright-llm`, `chainright-multi` | Mistral API key |
| `DEEPSEEK_API_KEY` | `chainright-llm`, `chainright-multi` | DeepSeek API key |
