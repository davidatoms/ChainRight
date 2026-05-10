"""ARPABET phoneme label set for the phoneme-layer chain.

The classic ARPABET (Carnegie Mellon variant) has 39 phonemes for U.S.
English, plus a blank class for CTC decoders and a silence/pause class
for explicit non-speech segments. Brain2Text-style decoders typically
emit 40-41 classes (39 phonemes + blank + sometimes silence).

This module exposes the standard 39-phoneme set plus blank/silence
constants. For pipelines using IPA or other phoneme inventories, build
your own `Set[str]` and pass it to `chain_phoneme_event` — the chain
primitive doesn't care which inventory you use, only that it's a fixed
set with a deterministic id.
"""

from __future__ import annotations

import hashlib
from typing import Set


# CMU / ARPABET 39 phonemes (standard for U.S. English).
ARPABET_PHONEMES: Set[str] = {
    # Vowels
    "AA", "AE", "AH", "AO", "AW", "AY",
    "EH", "ER", "EY",
    "IH", "IY",
    "OW", "OY",
    "UH", "UW",
    # Consonants
    "B", "CH", "D", "DH",
    "F", "G", "HH",
    "JH", "K", "L", "M", "N", "NG",
    "P", "R", "S", "SH",
    "T", "TH", "V",
    "W", "Y", "Z", "ZH",
}

# Standard CTC blank and an explicit silence/pause token.
ARPABET_BLANK: str = "<BLANK>"
ARPABET_SILENCE: str = "<SIL>"


def default_phoneme_set(include_blank: bool = True, include_silence: bool = True) -> Set[str]:
    """Return the default 39-phoneme set, optionally with blank and silence."""
    out = set(ARPABET_PHONEMES)
    if include_blank:
        out.add(ARPABET_BLANK)
    if include_silence:
        out.add(ARPABET_SILENCE)
    return out


def phoneme_set_id(phoneme_set: Set[str]) -> str:
    """Deterministic SHA-256 of a phoneme set.

    Joined with a null byte so multi-char tokens (e.g. 'CH', 'NG', '<SIL>')
    can't collide with concatenations of shorter tokens.
    """
    canonical = "\x00".join(sorted(phoneme_set))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def is_valid_phoneme(symbol: str, phoneme_set: Set[str]) -> bool:
    """Whether `symbol` is in the given phoneme set."""
    return isinstance(symbol, str) and symbol in phoneme_set
