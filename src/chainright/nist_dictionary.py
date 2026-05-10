"""NIST SD 19 character class dictionary for ChainRight letter-layer audit.

NIST Special Database 19 (SD 19) provides hand-printed character data with
a 62-class label set:
    10 digit classes:     0-9
    26 uppercase classes: A-Z
    26 lowercase classes: a-z

This module exposes that label set as Python sets, plus a configurable
extension for whitespace and punctuation common in modern decoder output
but not part of SD 19. Each dictionary has a deterministic SHA-256 id so
chain blocks can certify exactly which alphabet was applied at recognition
time.
"""

from __future__ import annotations

import hashlib
from typing import Set


NIST_SD19_DIGITS: Set[str] = set("0123456789")
NIST_SD19_UPPERCASE: Set[str] = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
NIST_SD19_LOWERCASE: Set[str] = set("abcdefghijklmnopqrstuvwxyz")
NIST_SD19_BASE: Set[str] = NIST_SD19_DIGITS | NIST_SD19_UPPERCASE | NIST_SD19_LOWERCASE

COMMON_SPECIAL: Set[str] = set(" .,!?;:'\"-()")
EXTENDED_SPECIAL: Set[str] = COMMON_SPECIAL | set("[]{}/\\@#$%&*+=<>")


def default_dictionary(include_special: bool = True) -> Set[str]:
    """Return the default character-class dictionary for letter-layer audit.

    With include_special=True, returns NIST SD 19's 62 classes plus common
    punctuation and whitespace. With False, just the 62 base classes.
    """
    return NIST_SD19_BASE | (COMMON_SPECIAL if include_special else set())


def dictionary_id(dictionary: Set[str]) -> str:
    """Deterministic SHA-256 of a character dictionary.

    Two dictionaries containing the same characters always produce the
    same id, regardless of insertion order. Chain blocks store this id
    so an auditor can verify which version of the alphabet was applied.
    """
    canonical = "".join(sorted(dictionary))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def is_valid_class(char: str, dictionary: Set[str]) -> bool:
    """Whether `char` is a single-character entry in `dictionary`."""
    return len(char) == 1 and char in dictionary


def coverage_report(text: str, dictionary: Set[str]) -> dict:
    """Per-character coverage of `text` by `dictionary`.

    Returns counts of in-set vs. out-of-set characters and the
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
