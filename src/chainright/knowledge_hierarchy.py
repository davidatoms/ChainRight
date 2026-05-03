#!/usr/bin/env python3
"""
Knowledge Hierarchy Objects

Creates an object model for the nested structure of knowledge:
    Book
    ├── Chapter
    │   └── Section
    │       └── Paragraph
    │           └── Sentence
    │               └── Concept

Each level is a first-class object with its own identity, hash, and embedding.
"""

import json
import uuid
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Metalocation:
    """Precise location reference within a document."""
    
    source_type: str        # "book", "paper", "website"
    source_id: str          # ISBN, DOI, URL
    source_title: str       # Full title
    source_author: str      # Author/authors
    source_year: int        # Publication year
    
    # Hierarchical navigation
    book_title: str
    chapter_number: int     # Ch 3
    chapter_title: str
    section_number: str     # 3.1
    section_title: str
    page_number: int
    paragraph_number: int
    sentence_number: int
    
    # Content offsets
    start_char: int
    end_char: int
    start_line: int
    end_line: int
    
    def __hash__(self) -> str:
        """Create unique hash for this metalocation."""
        loc_string = json.dumps(asdict(self), sort_keys=True)
        return hashlib.sha256(loc_string.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_path(self) -> str:
        """Convert to readable path."""
        return (f"{self.book_title} / "
                f"Ch {self.chapter_number}: {self.chapter_title} / "
                f"{self.section_number}: {self.section_title} / "
                f"Page {self.page_number}, Para {self.paragraph_number}, "
                f"Sent {self.sentence_number}")


@dataclass
class Concept:
    """
    Atomic unit of knowledge - a single coherent idea.
    
    "An algorithm is a well-defined computational procedure"
    """
    
    id: str
    text: str
    metalocation: Metalocation
    
    # Semantic properties
    embedding: List[float]          # 768-dim vector
    keywords: List[str]             # ["algorithm", "procedure"]
    key_entities: List[str]         # Named entities
    
    # Quality metrics
    importance_score: float         # 0.0-1.0
    clarity_score: float            # How well-written
    citations_in_genesis: int       # How many times referenced
    
    # Context
    preceding_sentence: Optional[str]
    following_sentence: Optional[str]
    section_context: Optional[str]  # Full section for context
    
    # Metadata
    created_at: float
    processed_at: float
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def hash(self) -> str:
        """Unique hash of this concept."""
        concept_data = {
            "text": self.text,
            "metalocation": self.metalocation.to_dict(),
            "keywords": sorted(self.keywords)
        }
        return hashlib.sha256(
            json.dumps(concept_data, sort_keys=True).encode()
        ).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "metalocation": self.metalocation.to_dict(),
            "embedding": self.embedding,
            "keywords": self.keywords,
            "key_entities": self.key_entities,
            "importance": self.importance_score,
            "citations": self.citations_in_genesis,
            "created_at": self.created_at
        }


class Sentence:
    """A sentence within a paragraph."""
    
    def __init__(self, text: str, index: int, metalocation: Metalocation):
        self.id = str(uuid.uuid4())
        self.text = text
        self.index = index
        self.metalocation = metalocation
        
        # Concepts extracted from this sentence
        self.concepts: List[Concept] = []
        
        # Embedding (will be calculated)
        self.embedding: Optional[List[float]] = None
        
        self.created_at = datetime.now().timestamp()
    
    def add_concept(self, concept: Concept) -> None:
        """Add a concept extracted from this sentence."""
        self.concepts.append(concept)
    
    def hash(self) -> str:
        """Hash of this sentence."""
        return hashlib.sha256(self.text.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "index": self.index,
            "metalocation": self.metalocation.to_dict(),
            "concepts": [c.to_dict() for c in self.concepts],
            "concept_count": len(self.concepts),
            "hash": self.hash()
        }


class Paragraph:
    """A paragraph containing multiple sentences."""
    
    def __init__(self, text: str, index: int, metalocation_base: Metalocation):
        self.id = str(uuid.uuid4())
        self.text = text
        self.index = index
        self.metalocation_base = metalocation_base
        
        # Child objects
        self.sentences: List[Sentence] = []
        self.concepts: List[Concept] = []
        
        self.embedding: Optional[List[float]] = None
        self.created_at = datetime.now().timestamp()
    
    def add_sentence(self, text: str) -> Sentence:
        """Add a sentence to this paragraph."""
        sentence_index = len(self.sentences)
        
        # Create metalocation for this sentence
        metalocation = Metalocation(
            **asdict(self.metalocation_base),
            sentence_number=sentence_index
        )
        
        sentence = Sentence(text, sentence_index, metalocation)
        self.sentences.append(sentence)
        return sentence
    
    def add_concept(self, concept: Concept) -> None:
        """Add a concept from this paragraph."""
        self.concepts.append(concept)
    
    def get_all_concepts(self) -> List[Concept]:
        """Get all concepts from all sentences."""
        all_concepts = list(self.concepts)
        for sentence in self.sentences:
            all_concepts.extend(sentence.concepts)
        return all_concepts
    
    def hash(self) -> str:
        """Merkle hash of paragraph."""
        sentence_hashes = [s.hash() for s in self.sentences]
        combined = "".join(sentence_hashes)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "index": self.index,
            "text": self.text,
            "metalocation": self.metalocation_base.to_dict(),
            "sentence_count": len(self.sentences),
            "concept_count": len(self.get_all_concepts()),
            "sentences": [s.to_dict() for s in self.sentences],
            "concepts": [c.to_dict() for c in self.concepts],
            "hash": self.hash()
        }


class Section:
    """A section containing multiple paragraphs."""
    
    def __init__(self, title: str, number: str, metalocation_base: Metalocation):
        self.id = str(uuid.uuid4())
        self.title = title
        self.number = number  # e.g., "3.1"
        self.metalocation_base = metalocation_base
        
        # Child objects
        self.paragraphs: List[Paragraph] = []
        self.concepts: List[Concept] = []
        
        self.embedding: Optional[List[float]] = None
        self.created_at = datetime.now().timestamp()
    
    def add_paragraph(self, text: str) -> Paragraph:
        """Add a paragraph to this section."""
        para_index = len(self.paragraphs)
        
        # Create metalocation for this paragraph by updating base with paragraph info
        base_dict = asdict(self.metalocation_base)
        base_dict.update({
            "paragraph_number": para_index
        })
        metalocation = Metalocation(**base_dict)
        
        paragraph = Paragraph(text, para_index, metalocation)
        self.paragraphs.append(paragraph)
        return paragraph
    
    def get_all_concepts(self) -> List[Concept]:
        """Get all concepts in this section."""
        all_concepts = list(self.concepts)
        for para in self.paragraphs:
            all_concepts.extend(para.get_all_concepts())
        return all_concepts
    
    def hash(self) -> str:
        """Merkle hash of section."""
        para_hashes = [p.hash() for p in self.paragraphs]
        combined = "".join(para_hashes)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "number": self.number,
            "paragraph_count": len(self.paragraphs),
            "concept_count": len(self.get_all_concepts()),
            "paragraphs": [p.to_dict() for p in self.paragraphs],
            "concepts": [c.to_dict() for c in self.concepts],
            "hash": self.hash()
        }


class Chapter:
    """A chapter containing multiple sections."""
    
    def __init__(self, title: str, number: int, metalocation_base: Metalocation):
        self.id = str(uuid.uuid4())
        self.title = title
        self.number = number
        self.metalocation_base = metalocation_base
        
        # Child objects
        self.sections: List[Section] = []
        self.concepts: List[Concept] = []
        
        self.embedding: Optional[List[float]] = None
        self.created_at = datetime.now().timestamp()
    
    def add_section(self, title: str, number: str) -> Section:
        """Add a section to this chapter."""
        # Create metalocation for this section by updating base with section info
        base_dict = asdict(self.metalocation_base)
        base_dict.update({
            "section_number": number,
            "section_title": title
        })
        metalocation = Metalocation(**base_dict)
        
        section = Section(title, number, metalocation)
        self.sections.append(section)
        return section
    
    def get_all_concepts(self) -> List[Concept]:
        """Get all concepts in this chapter."""
        all_concepts = list(self.concepts)
        for section in self.sections:
            all_concepts.extend(section.get_all_concepts())
        return all_concepts
    
    def hash(self) -> str:
        """Merkle hash of chapter."""
        section_hashes = [s.hash() for s in self.sections]
        combined = "".join(section_hashes)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "number": self.number,
            "section_count": len(self.sections),
            "concept_count": len(self.get_all_concepts()),
            "sections": [s.to_dict() for s in self.sections],
            "concepts": [c.to_dict() for c in self.concepts],
            "hash": self.hash()
        }


class Book:
    """A complete book with chapters, sections, paragraphs, sentences, and concepts."""
    
    def __init__(self, title: str, author: str, isbn: str, 
                 year: int, edition: int = 1, source_type: str = "book"):
        self.id = str(uuid.uuid4())
        self.title = title
        self.author = author
        self.isbn = isbn
        self.year = year
        self.edition = edition
        self.source_type = source_type
        
        # Child objects
        self.chapters: List[Chapter] = []
        self.concepts: List[Concept] = []
        
        # Statistics
        self.total_pages = 0
        self.total_chars = 0
        
        self.embedding: Optional[List[float]] = None
        self.created_at = datetime.now().timestamp()
    
    def add_chapter(self, title: str, number: int) -> Chapter:
        """Add a chapter to this book."""
        # Base metalocation for this chapter
        metalocation = Metalocation(
            source_type=self.source_type,
            source_id=self.isbn,
            source_title=self.title,
            source_author=self.author,
            source_year=self.year,
            book_title=self.title,
            chapter_number=number,
            chapter_title=title,
            section_number="0",
            section_title="",
            page_number=0,
            paragraph_number=0,
            sentence_number=0,
            start_char=0,
            end_char=0,
            start_line=0,
            end_line=0
        )
        
        chapter = Chapter(title, number, metalocation)
        self.chapters.append(chapter)
        return chapter
    
    def get_all_concepts(self) -> List[Concept]:
        """Get all concepts in this book."""
        all_concepts = list(self.concepts)
        for chapter in self.chapters:
            all_concepts.extend(chapter.get_all_concepts())
        return all_concepts
    
    def hash(self) -> str:
        """Merkle root hash of entire book."""
        chapter_hashes = [c.hash() for c in self.chapters]
        combined = "".join(chapter_hashes)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def bibliography_entry(self) -> str:
        """Generate bibliography entry for this book."""
        return (f"{self.author}. {self.title} "
                f"({self.edition} ed.). {self.year}. "
                f"ISBN: {self.isbn}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "isbn": self.isbn,
            "year": self.year,
            "edition": self.edition,
            "chapter_count": len(self.chapters),
            "concept_count": len(self.get_all_concepts()),
            "total_chars": self.total_chars,
            "hash": self.hash(),
            "created_at": self.created_at
        }


class KnowledgeHierarchy:
    """
    Manages the complete hierarchy of knowledge objects.
    
    Provides navigation, querying, and traversal across all levels.
    """
    
    def __init__(self):
        self.books: Dict[str, Book] = {}  # ISBN → Book
        self.chapters: Dict[str, Chapter] = {}  # Chapter ID → Chapter
        self.sections: Dict[str, Section] = {}  # Section ID → Section
        self.paragraphs: Dict[str, Paragraph] = {}  # Para ID → Paragraph
        self.sentences: Dict[str, Sentence] = {}  # Sent ID → Sentence
        self.concepts: Dict[str, Concept] = {}  # Concept ID → Concept
        
        self.created_at = datetime.now().timestamp()
    
    def add_book(self, title: str, author: str, isbn: str, 
                 year: int, edition: int = 1) -> Book:
        """Add a new book to the hierarchy."""
        book = Book(title, author, isbn, year, edition)
        self.books[isbn] = book
        return book
    
    def add_concept(self, concept: Concept) -> None:
        """Register a concept in the hierarchy."""
        self.concepts[concept.id] = concept
    
    def get_concept_by_text(self, text: str) -> Optional[Concept]:
        """Find concept by exact text match."""
        for concept in self.concepts.values():
            if concept.text == text:
                return concept
        return None
    
    def get_concepts_by_keyword(self, keyword: str) -> List[Concept]:
        """Find all concepts containing a keyword."""
        return [c for c in self.concepts.values() 
                if keyword in c.keywords]
    
    def get_concepts_by_source(self, source_id: str) -> List[Concept]:
        """Get all concepts from a specific source."""
        return [c for c in self.concepts.values() 
                if c.metalocation.source_id == source_id]
    
    def get_book_hierarchy(self, isbn: str) -> Optional[Dict[str, Any]]:
        """Get complete hierarchy for a book."""
        book = self.books.get(isbn)
        if not book:
            return None
        return book.to_dict()
    
    def get_path_to_concept(self, concept_id: str) -> Optional[str]:
        """Get the hierarchical path to a concept."""
        concept = self.concepts.get(concept_id)
        if not concept:
            return None
        return concept.metalocation.to_path()
    
    def statistics(self) -> Dict[str, Any]:
        """Get statistics about the hierarchy."""
        total_concepts = len(self.concepts)
        
        return {
            "total_books": len(self.books),
            "total_chapters": len(self.chapters),
            "total_sections": len(self.sections),
            "total_paragraphs": len(self.paragraphs),
            "total_sentences": len(self.sentences),
            "total_concepts": total_concepts,
            "avg_concepts_per_book": total_concepts / max(len(self.books), 1),
            "created_at": self.created_at
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Export entire hierarchy."""
        return {
            "books": [b.to_dict() for b in self.books.values()],
            "total_concepts": len(self.concepts),
            "statistics": self.statistics()
        }


# Example usage and builder
class HierarchyBuilder:
    """Helper to construct hierarchies from text."""
    
    @staticmethod
    def from_book_structure(title: str, author: str, isbn: str, year: int,
                           structure: Dict[str, Any]) -> Book:
        """
        Build a book hierarchy from nested dictionary structure.
        
        Example structure:
        {
            "Chapter 1": {
                "title": "Foundations",
                "sections": {
                    "1.1": {
                        "title": "Introduction",
                        "paragraphs": [
                            "Paragraph text 1",
                            "Paragraph text 2"
                        ]
                    }
                }
            }
        }
        """
        book = Book(title, author, isbn, year)
        
        for ch_num, (ch_name, ch_data) in enumerate(structure.items(), 1):
            chapter = book.add_chapter(ch_data.get("title", ch_name), ch_num)
            
            for sec_num, (sec_key, sec_data) in enumerate(
                ch_data.get("sections", {}).items()
            ):
                section = chapter.add_section(
                    sec_data.get("title", sec_key),
                    sec_key
                )
                
                for para_text in sec_data.get("paragraphs", []):
                    section.add_paragraph(para_text)
        
        return book
