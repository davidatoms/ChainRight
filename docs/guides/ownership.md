# Ownership Blockchain

The Ownership Blockchain records which author wrote which sentence, and when. It's designed for collaborative writing, research attribution, and any context where "who said what, and when" needs to be verifiable.

---

## How it works

Each **block** holds a collection of `OwnedSentence` objects. Every sentence carries:

- `author` — the person who wrote it
- `sentence` — the text content
- `timestamp` — when it was recorded (ISO 8601)
- `sentence_hash` — SHA-256 hash of the text

Blocks are mined with proof-of-work, so the record can't be backdated or altered without invalidating every block that follows.

---

## Basic usage

```python
from chainright import OwnershipBlockchain, OwnedSentence

bc = OwnershipBlockchain()

# Add sentences from different authors
bc.add_sentence("alice", "The mitochondria is the powerhouse of the cell.")
bc.add_sentence("bob",   "Cells contain many specialized organelles.")
bc.add_sentence("alice", "Energy production drives all cellular functions.")

# Mine the pending sentences into a block
bc.mine_pending_sentences()

print(f"Chain valid: {bc.is_valid()}")
print(f"Blocks mined: {len(bc.chain)}")
```

---

## Query ownership

```python
# All sentences by a specific author
alice_sentences = bc.get_sentences_by_author("alice")
for s in alice_sentences:
    print(s.sentence, "—", s.timestamp)

# All authors who have contributed
authors = bc.get_all_authors()
print(authors)  # ['alice', 'bob']

# Everything recorded on a specific date
from datetime import date
today = date.today().isoformat()
todays_sentences = bc.get_sentences_by_date(today)
```

---

## Ownership summary

```python
summary = bc.get_ownership_summary()
# Returns a dict: { author -> sentence_count }
# e.g. {'alice': 2, 'bob': 1}

for author, count in summary.items():
    print(f"{author}: {count} sentence(s)")
```

---

## Save and reload

```python
bc.save("ownership_record.json")

# Restore later
bc2 = OwnershipBlockchain()
bc2.load("ownership_record.json")
print(bc2.is_valid())  # True
```

---

## Interactive CLI

Run the interactive demo directly:

```bash
python -m chainright.ownership_blockchain
```

Available commands inside the CLI:

| Command | Description |
|---------|-------------|
| `add <author> <sentence>` | Record a sentence |
| `mine` | Mine all pending sentences into a block |
| `authors` | List all authors |
| `sentences <author>` | Show sentences for one author |
| `summary` | Show sentence counts per author |
| `verify` | Check chain integrity |
| `save <file>` | Save chain to file |
| `load <file>` | Load chain from file |
| `exit` | Quit |

---

## Use cases

**Academic attribution** — Record who contributed each sentence to a shared paper. The blockchain timestamp is tamper-evident proof of authorship order.

**Collaborative writing** — Track contributions in real-time across multiple writers without relying on a central authority.

**AI conversation records** — Attribute AI-generated and human-generated sentences separately in a shared document, so the origin of every line is permanently traceable.

---

## Data model reference

### `OwnedSentence`

| Field | Type | Description |
|-------|------|-------------|
| `author` | `str` | Author identifier |
| `sentence` | `str` | The text content |
| `timestamp` | `str` | ISO 8601 timestamp |
| `sentence_hash` | `str` | SHA-256 of the sentence |

### `OwnershipBlock`

| Field | Type | Description |
|-------|------|-------------|
| `index` | `int` | Position in the chain |
| `sentences` | `list[OwnedSentence]` | Sentences in this block |
| `timestamp` | `str` | When the block was mined |
| `previous_hash` | `str` | Hash of the prior block |
| `hash` | `str` | This block's hash |
| `nonce` | `int` | Proof-of-work nonce |
