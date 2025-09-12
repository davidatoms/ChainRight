# Claude CLI with Blockchain Hashing

This project provides an interactive command line interface that demonstrates how conversations with Claude can be hashed and stored on a blockchain for immutability and transparency.

## Features

- **Real-time Hashing**: Every user input and Claude response is hashed using SHA-256
- **Blockchain Storage**: All conversation data is stored in a blockchain with proof-of-work mining
- **Interactive CLI**: Command-line interface for real-time conversation
- **Visual Hash Display**: See exactly how your messages and Claude's responses are being hashed
- **Blockchain Validation**: Verify the integrity of the conversation chain
- **Session Management**: Each conversation session gets a unique ID
- **Save/Load**: Persist conversations to JSON files

## How It Works

1. **User Input Hashing**: When you type a message, it's immediately hashed using SHA-256
2. **Block Creation**: The hashed message is added to a new block in the blockchain
3. **Proof of Work**: The block is mined with a configurable difficulty level
4. **Claude Response**: Claude's response is similarly hashed and added to the blockchain
5. **Chain Validation**: The entire conversation chain is validated for integrity

## Installation

Make sure you have Python 3.7+ installed and the required dependencies:

```bash
# The project uses only standard library modules
# No additional installation required
```

## Usage

### Interactive Mode

Run the interactive CLI:

```bash
python claude_cli.py
```

This will start an interactive session where you can:
- Type messages and see them hashed in real-time
- View Claude's responses and their hashes
- Use commands to manage the blockchain

### Demo Mode

Run the automated demo to see the system in action:

```bash
python demo_claude_cli.py
```

This demonstrates the full conversation flow with sample messages.

## CLI Commands

When in interactive mode, you can use these commands:

- `/status` - Show current blockchain status
- `/chain` - Display the full blockchain
- `/save <filename>` - Save the blockchain to a JSON file
- `/load <filename>` - Load a blockchain from a JSON file
- `/quit` or `/exit` - Exit the program

## Example Output

```
You: Hello Claude, how does blockchain hashing work?

============================================================
USER INPUT HASHING INFO:
============================================================
Text: Hello Claude, how does blockchain hashing work?
SHA-256 Hash: bca9d47471492f05989a6ec9e5bca4c0c88a2425905c1019b26e0f83d1d2643c
Hash Length: 64 characters
Block Index: 1
Block Hash: 002fbc548492eae7a6ab757b6891bc5c57bec85e483595b800b9f24104481ae2
Nonce: 383
Mining Difficulty: 2
Timestamp: 2025-08-13 14:58:01.335711
============================================================

Claude: Thank you for your input: 'Hello Claude, how does blockchain hashing work?'. The hash you see below proves this conversation is immutable.

============================================================
CLAUDE RESPONSE HASHING INFO:
============================================================
Text: Thank you for your input: 'Hello Claude, how does blockchain hashing work?'. The hash you see below proves this conversation is immutable.
SHA-256 Hash: 2010b4ac7587794e085a44f2071622d49319de245e49ebfe20b790c92d6e3ec2
Hash Length: 64 characters
Block Index: 2
Block Hash: 0081bf31628fd8b440fae76d378e83f895d3563129474f6e968199a33384f5e9
Nonce: 218
Mining Difficulty: 2
Timestamp: 2025-08-13 14:58:01.340858
============================================================
```

## Technical Details

### Hashing Algorithm
- Uses SHA-256 for all text hashing
- 64-character hexadecimal output
- Deterministic (same input always produces same hash)

### Blockchain Implementation
- Proof-of-work mining with configurable difficulty
- Each block contains conversation data, timestamp, and session ID
- Chain validation ensures integrity
- Genesis block starts the chain

### Data Structure
Each block contains:
```json
{
  "type": "user_input|claude_response",
  "content": "actual message content",
  "timestamp": "ISO format timestamp",
  "session_id": "unique session identifier"
}
```

## Files

- `claude_cli.py` - Main interactive CLI application
- `demo_claude_cli.py` - Automated demo script
- `blockchain.py` - Core blockchain implementation
- `README_Claude_CLI.md` - This documentation

## Security Features

- **Immutability**: Once added to the blockchain, conversation data cannot be altered
- **Integrity Verification**: Chain validation ensures no tampering
- **Cryptographic Hashing**: SHA-256 provides collision resistance
- **Proof of Work**: Mining difficulty prevents spam and ensures work was done

## Future Enhancements

- Integration with real Claude API
- Web interface for visualization
- Multiple conversation threads
- Advanced blockchain features (smart contracts, etc.)
- Export to different formats
- Real-time collaboration features

## Notes

- This is a demonstration system using simulated Claude responses
- In production, you would integrate with the actual Claude API
- Mining difficulty is set low (2) for demonstration purposes
- All data is stored locally in JSON format
