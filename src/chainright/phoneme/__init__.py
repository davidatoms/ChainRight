"""Phoneme-layer chain primitives for BCI / speech / phonological pipelines.

Parallel to `chainright.brain2text_chain` (the letter+word chain), this
package provides a phoneme-event chain that operates on per-frame phoneme
predictions — the format Brain2Text-style 41-class CTC decoders natively
produce.

Two layers are intended:
  - phoneme_chain.py: per-frame phoneme events
  - phoneme_word_chain.py (TODO): per-word aggregation, where a word is a
    phoneme sequence and the validation oracle is a phonemized version of
    the pretraining corpus (e.g., produced by Brain2Text's
    `phonemize_gpt2_output_dataset.py`).

The letter chain (chainright.brain2text_chain) and the phoneme chain are
independent — different data, same structural shape. Use whichever matches
your decoder's output.
"""

from chainright.phoneme.phoneme_chain import (
    PhonemeEventRecord,
    chain_phoneme_event,
    phoneme_session_summary,
)
from chainright.phoneme.phoneme_dictionary import (
    ARPABET_BLANK,
    ARPABET_PHONEMES,
    ARPABET_SILENCE,
    default_phoneme_set,
    is_valid_phoneme,
    phoneme_set_id,
)

__all__ = [
    "ARPABET_BLANK",
    "ARPABET_PHONEMES",
    "ARPABET_SILENCE",
    "default_phoneme_set",
    "is_valid_phoneme",
    "phoneme_set_id",
    "PhonemeEventRecord",
    "chain_phoneme_event",
    "phoneme_session_summary",
]
