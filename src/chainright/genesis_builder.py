#!/usr/bin/env python3
"""
Genesis Builder

Constructs the Genesis Block by:
1. Loading pretraining corpus (books, papers, websites)
2. Parsing into hierarchical objects
3. Extracting concepts
4. Building Merkle tree
5. Creating Genesis Block with complete provenance
"""

import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import re

from chainright.knowledge_hierarchy import (
    Book, Chapter, Section, Paragraph, Sentence, Concept,
    Metalocation, KnowledgeHierarchy, HierarchyBuilder
)
from chainright.blockchain import Block


class GenesisBuilder:
    """
    Constructs Genesis Block from pretraining corpus.
    
    Process:
    1. Load source documents
    2. Parse hierarchically
    3. Extract concepts
    4. Build knowledge graph
    5. Create immutable genesis record
    """
    
    def __init__(self, output_path: str = ".chainright/genesis"):
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        self.hierarchy = KnowledgeHierarchy()
        self.concept_index: Dict[str, Concept] = {}
        self.sources_processed: List[Dict[str, Any]] = []
    
    def add_book_from_dict(self, book_data: Dict[str, Any]) -> Book:
        """
        Add a book from dictionary structure.
        
        Expected format:
        {
            "title": "...",
            "author": "...",
            "isbn": "...",
            "year": 2009,
            "edition": 3,
            "chapters": {
                "1": {
                    "title": "Foundations",
                    "sections": {
                        "1.1": {
                            "title": "The Role of Algorithms",
                            "paragraphs": ["..."]
                        }
                    }
                }
            }
        }
        """
        book = self.hierarchy.add_book(
            title=book_data["title"],
            author=book_data["author"],
            isbn=book_data["isbn"],
            year=book_data["year"],
            edition=book_data.get("edition", 1)
        )
        
        # Process chapters
        for ch_num_str, ch_data in book_data.get("chapters", {}).items():
            ch_num = int(ch_num_str)
            chapter = book.add_chapter(ch_data["title"], ch_num)
            
            # Process sections
            for sec_num, sec_data in ch_data.get("sections", {}).items():
                section = chapter.add_section(sec_data["title"], sec_num)
                
                # Process paragraphs
                for para_idx, para_text in enumerate(
                    sec_data.get("paragraphs", [])
                ):
                    paragraph = section.add_paragraph(para_text)
                    
                    # Process sentences
                    sentences = self._split_sentences(para_text)
                    for sent_idx, sent_text in enumerate(sentences):
                        sentence = paragraph.add_sentence(sent_text)
                        self.hierarchy.sentences[sentence.id] = sentence
                    
                    self.hierarchy.paragraphs[paragraph.id] = paragraph
                
                self.hierarchy.sections[section.id] = section
            
            self.hierarchy.chapters[chapter.id] = chapter
        
        self.hierarchy.books[book.isbn] = book
        
        # Record source
        self.sources_processed.append({
            "type": "book",
            "isbn": book.isbn,
            "title": book.title,
            "author": book.author,
            "concepts_extracted": len(book.get_all_concepts()),
            "processed_at": datetime.now().isoformat()
        })
        
        return book
    
    def add_paper_from_dict(self, paper_data: Dict[str, Any]) -> Book:
        """
        Add an academic paper.
        
        Expected format:
        {
            "title": "...",
            "authors": ["..."],
            "arxiv_id": "1706.03762",
            "year": 2017,
            "sections": {
                "1": {
                    "title": "Introduction",
                    "paragraphs": ["..."]
                }
            }
        }
        """
        # Papers treated as single-chapter books
        book = self.hierarchy.add_book(
            title=paper_data["title"],
            author=", ".join(paper_data.get("authors", ["Unknown"])),
            isbn=paper_data.get("arxiv_id", "PAPER_" + str(len(self.hierarchy.books))),
            year=paper_data.get("year", 2024),
            edition=1
        )
        
        # Add all sections as one chapter
        chapter = book.add_chapter("Full Paper", 1)
        
        for sec_num, sec_data in paper_data.get("sections", {}).items():
            section = chapter.add_section(sec_data["title"], sec_num)
            
            for para_text in sec_data.get("paragraphs", []):
                paragraph = section.add_paragraph(para_text)
                
                sentences = self._split_sentences(para_text)
                for sentence_text in sentences:
                    sentence = paragraph.add_sentence(sentence_text)
                    self.hierarchy.sentences[sentence.id] = sentence
                
                self.hierarchy.paragraphs[paragraph.id] = paragraph
            
            self.hierarchy.sections[section.id] = section
        
        self.hierarchy.chapters[chapter.id] = chapter
        self.hierarchy.books[book.isbn] = book
        
        self.sources_processed.append({
            "type": "paper",
            "arxiv_id": paper_data.get("arxiv_id"),
            "title": book.title,
            "authors": paper_data.get("authors", []),
            "concepts_extracted": len(book.get_all_concepts()),
            "processed_at": datetime.now().isoformat()
        })
        
        return book
    
    def extract_concepts(self, book_isbn: str, extractor_func=None) -> List[Concept]:
        """
        Extract concepts from a book.
        
        Args:
            book_isbn: ISBN of book to extract from
            extractor_func: Optional function to extract concepts from text
                           Default: simple noun phrase extraction
        
        Returns:
            List of extracted concepts
        """
        book = self.hierarchy.books.get(book_isbn)
        if not book:
            raise ValueError(f"Book {book_isbn} not found")
        
        if extractor_func is None:
            extractor_func = self._extract_key_phrases
        
        extracted = []
        
        for chapter in book.chapters:
            for section in chapter.sections:
                for paragraph in section.paragraphs:
                    # Extract concepts from paragraph
                    text = paragraph.text
                    phrases = extractor_func(text)
                    
                    for phrase in phrases:
                        concept = Concept(
                            id=str(len(self.concept_index)),
                            text=phrase,
                            metalocation=Metalocation(
                                source_type="book",
                                source_id=book.isbn,
                                source_title=book.title,
                                source_author=book.author,
                                source_year=book.year,
                                book_title=book.title,
                                chapter_number=chapter.number,
                                chapter_title=chapter.title,
                                section_number=section.number,
                                section_title=section.title,
                                page_number=0,  # Would need layout info
                                paragraph_number=paragraph.index,
                                sentence_number=0,
                                start_char=0,
                                end_char=0,
                                start_line=0,
                                end_line=0
                            ),
                            embedding=[],  # Mock - Monolith would fill this
                            keywords=phrase.split(),
                            key_entities=[],
                            importance_score=0.5,
                            clarity_score=0.8,
                            citations_in_genesis=0,
                            preceding_sentence=None,
                            following_sentence=None,
                            section_context=section.title,
                            created_at=datetime.now().timestamp(),
                            processed_at=datetime.now().timestamp()
                        )
                        
                        self.concept_index[concept.id] = concept
                        self.hierarchy.concepts[concept.id] = concept
                        paragraph.add_concept(concept)
                        extracted.append(concept)
        
        return extracted
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple regex-based splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _extract_key_phrases(self, text: str, max_phrases: int = 10) -> List[str]:
        """Extract key phrases (simple implementation)."""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been'
        }
        
        # Extract noun phrases (capitalized words + words after them)
        words = text.split()
        phrases = []
        
        for i, word in enumerate(words):
            if word[0].isupper() and word.lower() not in stop_words:
                phrase = word
                # Look ahead for modifiers
                if i + 1 < len(words) and words[i + 1][0].isupper():
                    phrase += " " + words[i + 1]
                phrases.append(phrase)
        
        # Return unique phrases up to max
        return list(set(phrases))[:max_phrases]
    
    def build_merkle_tree(self) -> str:
        """
        Build Merkle tree of all concepts.
        
        Returns:
            Root hash of Merkle tree
        """
        if not self.hierarchy.concepts:
            return hashlib.sha256(b"empty").hexdigest()
        
        # Create leaf hashes
        concept_hashes = [
            hashlib.sha256(json.dumps(c.to_dict(), sort_keys=True).encode()).hexdigest()
            for c in self.hierarchy.concepts.values()
        ]
        
        # Build tree bottom-up
        while len(concept_hashes) > 1:
            level_hashes = []
            for i in range(0, len(concept_hashes), 2):
                if i + 1 < len(concept_hashes):
                    combined = concept_hashes[i] + concept_hashes[i + 1]
                else:
                    combined = concept_hashes[i] + concept_hashes[i]
                
                level_hash = hashlib.sha256(combined.encode()).hexdigest()
                level_hashes.append(level_hash)
            
            concept_hashes = level_hashes
        
        return concept_hashes[0]
    
    def create_genesis_block(self) -> Block:
        """
        Create the Genesis Block containing all pretraining corpus.
        
        Returns:
            Genesis Block
        """
        merkle_root = self.build_merkle_tree()
        
        genesis_data = {
            "type": "GENESIS_WITH_PRETRAINING",
            "version": "1.0",
            "created": datetime.now().isoformat(),
            
            "sources": self.sources_processed,
            "total_sources": len(self.sources_processed),
            "total_concepts": len(self.hierarchy.concepts),
            
            "statistics": self.hierarchy.statistics(),
            
            "merkle_root": merkle_root,
            "books": [b.to_dict() for b in self.hierarchy.books.values()],
        }
        
        # Create genesis block
        genesis_block = Block(
            index=0,
            data=json.dumps(genesis_data),
            previous_hash="0",
            difficulty=1,
            node_type="GENESIS"
        )
        
        genesis_block.mine_block()
        
        return genesis_block
    
    def save_to_files(self) -> Dict[str, Path]:
        """Save the genesis corpus to files."""
        files_created = {}
        
        # Save hierarchy
        hierarchy_path = self.output_path / "hierarchy.json"
        with open(hierarchy_path, 'w') as f:
            json.dump(self.hierarchy.to_dict(), f, indent=2)
        files_created["hierarchy"] = hierarchy_path
        
        # Save concepts index
        concepts_path = self.output_path / "concepts.json"
        concepts_data = [c.to_dict() for c in self.hierarchy.concepts.values()]
        with open(concepts_path, 'w') as f:
            json.dump(concepts_data, f, indent=2)
        files_created["concepts"] = concepts_path
        
        # Save sources
        sources_path = self.output_path / "sources.json"
        with open(sources_path, 'w') as f:
            json.dump(self.sources_processed, f, indent=2)
        files_created["sources"] = sources_path
        
        # Save statistics
        stats_path = self.output_path / "statistics.json"
        with open(stats_path, 'w') as f:
            json.dump(self.hierarchy.statistics(), f, indent=2)
        files_created["statistics"] = stats_path
        
        return files_created
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of built genesis."""
        stats = self.hierarchy.statistics()
        
        return {
            "total_sources": len(self.sources_processed),
            "total_concepts": stats["total_concepts"],
            "total_books": stats["total_books"],
            "total_chapters": stats["total_chapters"],
            "total_sections": stats["total_sections"],
            "total_paragraphs": stats["total_paragraphs"],
            "total_sentences": stats["total_sentences"],
            "concepts_per_book": stats.get("avg_concepts_per_book", 0),
            "sources": self.sources_processed
        }


# Example initialization
if __name__ == "__main__":
    # Example: Create a small genesis from structured data
    builder = GenesisBuilder()
    
    # Add CLRS book
    book_data = {
        "title": "Introduction to Algorithms",
        "author": "Cormen, Leiserson, Rivest, Stein",
        "isbn": "ISBN-9780262033848",
        "year": 2009,
        "edition": 3,
        "chapters": {
            "1": {
                "title": "Foundations",
                "sections": {
                    "1.1": {
                        "title": "The Role of Algorithms",
                        "paragraphs": [
                            "An algorithm is a well-defined computational procedure that takes some value or set of values as input and produces some value or set of values as output."
                        ]
                    }
                }
            }
        }
    }
    
    book = builder.add_book_from_dict(book_data)
    builder.extract_concepts(book.isbn)
    genesis_block = builder.create_genesis_block()
    
    print(f"Genesis Block created: {genesis_block.hash[:16]}...")
    print(f"Summary: {builder.get_summary()}")
