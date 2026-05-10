#!/usr/bin/env python3
"""DRAFT bridge: Brain2Text decoder output → ChainRight letter+word chain.

Intended to be moved to `Brain2Text/scripts/chain_decoder_output.py` once
ChainRight is installed in the Brain2Text environment (e.g.
`pip install -e <path-to-ChainRight>`). Living here in `examples/` because
this repo is the canonical home of the helpers; once the script is copied
to Brain2Text it should be deleted from here.

What it does
============
1. Iterates per-character recognition events from Brain2Text's decoder
   output (the placeholder `decoder_event_iterator` is the seam — replace
   it with the actual reader for the chosen format).
2. Hashes each event's source signal and appends a letter-layer block
   to a ChainRight blockchain. Each block records the predicted class,
   confidence, NIST-dictionary validity, and dictionary id.
3. At each whitespace or punctuation boundary, flushes the accumulated
   letter blocks into a word-layer block. Each word block records the
   word string, the letter_block_indices that compose it, the
   confidence statistics, and the corpus-membership result against
   Brain2Text's local pretraining-corpus slice.
4. Emits a `chain.json` for the session plus a printed summary mirroring
   the HB1-HB5 hypotheses in `notes/brain2text_letter_word_chain.md`.

Usage when complete
===================
    python scripts/chain_decoder_output.py \\
        --session t15-copytask-001 \\
        --decoder-output data/rnn_logits/t15_copytask_001.npy \\
        --corpus-data-dir data/ \\
        --corpus-source small-117M-k40 \\
        --corpus-split train \\
        --chain-out runs/chain_t15_copytask_001.json

What still needs filling in
===========================
- `decoder_event_iterator` is a stub. Brain2Text's actual decoder writes
  to a particular format (`.npy` logits, `.pkl` per-frame predictions,
  whatever `data/rnn_logits/` contains); replace the stub body with the
  real reader. See Brain2Text/scripts/inspect_phonemes.py and
  analyze_phoneme_distributions.py for the iteration patterns.
- `WORD_BOUNDARY_CHARS` is a default. Brain2Text's tokenization may not
  emit explicit spaces; review and adjust.
- The corpus-membership scan uses an in-memory linear scan over the
  selected slice. For sessions with many words, build a substring index
  (Aho-Corasick or similar) once and reuse it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from chainright.blockchain import Blockchain
from chainright.brain2text_chain import (
    LetterEventRecord,
    WordEventRecord,
    assemble_word_record,
    chain_letter_event,
    chain_word_event,
    session_summary,
)
from chainright.datasets import iter_records
from chainright.nist_dictionary import default_dictionary, dictionary_id


WORD_BOUNDARY_CHARS = set(" \t\n.,!?;:()")


def decoder_event_iterator(
    decoder_output_path: Path,
) -> Iterator[Tuple[str, float, bytes]]:
    """STUB: yield (predicted_class, confidence, signal_window_bytes).

    REPLACE this body with Brain2Text's actual per-character iteration.
    Examples of what to plug in for each common format:

      - .npy of logits with shape (n_frames, n_classes):
            arr = np.load(decoder_output_path)
            for row in arr:
                cls_idx = int(row.argmax())
                yield CLASS_MAP[cls_idx], float(softmax(row).max()), row.tobytes()

      - .pkl of (decoded_string, per_char_confidences):
            with open(decoder_output_path, "rb") as f:
                text, confs = pickle.load(f)
            for ch, c in zip(text, confs):
                yield ch, float(c), ch.encode("utf-8")

      - Streaming live decoder via socket: yield as events arrive, with
        a session-id + monotonic-time fallback for signal_window_bytes.

    The signal_window_bytes are the cryptographic anchor — sha256(bytes)
    is what gets recorded in the chain. If you can't provide the actual
    raw signal, hash a session_id + frame_index tuple as a degraded
    substitute (still useful for chain integrity, weaker for mechanistic
    audit).
    """
    raise NotImplementedError(
        "Replace decoder_event_iterator with Brain2Text's actual reader. "
        "See the docstring for examples per output format."
    )


def build_corpus_check_fn(
    corpus_source: str,
    corpus_split: str,
    data_dir: Optional[Path],
):
    """Build a closure that checks word membership in the chosen corpus slice.

    Loads the corpus into memory once; subsequent word checks are linear
    over the in-memory list. For very large corpora or many words, swap
    in a substring index built from this list.
    """
    print(f"Loading corpus {corpus_source}.{corpus_split}...")
    corpus_texts: List[str] = []
    for record in iter_records(corpus_source, corpus_split, data_dir=data_dir):
        text = record.get("text", "")
        if text:
            corpus_texts.append(text)
    print(f"  loaded {len(corpus_texts)} records")

    def check(word: str) -> Dict[str, Any]:
        for i, text in enumerate(corpus_texts, start=1):
            if word and word in text:
                return {
                    "present": True,
                    "first_match_record_index": i,
                    "source": corpus_source,
                    "split": corpus_split,
                }
        return {
            "present": False,
            "first_match_record_index": None,
            "source": corpus_source,
            "split": corpus_split,
        }

    return check


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--session", required=True,
                   help="Brain2Text session id (used in every block payload).")
    p.add_argument("--decoder-output", type=Path, required=True,
                   help="Path to the per-session decoder output file.")
    p.add_argument("--corpus-data-dir", type=Path, default=None,
                   help="gpt-2-output-dataset/data directory (auto-detected if omitted).")
    p.add_argument("--corpus-source", default="small-117M-k40",
                   help="Which gpt-2-output-dataset corpus to validate words against.")
    p.add_argument("--corpus-split", default="train",
                   choices=["train", "valid", "test"])
    p.add_argument("--chain-out", type=Path, required=True,
                   help="Where to write the per-session chain JSON.")
    p.add_argument("--difficulty", type=int, default=1,
                   help="Chain proof-of-work difficulty. 0 for live BCI (no PoW).")
    p.add_argument("--include-special", action="store_true", default=True,
                   help="Include common punctuation/whitespace in the dictionary.")
    args = p.parse_args(argv)

    nist_dict = default_dictionary(include_special=args.include_special)
    print(f"Dictionary: {len(nist_dict)} chars, id={dictionary_id(nist_dict)[:16]}...")

    corpus_check_fn = build_corpus_check_fn(
        args.corpus_source, args.corpus_split, args.corpus_data_dir,
    )

    blockchain = Blockchain(difficulty=args.difficulty)
    print(f"Started chain for session {args.session} (difficulty={args.difficulty})")

    pending_letter_blocks: List[Dict[str, Any]] = []
    n_letters = 0
    n_words = 0

    for char, confidence, signal_bytes in decoder_event_iterator(args.decoder_output):
        signal_hash = hashlib.sha256(signal_bytes).hexdigest()

        info = chain_letter_event(
            blockchain,
            LetterEventRecord(
                predicted_class=char,
                confidence=confidence,
                raw_signal_hash=signal_hash,
            ),
            nist_dictionary=nist_dict,
            session_id=args.session,
        )
        n_letters += 1

        if char in WORD_BOUNDARY_CHARS:
            if pending_letter_blocks:
                record = assemble_word_record(pending_letter_blocks)
                chain_word_event(
                    blockchain, record,
                    corpus_check_fn=corpus_check_fn,
                    session_id=args.session,
                )
                n_words += 1
                pending_letter_blocks = []
        else:
            pending_letter_blocks.append(info)

    # Flush final word if utterance ends without a boundary.
    if pending_letter_blocks:
        record = assemble_word_record(pending_letter_blocks)
        chain_word_event(
            blockchain, record,
            corpus_check_fn=corpus_check_fn,
            session_id=args.session,
        )
        n_words += 1

    args.chain_out.parent.mkdir(parents=True, exist_ok=True)
    blockchain.save_to_file(str(args.chain_out))

    summary = session_summary(blockchain, session_id=args.session)
    print()
    print(f"Session {args.session} chained.")
    print(f"  Letter events:           {summary['letter_events']}")
    print(f"  Letter validity rate:    {summary['letter_validity_rate']:.2%}")
    print(f"  Word events:             {summary['word_events']}")
    print(f"  Word corpus-match rate:  {summary['word_corpus_match_rate']:.2%}")
    print(f"  Mean letter confidence:  {summary['mean_letter_confidence']:.3f}")
    if summary["out_of_dict_chars_seen"]:
        print(f"  Out-of-dictionary chars: {summary['out_of_dict_chars_seen']}")
    print(f"  Chain length:            {len(blockchain.chain)} blocks")
    print(f"  Chain valid:             {blockchain.is_chain_valid()}")
    print(f"  Saved to:                {args.chain_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
