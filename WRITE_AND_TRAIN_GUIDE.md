# Write & Train CLI System

## Overview

The ChainRight Write & Train system provides a complete pipeline for capturing writing, calculating cognitive effort (PoE), and training ML models in real-time.

### Architecture

```
┌─────────────────┐
│ User Writes     │
│ (Interactive)   │
└────────┬────────┘
         ↓
┌──────────────────────────┐
│ write.py (CLI Commands)  │
│  - write start           │
│  - write history         │
│  - write search          │
│  - write publish         │
└────────┬─────────────────┘
         ↓
┌──────────────────────────────────┐
│ write_and_train.py (Orchestrator)│
│  - WriteCaptureCLI               │
│  - TrainingOrchestrator          │
│  - Feature extraction            │
│  - PoE calculation               │
└────────┬───────────────────────┬─┘
         ↓                       ↓
    ┌────────────┐         ┌─────────────┐
    │ Local DB   │         │ Blockchain  │
    │ (SQLite)   │         │ (JSON)      │
    └────────────┘         └─────────────┘
         ↓
┌──────────────────────────┐
│ train.py (CLI Commands)  │
│  - train latest          │
│  - train all             │
│  - train session         │
│  - train status          │
│  - train evaluate        │
└──────────────────────────┘
```

---

## Three Modules

### 1. **write_and_train.py** (Core Logic)

Contains the orchestration classes:

#### `WriteCaptureCLI`
- Real-time writing capture
- Feature extraction from text
- PoE calculation
- Mock embeddings (ready for Monolith)
- Session recording to blockchain

**Key methods:**
```python
session = WriteCaptureCLI(title="My session", user_id="alice")
session.start_session()

# In loop:
metadata = session.capture_paragraph("I'm debugging...")

# When done:
block = session.end_session()  # Records to blockchain
```

#### `TrainingOrchestrator`
- Manages training pipeline
- Coordinates feature extraction
- Prepares data for Monolith
- Tracks training metrics

**Key methods:**
```python
trainer = TrainingOrchestrator()
results = trainer.train_session(session_data)
summary = trainer.get_training_summary()
```

---

### 2. **write.py** (Writing Commands)

Interactive CLI for capturing and managing writing sessions.

#### Commands:

**`chainright write start [OPTIONS]`**
```bash
# Start an interactive writing session
chainright write start --title "Debugging async"
chainright write start -t "My thoughts"
```
- Prompts for input line-by-line
- Each line = paragraph, captured in real-time
- Shows PoE score for each paragraph
- Ctrl+D to finish
- Automatically mines block and shows recommendations

**`chainright write history [OPTIONS]`**
```bash
# View past writing sessions
chainright write history
chainright write history --limit 20
chainright write history --filter "async"
chainright write history --sort poe
```
- Lists all your writing sessions
- Filter by keyword or date
- Sort by: time, PoE, or length

**`chainright write search <QUERY> [OPTIONS]`**
```bash
# Search your writings
chainright write search "race condition"
chainright write search "async" --min-poe 4.0
```
- Full-text search across your sessions
- Optional PoE threshold

**`chainright write recommend`**
```bash
# Get knowledge recommendations based on your writing style
chainright write recommend
```
- Analyzes your writing patterns
- Suggests relevant knowledge assets
- Shows relevance and PoE scores

**`chainright write analyze`**
```bash
# Analyze your writing patterns and interests
chainright write analyze
```
- Total sessions and characters
- Average PoE per session
- Detected interests and topics
- Growth areas

**`chainright write publish <SESSION_TITLE>`**
```bash
# Publish a local session to the blockchain
chainright write publish "Debugging async"
```
- Takes local session and records to mainchain
- Creates permanent timestamped record
- Makes it available for marketplace

---

### 3. **train.py** (Training Commands)

ML training on captured sessions.

#### Commands:

**`chainright train latest [OPTIONS]`**
```bash
# Train on your most recent writing session
chainright train latest
chainright train latest --verbose
```
- Trains on newest session
- Shows paragraphs trained, avg PoE
- Stores training run results

**`chainright train all [OPTIONS]`**
```bash
# Train on all available sessions
chainright train all
chainright train all --limit 10
chainright train all --user alice@example.com
```
- Batch training on multiple sessions
- Optional user filter
- Progress bar
- Final summary with metrics

**`chainright train session <SESSION_ID> [OPTIONS]`**
```bash
# Train on specific session by ID
chainright train session abc123def456
chainright train session abc123def456 --verbose
```
- Train on exact session
- Verbose output for debugging

**`chainright train status`**
```bash
# View training status and statistics
chainright train status
```
- Total training runs
- Paragraphs trained
- Average PoE across runs
- Number of trained users

**`chainright train evaluate [OPTIONS]`**
```bash
# Evaluate model performance
chainright train evaluate
chainright train evaluate --metric convergence
```
Available metrics:
- `accuracy`: Recommendation accuracy, ranking correlation
- `convergence`: Training iterations, loss, convergence speed
- `user_interest`: Interest stability, drift, top topics

**`chainright train user-model [OPTIONS]`**
```bash
# Get or export user's learned model embedding
chainright train user-model --user alice@example.com
chainright train user-model --user alice@example.com --output model.json
```
- Show user embedding stats
- Optional export to JSON

---

## Data Flow & Storage

### Local Filesystem

```
~/.chainright/
├── local_ledger.json          # Local blockchain
├── sessions.db                # Session metadata (SQLite)
│   └─ Schema:
│       - session_id (PK)
│       - title
│       - user_id
│       - start_time, end_time
│       - total_chars, total_poe
│       - data (JSON blob)
└── training.db                # Training results (SQLite)
    ├─ training_runs
    │  ├── run_id (PK)
    │  ├── session_id
    │  ├── timestamp
    │  ├── paragraphs_trained
    │  ├── avg_poe
    │  └── status
    └─ user_models
       ├── user_id (PK)
       ├── updated_at
       ├── embedding (binary)
       └── model_version
```

### What Gets Recorded Where

| Data | Where | Purpose |
|------|-------|---------|
| Full text of sessions | `sessions.db` | Quick retrieval, search |
| Paragraph metadata | `sessions.db` | PoE, features, timestamps |
| PoE scores | `sessions.db` + blockchain | Effort tracking, ranking |
| User embeddings | `training.db` + blockchain | Personalization, recommendations |
| Training runs | `training.db` | Audit trail, performance tracking |
| Full content + signatures | Local blockchain | Immutable record, ownership proof |

---

## Example Workflow

### Alice's Day

```bash
# Morning: Debug async code
$ chainright write start --title "Fixing async timeouts"
📝 Writing Session: Fixing async timeouts
Session ID: abc123...

> I'm seeing connection pool exhaustion
  ✓ Captured (36 words, PoE: 2.1)

> The issue is we're not awaiting properly
  ✓ Captured (32 words, PoE: 2.8)

> Let me trace the call stack...
  ✓ Captured (28 words, PoE: 3.5)

✓ Session Complete!
  Block: def456...
  Total PoE: 8.4
  
💡 Recommendations:
  1. "Connection Pool Optimization" (relevance: 0.92)
  2. "Async Debugging Patterns" (relevance: 0.88)

# Later: Train the model
$ chainright train latest
🤖 Training on session: Fixing async timeouts
  ✓ Trained on 3 paragraphs
  ✓ Average PoE: 2.8
✅ Training complete!

# Review history
$ chainright write history --sort poe
📚 Writing History (7 sessions):

  1. Fixing async timeouts
     Date: 2026-05-02 14:30
     Duration: 45s | PoE: 8.4 | Chars: 2847
  
  2. Database indexing strategy
     Date: 2026-05-02 10:15
     Duration: 82s | PoE: 7.1 | Chars: 3245

# Search something
$ chainright write search "async" --min-poe 4.0
🔍 Found 3 session(s) matching 'async':
  • Fixing async timeouts (PoE: 8.4)
  • Async patterns for APIs (PoE: 6.2)
  • Advanced coroutines (PoE: 5.8)

# Get recommendations
$ chainright write recommend
💡 Recommendations based on your writing:
  Your writing profile:
    • Sessions: 7
    • Avg PoE: 6.1
    • Topics: Async, Performance, Architecture
  
  📚 Suggested knowledge assets:
    1. Advanced Async Patterns (relevance: 92%, PoE: 6.8)
    2. Performance Optimization (relevance: 85%, PoE: 6.1)

# Publish a session to blockchain
$ chainright write publish "Fixing async timeouts"
📤 Publishing session to blockchain...
✅ Published!
  Block: ghi789...

# Check training status
$ chainright train status
📊 Training Status:
  Training runs: 7
  Total paragraphs trained: 47
  Average PoE: 5.9
  User models: 1
```

---

## Integration Points

### Monolith Integration (Future)

Currently uses mock embeddings. When Monolith is integrated:

```python
# In write_and_train.py:
from monolith import MonolithModel

class WriteCaptureCLI:
    def _create_mock_embedding(self, text: str):
        # Replace with:
        return self.monolith_model.embed_text(text)
```

### Blockchain Integration

Full sessions can be published to mainchain:

```bash
$ chainright write publish "My session"
# Records to blockchain with:
#  - Title
#  - Full content
#  - PoE score
#  - Timestamp
#  - User signature (when wallet integrated)
```

### Marketplace Integration (Future)

Published sessions can be:
- Searched and ranked by PoE + relevance
- Bought/sold on marketplace
- Attributed to authors with royalty splits

---

## CLI Entry Point

The main CLI entry point is in `cli/main.py`:

```python
from chainright.cli.main import cli

if __name__ == "__main__":
    cli()
```

To use as a command-line tool, add to `pyproject.toml`:

```toml
[project.scripts]
chainright = "chainright.cli.main:cli"
```

Then:
```bash
pip install -e .
chainright write start "My title"
chainright train latest
```

---

## Testing

Test the modules:

```bash
# Test write capture
python -c "
from chainright.cli.write_and_train import WriteCaptureCLI
session = WriteCaptureCLI(title='Test', user_id='test_user')
session.start_session()
session.capture_paragraph('Testing the capture.')
block = session.end_session()
print(f'Block hash: {block.hash[:16]}...')
"

# Test training
python -c "
from chainright.cli.write_and_train import TrainingOrchestrator
trainer = TrainingOrchestrator()
print(f'Trainer initialized: {trainer}')
"

# Test CLI
python -m chainright.cli.main --help
python -m chainright.cli.main write --help
python -m chainright.cli.main train --help
```

---

## Next Steps

1. **Integrate Monolith**: Replace mock embeddings with real Monolith calls
2. **Add wallet support**: Sign sessions with user's private key
3. **Connect to marketplace**: Enable buying/selling of published sessions
4. **Add caching**: Cache embeddings for fast search
5. **GUI dashboard**: Web interface for visualization

---

## Architecture Benefits

✅ **Local-first**: All data stored locally until published  
✅ **Real-time feedback**: PoE calculated as you type  
✅ **Privacy**: Your writing stays local until you publish  
✅ **Composable**: CLI commands can be chained  
✅ **Extensible**: Easy to add new features  
✅ **Testable**: Each module independently testable
