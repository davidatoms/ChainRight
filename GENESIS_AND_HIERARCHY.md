# Hierarchical Knowledge Objects & Genesis Builder

## Overview

ChainRight now has a complete **object-oriented model** for knowledge organization:

```
Book (title, author, ISBN, year)
├── Chapter (number, title)
│   └── Section (number, title)
│       └── Paragraph (text, index)
│           └── Sentence (text, index)
│               └── Concept (text, embedding, importance)
```

Each level is a **first-class object** with its own identity, hash, and metadata.

---

## Architecture

### Level 0: Concept
**Atomic unit of knowledge** - a single coherent idea

```python
Concept(
    id="concept_001",
    text="An algorithm is a well-defined computational procedure",
    metalocation=Metalocation(...),
    embedding=[0.23, -0.45, 0.89, ...],      # 768-dim vector
    keywords=["algorithm", "procedure"],
    importance_score=0.95,
    citations_in_genesis=342                 # Referenced 342 times
)
```

### Level 1: Sentence
**Contains multiple concepts**

```python
sentence = Sentence(
    text="An algorithm is a well-defined computational procedure...",
    index=0,
    metalocation=Metalocation(...)  # Inherits from paragraph
)

sentence.concepts = [
    Concept(...),  # "algorithm"
    Concept(...),  # "procedure"
]
```

### Level 2: Paragraph
**Contains multiple sentences**

```python
paragraph = Paragraph(
    text="Full paragraph text...",
    index=2,
    metalocation_base=Metalocation(...)
)

for sentence_text in sentences:
    sentence = paragraph.add_sentence(sentence_text)
```

### Level 3: Section
**Contains multiple paragraphs**

```python
section = Section(
    title="1.1: The Role of Algorithms",
    number="1.1",
    metalocation_base=Metalocation(...)
)

for para_text in paragraphs:
    para = section.add_paragraph(para_text)
```

### Level 4: Chapter
**Contains multiple sections**

```python
chapter = Chapter(
    title="Foundations",
    number=1,
    metalocation_base=Metalocation(...)
)

section = chapter.add_section("1.1: The Role of Algorithms", "1.1")
```

### Level 5: Book
**Complete book with chapters**

```python
book = Book(
    title="Introduction to Algorithms",
    author="Cormen, Leiserson, Rivest, Stein",
    isbn="ISBN-9780262033848",
    year=2009,
    edition=3
)

chapter = book.add_chapter("Foundations", 1)
```

---

## Metalocation: Precise Source Tracking

Every concept has a **complete metalocation** that tracks its exact origin:

```python
Metalocation(
    source_type="book",
    source_id="ISBN-9780262033848",
    source_title="Introduction to Algorithms",
    source_author="Cormen, Leiserson, Rivest, Stein",
    source_year=2009,
    
    # Hierarchical path
    book_title="Introduction to Algorithms",
    chapter_number=1,
    chapter_title="Foundations",
    section_number="1.1",
    section_title="The Role of Algorithms",
    page_number=10,
    paragraph_number=2,
    sentence_number=1,
    
    # Character offsets
    start_char=145,
    end_char=198,
    start_line=0,
    end_line=0
)
```

**Readable path:**
```
Introduction to Algorithms / Ch 1: Foundations / 1.1: The Role of Algorithms / 
Page 10, Para 2, Sent 1
```

---

## Genesis Builder

Constructs the **Genesis Block** from pretraining corpus:

### Step 1: Load Sources
```python
builder = GenesisBuilder()

book_data = {
    "title": "Introduction to Algorithms",
    "author": "CLRS",
    "isbn": "ISBN-9780262033848",
    "year": 2009,
    "chapters": {
        "1": {
            "title": "Foundations",
            "sections": {
                "1.1": {
                    "title": "The Role of Algorithms",
                    "paragraphs": ["An algorithm is..."]
                }
            }
        }
    }
}

book = builder.add_book_from_dict(book_data)
```

### Step 2: Extract Concepts
```python
# Extract key phrases/concepts from all paragraphs
builder.extract_concepts(book.isbn)

# Results: Every phrase becomes a Concept with full provenance
```

### Step 3: Build Merkle Tree
```python
# Efficient verification of corpus integrity
merkle_root = builder.build_merkle_tree()
# Output: 0xabc123... (root hash)
```

### Step 4: Create Genesis Block
```python
genesis_block = builder.create_genesis_block()

# Contains:
# - All sources
# - All concepts
# - Merkle root
# - Complete statistics
# - Immutable hash
```

### Step 5: Save to Files
```python
files = builder.save_to_files()
# Output:
# - hierarchy.json      (full object graph)
# - concepts.json       (all concepts with metalocation)
# - sources.json        (bibliography)
# - statistics.json     (corpus stats)
```

---

## CLI: Genesis Commands

### Build Genesis
```bash
# Initialize from pretraining corpus
chainright genesis init --sources ~/library

# Output:
# ✅ Genesis Block created!
#   Block Hash: abc123def456...
#   Merkle Root: def456abc123...
#   
#   📊 Statistics:
#     Sources: 150
#     Concepts: 2,337,420
#     Books: 45
#     Chapters: 892
#     Sections: 12,456
#     Paragraphs: 847,392
#     Sentences: 3,247,821
```

### Show Contents
```bash
chainright genesis show
# Lists all books in genesis

chainright genesis show --source "CLRS"
# Shows only Algorithms book

chainright genesis show --limit 20
# First 20 books
```

### Search Concepts
```bash
chainright genesis search "sorting"
# Finds all concepts mentioning "sorting"

chainright genesis search "algorithm" --limit 20
# Top 20 matches for "algorithm"
```

### Generate Citations
```bash
chainright genesis cite concept_001
# Output (APA format):
# Cormen, T. H., et al. (2009). Introduction to Algorithms 
# (3rd ed., p. 10). MIT Press.

chainright genesis cite concept_001 --style MLA
# Same concept in MLA format

chainright genesis cite concept_001 --style BibTeX
# BibTeX format for LaTeX
```

### Check Text (Plagiarism Detection)
```bash
chainright genesis check "An algorithm is a procedure..."
# Output:
# ⚠️ PLAGIARISM DETECTED
#   Similarity: 95%
#   Source: Introduction to Algorithms (CLRS)

chainright genesis check "I invented a novel sorting method"
# Output:
# ✅ LIKELY NOVEL
#   Max similarity: 34% (below threshold)

chainright genesis check "Building on quicksort with parallel merge" --threshold 0.80
# Output:
# 📝 DERIVATION DETECTED
#   Similarity: 78%
#   Needs citation: "Quicksort is a comparison-based sorting algorithm..."
#   Source: CLRS Ch 7, p. 170
```

### View Statistics
```bash
chainright genesis status
# Shows corpus size and composition
```

---

## Knowledge Hierarchy: Navigation

Query the complete object graph:

```python
from chainright.knowledge_hierarchy import KnowledgeHierarchy

hierarchy = KnowledgeHierarchy()

# Get all concepts from a source
clrs_concepts = hierarchy.get_concepts_by_source("ISBN-9780262033848")

# Find concepts by keyword
sorting_concepts = hierarchy.get_concepts_by_keyword("sorting")

# Get path to a concept
path = hierarchy.get_path_to_concept("concept_123")
# Output: "Introduction to Algorithms / Ch 3: Sorting / 3.1: Quicksort / ..."

# Get statistics
stats = hierarchy.statistics()
# Output: {
#   "total_books": 150,
#   "total_concepts": 2337420,
#   "avg_concepts_per_book": 15582,
#   ...
# }
```

---

## How It Powers ChainRight

### 1. Writing with Genesis Context
```bash
$ chainright write start "New sorting algorithm"
> I created a parallel version of quicksort
  ✓ Captured (29 words, PoE: 3.2)
  
  📚 Genesis references detected:
    • "quicksort" → CLRS Ch 7, Page 170 (99% match)
    • "parallel" → GPUs paper Ch 5 (82% match)
  
  ⚠ Your concept is 92% similar to existing quicksort
    Novel portion: 8%
    PoE adjusted: 3.2 × 0.08 = 0.26 (low novelty)
```

### 2. Automatic Citations
```bash
$ chainright write publish "New sorting algorithm"
✓ Published!
  References auto-cited:
    [1] Cormen et al. (2009) - Introduction to Algorithms, Ch 7, p. 170
    [2] Kirk & Hwu (2012) - Programming Massively Parallel Processors
```

### 3. Plagiarism Protection
- Alice's work automatically compared against genesis
- Similarity score clearly shown
- Derivative vs. novel clearly indicated
- Citations auto-generated for derivative work

### 4. Copyright by Metalocation
- **Genesis concept:** "Quicksort was invented by Hoare (1962)"
  - Metalocation: CLRS ISBN, Ch 7, Page 170
  - Copyright: CLRS 2009, Hoare 1962 (provenance chain)

- **Alice's work:** "I implemented parallel quicksort"
  - References genesis "quicksort" concept
  - Adds novelty: "parallel" approach
  - PoE = novelty × effort
  - Auto-cites CLRS + Hoare

---

## Example: Complete Workflow

### Day 1: Build Genesis
```bash
# Admin builds genesis from 150 computer science books
chainright genesis init --sources ~/cs_library

# Result:
# - 2.3M concepts extracted
# - All with complete metalocation
# - Merkle tree built
# - Genesis block mined and immutable
```

### Day 2: Alice Writes
```bash
# Alice is debugging sorting
chainright write start "Optimizing quicksort"

# System shows:
# "Quicksort was invented by C.A.R. Hoare (1961)
#  See: CLRS Introduction to Algorithms, Ch 7.1, p. 170"

# Alice writes about her optimization
# PoE calculated as: (novelty vs. quicksort) × (cognitive effort)
# PoE = 3.8 (moderate effort, moderately novel)
```

### Day 3: Publish & Cite
```bash
# Alice publishes
chainright write publish "Optimizing quicksort"

# Block recorded with:
# - Full text of her work
# - PoE score: 3.8
# - Metalocation of referenced genesis concepts
# - Automatic citations to CLRS, Hoare papers
# - Hash proof of authorship
```

### Day 4: Bob Searches
```bash
# Bob searches for quicksort optimizations
chainright genesis search "quicksort optimization"

# Results show:
# 1. Alice's work (PoE: 3.8, relevance: 0.95)
# 2. CLRS Ch 7.3 "Quicksort Optimization Tips" (relevance: 0.92)
# 3. Bob Sedgewick's paper on cache-aware sorting (relevance: 0.88)

# Bob buys Alice's work for 2.5 CRIGHT tokens
# Alice gets paid, CLRS gets attribution royalty
```

---

## Data Files

After running `chainright genesis init`, you get:

```
.chainright/genesis/
├── hierarchy.json           # Complete object graph
├── concepts.json            # All concepts with metalocation
├── sources.json             # Bibliography
└── statistics.json          # Corpus statistics
```

Each file is immutable (unless explicitly rebuilt).

---

## Future Enhancements

1. **PDF/EPUB Parser**: Load real books and papers
2. **Monolith Integration**: Real embeddings instead of mock
3. **ArXiv Importer**: Automatic paper ingestion
4. **Wikipedia Ingestion**: Structured knowledge import
5. **Continuous Updates**: Genesis v2.0, v3.0 as knowledge grows
6. **Version Tracking**: Track genesis evolution over time
7. **Merkle Proofs**: Prove any concept is in genesis efficiently

---

## Benefits of Hierarchical Design

✅ **Precise Attribution**: Know exact source down to sentence  
✅ **Efficient Queries**: Navigate massive corpus quickly  
✅ **Plagiarism Detection**: Compare against 2.3M concepts  
✅ **Citation Generation**: Academic integrity automatic  
✅ **Merkle Proofs**: Efficient blockchain verification  
✅ **Modular Objects**: Each level independent and queryable  
✅ **Scalable**: Handle billions of concepts efficiently  
✅ **Immutable**: Once in genesis, never changes  
✅ **Provenance Preserved**: Full lineage from original source
