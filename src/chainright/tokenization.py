"""Tokenization helpers for ChainRight.

This module exposes a few deterministic tokenization strategies so a user can
see how the same text breaks apart across different representations.
Optional model-specific tokenizers are included only when their packages are
installed in the environment.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from importlib.util import find_spec
import re
from typing import List, Optional


TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


@dataclass
class TokenizationView:
    """One tokenization strategy and its output."""

    name: str
    tokens: List[str]

    @property
    def count(self) -> int:
        return len(self.tokens)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["count"] = self.count
        return payload


@dataclass
class TokenizationReport:
    """Combined tokenization output for a single text input."""

    text: str
    views: List[TokenizationView]

    @property
    def character_count(self) -> int:
        return len(self.text)

    @property
    def byte_count(self) -> int:
        return len(self.text.encode("utf-8"))

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "character_count": self.character_count,
            "byte_count": self.byte_count,
            "views": [view.to_dict() for view in self.views],
        }


def tokenize_characters(text: str) -> TokenizationView:
    return TokenizationView(name="characters", tokens=list(text))


def tokenize_whitespace(text: str) -> TokenizationView:
    return TokenizationView(name="whitespace", tokens=text.split())


def tokenize_words_and_punctuation(text: str) -> TokenizationView:
    return TokenizationView(name="words_and_punctuation", tokens=TOKEN_PATTERN.findall(text))


def tokenize_bytes(text: str) -> TokenizationView:
    return TokenizationView(
        name="utf8_bytes",
        tokens=[f"0x{byte:02x}" for byte in text.encode("utf-8")],
    )


def tokenize_sentences(text: str) -> TokenizationView:
    pieces = [piece.strip() for piece in re.split(r"(?<=[.!?])\s+", text) if piece.strip()]
    return TokenizationView(name="sentences", tokens=pieces)


def tokenize_tiktoken(text: str, model: str = "cl100k_base") -> Optional[TokenizationView]:
    if find_spec("tiktoken") is None:
        return None

    import tiktoken  # type: ignore[import-not-found]

    encoding = tiktoken.get_encoding(model)
    token_ids = encoding.encode(text)
    return TokenizationView(
        name=f"tiktoken:{model}",
        tokens=[str(token_id) for token_id in token_ids],
    )


def build_tokenization_report(text: str, model: str = "cl100k_base") -> TokenizationReport:
    views = [
        tokenize_characters(text),
        tokenize_whitespace(text),
        tokenize_words_and_punctuation(text),
        tokenize_sentences(text),
        tokenize_bytes(text),
    ]

    optional_view = tokenize_tiktoken(text, model=model)
    if optional_view is not None:
        views.append(optional_view)

    return TokenizationReport(text=text, views=views)
