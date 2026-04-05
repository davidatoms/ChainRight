# Training Data Export

ChainRight's `PersonalAITrainer` and `AITrainingDataset` classes transform your conversation history into structured datasets you can use to fine-tune a custom AI model.

---

## Overview

Every conversation you have through ChainRight is stored in the global ledger. The training tools let you:

- Extract conversations attributed to a specific user
- Analyze your communication patterns
- Export data in formats accepted by OpenAI, Hugging Face, and other fine-tuning platforms

---

## `PersonalAITrainer` — your conversations only

`PersonalAITrainer` filters the global ledger to a single user's history and prepares it for training.

```python
from chainright import PersonalAITrainer

trainer = PersonalAITrainer(user_id="alice")
trainer.load_from_ledger("ledger.json")

# See what you have
stats = trainer.get_stats()
print(stats)
# {
#   'total_messages': 84,
#   'total_words': 12450,
#   'avg_message_length': 148,
#   'date_range': {'first': '2024-01-15', 'last': '2024-03-20'},
#   'estimated_dataset_size_mb': 0.9
# }
```

### Export as OpenAI fine-tuning JSONL

```python
trainer.export_openai_format("alice_finetune.jsonl")
```

Each line of the output file is one training example:

```json
{"messages": [
  {"role": "system", "content": "You are a helpful assistant."},
  {"role": "user", "content": "Explain hashing in simple terms."},
  {"role": "assistant", "content": "Hashing takes any input and produces a fixed-length fingerprint..."}
]}
```

This format is accepted directly by the OpenAI fine-tuning API and most Hugging Face trainers.

### Export other formats

```python
# Generic JSONL (one conversation pair per line)
trainer.export_jsonl("alice_data.jsonl")

# CSV (prompt, response, timestamp columns)
trainer.export_csv("alice_data.csv")

# Structured knowledge base
trainer.export_knowledge_base("alice_knowledge.json")
```

### Analyze communication patterns

```python
insights = trainer.get_insights()
# Returns:
# - Most common topics/keywords
# - Peak conversation hours
# - Average response length
# - Knowledge gaps (questions without detailed responses)
# - Learning progression over time
```

---

## `AITrainingDataset` — the full global ledger

`AITrainingDataset` works on the entire ledger across all users. Use this when you want to train on aggregate conversation data.

```python
from chainright import AITrainingDataset

dataset = AITrainingDataset()
dataset.load_from_ledger("ledger.json")

stats = dataset.get_stats()
# {
#   'total_conversations': 312,
#   'unique_users': 8,
#   'unique_sessions': 45,
#   'total_words': 89200
# }

# Export everything
dataset.export_openai_format("full_dataset.jsonl")

# Export for a single user only
dataset.export_openai_format("alice_only.jsonl", filter_user="alice")
```

---

## CLI workflow

```bash
chainright-train
```

```
> load ledger.json
Loaded 84 conversations for user 'alice'

> stats
Total messages:  84
Total words:     12,450
Date range:      2024-01-15 → 2024-03-20
Est. size:       0.9 MB

> insights
Top topics: blockchain (23), cryptography (18), AI training (15)
Peak hours: 9am–11am, 3pm–5pm

> export-openai
Exported 84 examples to alice_finetune.jsonl

> exit
```

---

## Fine-tuning workflow (OpenAI example)

Once you have your `.jsonl` file:

```bash
# Validate the file
openai tools fine_tunes.prepare_data -f alice_finetune.jsonl

# Upload and start training
openai api fine_tunes.create \
  -t alice_finetune.jsonl \
  -m gpt-3.5-turbo
```

---

## Notes on data quality

- Short exchanges (under 20 words) are included but may add noise. Filter them with `trainer.filter_min_length(20)` if needed.
- The ledger stores hashes alongside text. Exported datasets contain only the plain text — hashes are metadata and are not included in training examples.
- All timestamps are UTC.
