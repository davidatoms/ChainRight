"""NIST Special Database 19 — hand-printed character labels.

SD 19 has 62 character classes:
    10 digit classes:     0-9
    26 uppercase classes: A-Z
    26 lowercase classes: a-z

These are the same characters as `chainright.character_dictionary.BASIC_LATIN`;
the aliases here exist so chain blocks tagged with this dictionary id are
self-documenting as NIST-framed. For broader alphabets, combine `SD19_BASE`
with `character_dictionary.COMMON_SPECIAL` or a caller-defined extension.

SD 19 does not include special characters or whitespace.
"""

from typing import Set

from chainright.character_dictionary import (
    BASIC_LATIN as SD19_BASE,
    DIGITS as SD19_DIGITS,
    LOWERCASE_LATIN as SD19_LOWERCASE,
    UPPERCASE_LATIN as SD19_UPPERCASE,
)


def sd19_dictionary() -> Set[str]:
    """Return the 62-class NIST SD 19 label set as a fresh `Set[str]`."""
    return set(SD19_BASE)
