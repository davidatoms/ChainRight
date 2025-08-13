# Claude CLI with Real API Integration

This version of the Claude CLI uses the **real Claude API** via curl commands to get actual responses from Claude, while still maintaining all the blockchain hashing functionality.

## Features

- **Real Claude API**: Uses actual Claude API calls instead of simulated responses
- **Conversation Context**: Maintains conversation history for context-aware responses
- **Blockchain Hashing**: Every real message and response is hashed and stored
- **API Key Management**: Secure API key handling with environment variables
- **Error Handling**: Robust error handling for API calls and network issues

## Quick Start

### 1. Get Your Claude API Key

1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Sign up or log in
3. Create a new API key
4. Copy the key (it starts with `sk-ant-`)

### 2. Set Up the Environment

**Option A: Use the setup script (recommended)**
```bash
./setup_claude_api.sh
```

**Option B: Manual setup**
```bash
# Set API key for current session
export CLAUDE_API_KEY='sk-ant-your-api-key-here'

# Or add to your shell profile permanently
echo 'export CLAUDE_API_KEY="sk-ant-your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### 3. Test the API

```bash
python3 test_claude_api.py
```

### 4. Run the Real CLI

```bash
python3 claude_cli_real.py
```

## How It Works

### API Integration
- Uses `curl` commands to call the Claude API
- Sends conversation context for better responses
- Handles API errors gracefully
- Supports conversation continuity

### Blockchain Storage
- Every user message is hashed and stored in a block
- Every Claude response is hashed and stored in a block
- Complete conversation history is preserved
- Immutable record of all interactions

### Conversation Context
- Maintains last 10 exchanges for context
- Claude can reference previous conversation
- Context is cleared with `/clear` command

## API Configuration

### Model Selection
Default model: `claude-3-5-sonnet-20241022`

You can change this in the code:
```python
cli = ClaudeCLIReal(difficulty=2, api_key=api_key, model="claude-3-haiku-20240307")
```

### Available Models
- `claude-3-5-sonnet-20241022` (default, most capable)
- `claude-3-5-haiku-20241022` (fastest, most affordable)
- `claude-3-opus-20240229` (most capable, most expensive)

### Token Limits
- Default max tokens: 1000 per response
- Adjustable in the `call_claude_api` method
- Unlimited tokens available with your account

## Commands

- `/status` - Show blockchain and API status
- `/chain` - Display full blockchain with conversation data
- `/save <filename>` - Save blockchain to JSON file
- `/load <filename>` - Load blockchain from JSON file
- `/clear` - Clear conversation context (Claude will forget previous conversation)
- `/quit` or `/exit` - Exit the program

## Example Session

```
Claude CLI with Blockchain Hashing - Real API Version
============================================================
Type your messages to interact with Claude.
Each message and response will be hashed and added to the blockchain.

You: Hello Claude, can you explain blockchain technology?

Processing your input...
============================================================
USER INPUT HASHING INFO:
============================================================
Text: Hello Claude, can you explain blockchain technology?
SHA-256 Hash: a1b2c3d4e5f6...
Hash Length: 64 characters
Block Index: 1
Block Hash: 00abc123...
Nonce: 42
Mining Difficulty: 2
Timestamp: 2025-08-13 15:30:00
============================================================

Calling Claude API...

============================================================
CLAUDE RESPONSE HASHING INFO:
============================================================
Text: Blockchain is a distributed ledger technology that...
SHA-256 Hash: f6e5d4c3b2a1...
Hash Length: 64 characters
Block Index: 2
Block Hash: 00def456...
Nonce: 123
Mining Difficulty: 2
Timestamp: 2025-08-13 15:30:05
============================================================

Claude: Blockchain is a distributed ledger technology that...
```

## Error Handling

The system handles various API errors:

- **No API Key**: Prompts for key or shows error
- **Network Timeout**: 30-second timeout with retry option
- **Invalid Response**: Graceful error display
- **Rate Limiting**: Automatic retry with backoff
- **Authentication Errors**: Clear error messages

## Security

- API key is stored in environment variables only
- No API key is saved to files
- All communication uses HTTPS
- Blockchain provides immutable audit trail

## Cost Considerations

With unlimited tokens, you can:
- Have long conversations without worrying about limits
- Use the most capable models (Claude 3.5 Sonnet)
- Generate detailed responses
- Maintain extensive conversation context

## Troubleshooting

### Common Issues

1. **"No API key configured"**
   - Set `CLAUDE_API_KEY` environment variable
   - Run `./setup_claude_api.sh`

2. **"API call timed out"**
   - Check internet connection
   - Try again (temporary network issue)

3. **"Invalid JSON response"**
   - Check API key validity
   - Verify account has credits/tokens

4. **"curl not found"**
   - Install curl: `brew install curl` (macOS) or `sudo apt install curl` (Ubuntu)

### Debug Mode

To see detailed API calls, modify the curl command in `claude_cli_real.py`:
```python
curl_command = [
    "curl", "-v", "-X", "POST", "https://api.anthropic.com/v1/messages",
    # ... rest of command
]
```

## Files

- `claude_cli_real.py` - Main CLI with real API integration
- `test_claude_api.py` - API connection test
- `setup_claude_api.sh` - Automated setup script
- `blockchain.py` - Core blockchain implementation
- `README_Real_API.md` - This documentation

## Next Steps

1. Run the setup script: `./setup_claude_api.sh`
2. Test the API: `python3 test_claude_api.py`
3. Start chatting: `python3 claude_cli_real.py`
4. Explore the blockchain: Use `/chain` and `/status` commands
5. Save conversations: Use `/save conversation.json`

Enjoy your unlimited token conversations with Claude, all securely hashed and stored on the blockchain!
