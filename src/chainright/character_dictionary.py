"""Generic character-class dictionary for ChainRight letter-layer audit.

Provides the basic letter / digit / punctuation alphabet that the letter+word
chain validates each character against. The 62-class Latin alphanumeric set
(10 digits + 26 upper + 26 lower) happens to match NIST Special Database 19,
but the framing here is generic — typing, character-level decoders, OCR,
anything that emits one character at a time.

For an explicit NIST-handwriting framing (with `SD19_*` aliases for
self-documenting chain blocks) see `chainright.nist_handwriting`. For
phoneme-layer audit see `chainright.phoneme`.

Each dictionary has a deterministic SHA-256 id so chain blocks can certify
exactly which alphabet was applied at recognition time.
"""

from __future__ import annotations

import hashlib
from typing import Set


# Latin alphanumeric base — 62 characters total.
DIGITS: Set[str] = set("0123456789")
UPPERCASE_LATIN: Set[str] = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
LOWERCASE_LATIN: Set[str] = set("abcdefghijklmnopqrstuvwxyz")
BASIC_LATIN_LETTERS: Set[str] = UPPERCASE_LATIN | LOWERCASE_LATIN
BASIC_LATIN: Set[str] = DIGITS | BASIC_LATIN_LETTERS

# Punctuation extensions — separate from the alphanumeric base because most
# decoders / typing flows want to opt in or out of including these.
COMMON_SPECIAL: Set[str] = set(" .,!?;:'\"-()")
EXTENDED_SPECIAL: Set[str] = COMMON_SPECIAL | set("[]{}/\\@#$%&*+=<>")


def default_dictionary(include_special: bool = True) -> Set[str]:
    """Default character-class dictionary for letter-layer audit.

    With include_special=True, returns the 62 base classes plus common
    whitespace and punctuation. With False, just the 62 base classes.
    """
    return BASIC_LATIN | (COMMON_SPECIAL if include_special else set())


def dictionary_id(dictionary: Set[str]) -> str:
    """Deterministic SHA-256 of a character dictionary.

    Two dictionaries containing the same characters always produce the same
    id, regardless of insertion order. Chain blocks store this id so an
    auditor can verify which version of the alphabet was applied.
    """
    canonical = "".join(sorted(dictionary))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def is_valid_class(char: str, dictionary: Set[str]) -> bool:
    """Whether `char` is a single-character entry in `dictionary`."""
    return len(char) == 1 and char in dictionary


def coverage_report(text: str, dictionary: Set[str]) -> dict:
    """Per-character coverage of `text` by `dictionary`.

    Returns counts of in-set vs. out-of-set characters and a sorted,
    deduplicated list of out-of-set characters that appeared.
    """
    in_count = 0
    out_count = 0
    out_chars: Set[str] = set()
    for ch in text:
        if ch in dictionary:
            in_count += 1
        else:
            out_count += 1
            out_chars.add(ch)
    total = in_count + out_count
    return {
        "total_chars": total,
        "in_dictionary": in_count,
        "out_of_dictionary": out_count,
        "coverage_rate": (in_count / total) if total > 0 else 0.0,
        "out_of_dict_chars": sorted(out_chars),
    }
