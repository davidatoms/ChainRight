# ChainRight - Global Conversation Blockchain

A decentralized platform for creating immutable, attributed conversations with AI that can be used for personal AI training and global knowledge sharing.

## Vision

ChainRight creates a **global conversation blockchain** where:
- Every conversation is permanently recorded and attributed
- Users own their data and can train personal AI models
- Companies can access shared training datasets
- Knowledge is distilled and preserved immutably

## Features

### **Global Conversation Blockchain**
- Immutable record of all human-AI conversations
- Cryptographic attribution and ownership verification
- Searchable conversation history
- Duplicate-tolerant data storage

### **Personal AI Training**
- Extract your conversations for personal AI training
- Generate training datasets in multiple formats
- Track your learning progress and patterns
- Create personalized AI models from your data

### **AI Training Dataset Generation**
- Export conversations for model training
- Multiple formats: OpenAI, JSONL, CSV, Knowledge Base
- Global dataset for shared AI development
- Reduce training duplication across companies

### **Privacy & Security**
- User-controlled data ownership
- Cryptographic verification of message authenticity
- Private API key management
- Secure blockchain validation

## Quick Start

### 1. Setup Environment

```bash
# Clone the repository
git clone <your-repo-url>
cd ChainRightv1

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file in the project root:
```bash
CLAUDE_API_KEY=sk-ant-your-api-key-here
```

Get your API key from [Anthropic Console](https://console.anthropic.com/)

### 3. Run the Global Conversation System

```bash
# Start the global conversation blockchain
python global_conversation_blockchain.py

# Commands available:
# /stats - Show blockchain statistics
# /verify <message> - Verify message ownership
# /search <term> - Search message content
# /my-conversations - Show your conversations
# /save - Save blockchain
```

### 4. Generate Personal AI Training Data

```bash
# Train your own AI from your conversations
python personal_ai_trainer.py

# Commands available:
# /load <user_id> - Load your conversation data
# /stats - Show your personal statistics
# /generate - Generate training datasets
# /train - Prepare for model training
```

### 5. Export AI Training Datasets

```bash
# Export global datasets for AI training
python ai_training_dataset.py

# Commands available:
# /load <blockchain_file> - Load blockchain file
# /stats - Show dataset statistics
# /export <format> <filename> - Export training data
# /formats - Show available export formats
```

## Available Scripts

### Core Blockchain
- `blockchain.py` - Core blockchain implementation
- `global_conversation_blockchain.py` - Global conversation system
- `claude_cli_real.py` - Real Claude API integration
- `claude_cli_enhanced.py` - Enhanced CLI with colors and model selection

### Personal AI Training
- `personal_ai_trainer.py` - Personal AI training system
- `ai_training_dataset.py` - Global dataset export

### Demos and Examples
- `demo_claude_cli.py` - Automated demo
- `test_claude_api.py` - API connection test
- `setup_claude_api.sh` - Setup script

## Data Formats

### Conversation Structure
```json
{
  "user_id": "user_1734112345_12345",
  "message": "Hello Claude, how does blockchain work?",
  "message_type": "user_input",
  "session_id": "a1b2c3d4",
  "timestamp": "2025-08-13T15:30:00.123456",
  "message_hash": "abc123...",
  "user_hash": "def456...",
  "metadata": {}
}
```

### Training Dataset Formats
- **OpenAI**: Fine-tuning format for GPT models
- **JSONL**: Standard format for local models
- **CSV**: Tabular data for analysis
- **Knowledge Base**: Structured Q&A for RAG systems

## Use Cases

### For Individuals
- **Personal Knowledge Base**: Build your own AI from your conversations
- **Learning Tracking**: Monitor your learning progress over time
- **Knowledge Distillation**: Extract insights from your interactions
- **Personal AI Models**: Train models that understand your style

### For Companies
- **Shared Training Data**: Access global conversation datasets
- **Reduced Training Costs**: Eliminate duplicate data collection
- **Better AI Models**: Train on diverse, real conversations
- **Transparent Attribution**: Verify data sources and ownership

### For AI Development
- **Decentralized Training**: One dataset serves all developers
- **Quality Data**: Real conversations, not synthetic data
- **Continuous Improvement**: Dataset grows with usage
- **Efficient Training**: No need to retrain on same data

## Security Features

- **Immutable Records**: Once added, conversations cannot be altered
- **Cryptographic Verification**: SHA-256 hashing for integrity
- **User Attribution**: Clear ownership of all messages
- **Private API Keys**: Secure environment variable management
- **Blockchain Validation**: Proof-of-work ensures data integrity

## Privacy

- **User Control**: You own your conversation data
- **Selective Sharing**: Choose what to include in training datasets
- **Anonymization Options**: Remove personal identifiers if needed
- **Local Processing**: Process data locally before sharing

## Contributing

This is a private repository. For contributions:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

- **Codebase**: Licensed under the [Apache License, Version 2.0](LICENSE).
- **Conversation Datasets**: Licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

## Support

For issues and questions:
- Check the documentation in each script
- Review the example outputs
- Test with the demo scripts first

## Future Enhancements

- Web interface for blockchain visualization
- Real-time collaboration features
- Advanced model training pipelines
- Multi-language support
- Mobile application
- API endpoints for integration
- Advanced analytics and insights
- Federated learning support

---

**ChainRight**: Where conversations become knowledge, and knowledge becomes AI.
