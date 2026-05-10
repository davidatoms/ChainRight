"""NIST handwriting-specific dictionaries and label sets.

Kept separate from `chainright.character_dictionary` so the generic
letter+word chain doesn't impose NIST framing by default. Use this module
when the use case is specifically NIST handwriting recognition (SD 19
hand-printed characters, future SD 1/3/7/13 form database integrations,
etc.).

Today exposes the SD 19 62-class label set. The characters are the same
as `character_dictionary.BASIC_LATIN`, but the SD19_* aliases here make
NIST-framed chain blocks self-documenting via the dictionary id and let
the SD 19 framing be opt-in.
"""

from chainright.nist_handwriting.sd19 import (
    SD19_BASE,
    SD19_DIGITS,
    SD19_LOWERCASE,
    SD19_UPPERCASE,
    sd19_dictionary,
)

__all__ = [
    "SD19_BASE",
    "SD19_DIGITS",
    "SD19_LOWERCASE",
    "SD19_UPPERCASE",
    "sd19_dictionary",
]
