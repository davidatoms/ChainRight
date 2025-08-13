# Sentence Ownership Blockchain System

## Overview

The Sentence Ownership Blockchain system extends the basic blockchain functionality to track **who wrote what** and **when**. This creates a cryptographically secure record of authorship and allows multiple people to contribute sentences to the same blockchain on the same day.

## Key Features

### 1. **Sentence Ownership Tracking**
- Each sentence is linked to its author
- Timestamped creation records
- Immutable authorship verification

### 2. **Multi-Author Support**
- Multiple people can contribute on the same day
- Each author's sentences are clearly identified
- Collaborative writing with individual attribution

### 3. **Block Mining with Ownership**
- Authors can "mine" blocks containing their sentences
- Multiple authors can contribute to the same block
- Proof-of-work ensures block integrity

## How It Works

### Sentence Structure

Each sentence in the blockchain contains:
```json
{
  "text": "Hello, this is my first sentence in the blockchain!",
  "author": "Alice",
  "timestamp": 1705276800.0
}
```

### Block Structure

Each block contains multiple sentences from different authors:
```json
{
  "index": 1,
  "sentences": [
    {
      "text": "Hello, this is my first sentence in the blockchain!",
      "author": "Alice",
      "timestamp": 1705276800.0
    },
    {
      "text": "Greetings from Bob! I'm also contributing today.",
      "author": "Bob", 
      "timestamp": 1705276801.0
    },
    {
      "text": "Hi everyone, Carol here. Happy to join!",
      "author": "Carol",
      "timestamp": 1705276802.0
    }
  ],
  "date_str": "2025-08-13",
  "previous_hash": "0000a1b2c3d4e5f6...",
  "hash": "0000f9e8d7c6b5a4..."
}
```

## Usage Examples

### Basic Usage

```python
from ownership_blockchain import OwnershipBlockchain

# Create blockchain
blockchain = OwnershipBlockchain(difficulty=2)
blockchain.create_genesis_block("2025-08-13")

# Multiple authors add sentences
blockchain.add_sentence("Hello, this is my first sentence!", "Alice")
blockchain.add_sentence("Greetings from Bob!", "Bob")
blockchain.add_sentence("Hi everyone, Carol here!", "Carol")

# Mine the block with all sentences
new_block = blockchain.mine_pending_sentences("2025-08-13")

# Check who contributed to this block
print(f"Authors in block: {new_block.get_authors()}")
# Output: ['Alice', 'Bob', 'Carol']
```

### Querying by Author

```python
# Get all sentences by a specific author
alice_sentences = blockchain.get_sentences_by_author("Alice")
for sentence in alice_sentences:
    print(f"[{sentence.author}] {sentence.text}")

# Get all authors who have contributed
all_authors = blockchain.get_all_authors()
print(f"All authors: {all_authors}")
```

### Querying by Date

```python
# Get all sentences from a specific date
date_sentences = blockchain.get_sentences_by_date("2025-08-13")
for sentence in date_sentences:
    print(f"[{sentence.author}] {sentence.text}")

# Get all authors who contributed on a specific date
date_authors = blockchain.get_authors_by_date("2025-08-13")
print(f"Authors on 2025-08-13: {date_authors}")
```

## Research Applications

### 1. **Collaborative Writing Research**
- Track individual contributions in group writing projects
- Analyze writing patterns across multiple authors
- Study collaborative creativity and authorship dynamics

### 2. **Digital Humanities**
- Preserve multi-author texts with cryptographic verification
- Create immutable records of collaborative literary works
- Study authorship attribution and verification

### 3. **Educational Technology**
- Track student contributions in collaborative assignments
- Provide verifiable proof of individual work
- Enable peer review with immutable records

### 4. **Content Creation Platforms**
- Verify authorship of user-generated content
- Create transparent attribution systems
- Enable fair compensation based on contributions

## Advanced Features

### Ownership Summary

```python
# Get comprehensive ownership statistics
summary = blockchain.get_ownership_summary()

print(f"Total blocks: {summary['total_blocks']}")
print(f"Total sentences: {summary['total_sentences']}")
print(f"All authors: {summary['authors']}")

# Author statistics
for author, stats in summary['author_stats'].items():
    print(f"{author}: {stats['sentence_count']} sentences")
```

### Block Analysis

```python
# Analyze a specific block
block = blockchain.chain[1]  # Second block

print(f"Block {block.index} contains {len(block.sentences)} sentences")
print(f"Authors: {block.get_authors()}")

# Get sentences by author in this block
for author in block.get_authors():
    sentences = block.get_sentences_by_author(author)
    print(f"{author}: {len(sentences)} sentences")
```

## Use Cases

### 1. **Academic Collaboration**
Multiple researchers can contribute to a shared document:
- Each contribution is cryptographically verified
- Authorship is permanently recorded
- Collaboration timeline is preserved

### 2. **Creative Writing**
Authors can collaborate on stories or poems:
- Individual contributions are tracked
- Creative process is documented
- Authorship disputes are resolved through blockchain verification

### 3. **Educational Projects**
Students can work on group assignments:
- Individual contributions are verified
- Teachers can see who contributed what
- Plagiarism detection is enhanced

### 4. **Content Platforms**
Social media or blogging platforms can use this for:
- Verifying original content creators
- Tracking content evolution
- Ensuring fair attribution

## Technical Implementation

### Cryptographic Security

1. **Sentence Hashing**: Each sentence is included in the block hash
2. **Author Verification**: Author information is cryptographically signed
3. **Timestamp Integrity**: Creation timestamps are verified through the blockchain
4. **Tamper Detection**: Any modification breaks the chain validation

### Data Structure

```python
class OwnedSentence:
    def __init__(self, text: str, author: str, timestamp: float = None):
        self.text = text
        self.author = author
        self.timestamp = timestamp or time.time()

class OwnershipBlock:
    def __init__(self, index: int, sentences: List[OwnedSentence], date_str: str, previous_hash: str):
        self.index = index
        self.sentences = sentences
        self.date_str = date_str
        self.previous_hash = previous_hash
        # ... mining and hashing logic
```

## Example Scenarios

### Scenario 1: Multiple Authors on Same Day

**Date**: 2025-08-13

**Alice** writes:
- "Hello, this is my first sentence in the blockchain!"
- "I'm excited to be part of this project."

**Bob** writes:
- "Greetings from Bob! I'm also contributing today."
- "This ownership tracking feature is really useful."

**Carol** writes:
- "Hi everyone, Carol here. Happy to join!"
- "I think this will be great for collaborative writing."

**Result**: All sentences are mined into the same block, with clear authorship attribution.

### Scenario 2: Sequential Contributions

**Morning**: Alice and Bob contribute sentences → Block 1 mined
**Afternoon**: Carol and David contribute sentences → Block 2 mined
**Evening**: Alice contributes more sentences → Block 3 mined

**Result**: Multiple blocks on the same day, each with different author combinations.

## Benefits

### 1. **Transparency**
- Clear attribution for every sentence
- Verifiable authorship records
- Transparent collaboration history

### 2. **Security**
- Cryptographically secure authorship verification
- Immutable records prevent tampering
- Timestamped creation evidence

### 3. **Collaboration**
- Multiple authors can contribute simultaneously
- Individual contributions are preserved
- Collaborative works are documented

### 4. **Research Value**
- Rich data for authorship studies
- Collaboration pattern analysis
- Digital humanities research opportunities

## Limitations

1. **Author Identity**: The system doesn't verify real-world identity
2. **Pseudonymity**: Authors can use pseudonyms
3. **Content Moderation**: No built-in content filtering
4. **Scalability**: Large numbers of authors may impact performance

## Future Enhancements

### 1. **Identity Verification**
- Integration with digital identity systems
- Real-world identity verification
- Reputation systems

### 2. **Content Analysis**
- Sentiment analysis of contributions
- Writing style analysis
- Collaboration pattern detection

### 3. **Advanced Queries**
- Complex authorship queries
- Temporal analysis of contributions
- Cross-author relationship analysis

### 4. **Integration**
- API for external applications
- Web interface for easy access
- Mobile applications

## Conclusion

The Sentence Ownership Blockchain system provides a powerful foundation for tracking authorship in collaborative environments. By combining blockchain technology with ownership tracking, it creates immutable records of who wrote what and when, enabling new forms of collaborative writing, research, and content creation.

The system's cryptographic security ensures that authorship claims cannot be falsified, while its multi-author support enables rich collaborative experiences. This makes it valuable for academic research, creative writing, educational technology, and content creation platforms.

## Running the System

```bash
# Demo with multiple authors
python3 ownership_blockchain.py

# Interactive demo
python3 ownership_blockchain.py
# Then choose option 2 for interactive mode
```

## Files

- `ownership_blockchain.py` - Main implementation with ownership tracking
- `OWNERSHIP_README.md` - This documentation
- `ownership_blockchain_YYYY-MM-DD.json` - Example blockchain files
