#!/usr/bin/env python3
"""Content fingerprinting and similarity detection for copyright enforcement."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import numpy as np
except ImportError:
    np = None


@dataclass
class ContentFingerprint:
    """Fingerprint of a piece of content for copyright tracking."""
    
    content_hash: str  # SHA-256 of raw content
    content_type: str  # "text", "audio", "image", etc.
    file_size: int  # bytes
    title: str
    creator_wallet: str  # Public key of creator
    timestamp: float  # When registered
    
    # Optional embeddings for similarity detection
    embedding: Optional[list[float]] = None
    embedding_model: Optional[str] = None  # e.g., "monolith-v1"
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "content_hash": self.content_hash,
            "content_type": self.content_type,
            "file_size": self.file_size,
            "title": self.title,
            "creator_wallet": self.creator_wallet,
            "timestamp": self.timestamp,
            "embedding": self.embedding,
            "embedding_model": self.embedding_model,
        }


def compute_content_hash(file_path: str | Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def compute_text_hash(text: str) -> str:
    """Compute SHA-256 hash of text content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_embedding_placeholder(text: str) -> list[float]:
    """
    Get embedding for text (placeholder using mock embeddings).
    
    In production, this would call Monolith or another embedding model.
    For now, we use a simple hash-based deterministic "embedding" of fixed size.
    """
    if np is None:
        # Fallback: use hash components as a "vector"
        hash_val = hashlib.sha256(text.encode()).digest()
        return [float(b) / 255.0 for b in hash_val[:768]]  # 768-dim like many models
    else:
        # Could use actual embeddings here in the future
        hash_val = hashlib.sha256(text.encode()).digest()
        return [float(b) / 255.0 for b in hash_val[:768]]


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not vec_a or not vec_b:
        return 0.0
    
    if np is not None:
        a = np.array(vec_a)
        b = np.array(vec_b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    else:
        # Fallback without numpy
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        mag_a = sum(x ** 2 for x in vec_a) ** 0.5
        mag_b = sum(x ** 2 for x in vec_b) ** 0.5
        return dot_product / (mag_a * mag_b) if mag_a and mag_b else 0.0


def detect_similarity(
    original_fingerprint: ContentFingerprint,
    test_content_or_fingerprint: str | ContentFingerprint,
    threshold: float = 0.80,
) -> dict:
    """
    Detect if test content is similar to original content.
    
    Args:
        original_fingerprint: The original copyrighted work
        test_content_or_fingerprint: Text or another fingerprint to test
        threshold: Similarity threshold (0.0-1.0)
    
    Returns:
        Dict with similarity score, match status, and evidence
    """
    # Get test fingerprint
    if isinstance(test_content_or_fingerprint, str):
        test_embedding = get_embedding_placeholder(test_content_or_fingerprint)
        test_hash = compute_text_hash(test_content_or_fingerprint)
    else:
        test_embedding = test_content_or_fingerprint.embedding or []
        test_hash = test_content_or_fingerprint.content_hash
    
    # Exact hash match
    if original_fingerprint.content_hash == test_hash:
        return {
            "is_match": True,
            "similarity": 1.0,
            "match_type": "EXACT_COPY",
            "evidence": "SHA-256 hash matches perfectly",
        }
    
    # Embedding-based similarity
    if original_fingerprint.embedding and test_embedding:
        similarity = cosine_similarity(original_fingerprint.embedding, test_embedding)
    else:
        # Fallback: compare hash prefixes
        similarity = sum(
            1 for a, b in zip(original_fingerprint.content_hash, test_hash) if a == b
        ) / len(original_fingerprint.content_hash)
    
    match_type = "NO_MATCH"
    if similarity >= threshold:
        match_type = "HIGH_SIMILARITY"
    elif similarity >= 0.70:
        match_type = "MEDIUM_SIMILARITY"
    elif similarity >= 0.50:
        match_type = "LOW_SIMILARITY"
    
    return {
        "is_match": similarity >= threshold,
        "similarity": round(similarity, 4),
        "match_type": match_type,
        "evidence": f"Embedding cosine similarity: {similarity:.2%}",
    }
