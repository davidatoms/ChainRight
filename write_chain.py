#!/usr/bin/env python3
"""Live writing → ChainRight letter+word chain.

Captures keystrokes one at a time, turns each character into a letter-event
chain block (with JSON metadata: timestamp, predicted_class, confidence,
dictionary_id, validity), assembles words at boundary characters and
validates them against the pretraining corpus.

Each invocation appends to the existing chain or creates a new one. The
chain becomes a durable, cryptographically anchored journal of every
character written across every session — the same shape the chain has for
Brain2Text-style decoder output, just with a human at the keyboard
instead of a BCI.

The output JSON is structured exactly like the chain produced by
`examples/brain2text_chain_decoder_draft.py`, so downstream analysis
tools (the equilibrium harness, the boolean-signature classifier, the
corpus-membership scanner) can consume writing-session chains
interchangeably with decoder-session chains.

Usage:
    python write_chain.py                                # default chain at writing_chain.json
    python write_chain.py --chain-out journal.chain.json
    python write_chain.py --session morning --corpus-source small-117M-k40
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional

from chainright.blockchain import Blockchain
from chainright.brain2text_chain import (
    LetterEventRecord,
    WordEventRecord,
    assemble_word_record,
    chain_letter_event,
    chain_word_event,
    session_summary,
)
from chainright.character_dictionary import default_dictionary, dictionary_id
from chainright.datasets import iter_records


WORD_BOUNDARY_CHARS = set(" \t\n.,!?;:()")


def build_corpus_check_fn(source: str, split: str, data_dir: Optional[Path]):
    """Load the chosen corpus once into memory, then return a closure that
    substring-matches a word against it.

    Linear scan per word — acceptable for typing-rate input (~3-5 chars/s)
    against any of the gpt-2-output-dataset test/valid splits (5K records
    each). For very large corpora or many words per second, swap in a
    substring index.
    """
    print(f"Loading corpus {source}.{split}...", file=sys.stderr)
    texts: List[str] = []
    for record in iter_records(source, split, data_dir=data_dir):
        text = record.get("text", "")
        if text:
            texts.append(text)
    print(f"  {len(texts)} records loaded", file=sys.stderr)

    def check(word: str) -> Dict[str, Any]:
        for i, text in enumerate(texts, start=1):
            if word and word in text:
                return {
                    "present": True,
                    "first_match_record_index": i,
                    "source": source,
                    "split": split,
                }
        return {
            "present": False,
            "first_match_record_index": None,
            "source": source,
            "split": split,
        }

    return check


def capture_keystrokes_windows(
    blockchain: Blockchain,
    dictionary,
    corpus_check_fn,
    session_id: str,
    starting_step: int = 0,
):
    """Per-keystroke capture on Windows via msvcrt. Returns counts."""
    import msvcrt  # local import; only available on Windows

    pending: List[Dict[str, Any]] = []
    n_letters = 0
    n_words = 0
    step = starting_step
    last_keystroke_t = perf_counter()
    start_t = last_keystroke_t

    sys.stdout.write(">>> ")
    sys.stdout.flush()

    while True:
        try:
            ch = msvcrt.getwch()
        except KeyboardInterrupt:
            break

        now = perf_counter()

        # End-of-stream sentinels.
        if ch in ("\x03", "\x04", "\x1a"):  # Ctrl+C, Ctrl+D, Ctrl+Z
            sys.stdout.write("\n")
            sys.stdout.flush()
            break

        # Backspace removes the last pending letter from the in-progress word
        # but stays out of the chain (we record forward-progress events only).
        if ch in ("\x08", "\x7f"):
            if pending:
                pending.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
                last_keystroke_t = now
            continue

        # Enter normalizes to '\n' and is treated as a word boundary.
        if ch == "\r":
            ch = "\n"
            sys.stdout.write("\n")
            sys.stdout.flush()
        elif ch.isprintable() or ch in WORD_BOUNDARY_CHARS:
            sys.stdout.write(ch)
            sys.stdout.flush()
        else:
            # Skip unknown control sequences (arrow keys, F-keys, etc.).
            continue

        # Confidence model for human typing: 1.0 baseline, no decoder
        # uncertainty. Inter-keystroke interval is preserved in `extra` so
        # downstream tools can model pauses as a soft confidence signal.
        interval = now - last_keystroke_t
        last_keystroke_t = now

        # Signal hash anchors the event to (session_id, step, char) — there's
        # no underlying neural / image signal for typed input, so this is the
        # honest cryptographic anchor.
        signal_hash = hashlib.sha256(
            f"{session_id}:{step}:{ch}".encode("utf-8")
        ).hexdigest()

        info = chain_letter_event(
            blockchain,
            LetterEventRecord(
                predicted_class=ch,
                confidence=1.0,
                raw_signal_hash=signal_hash,
                extra={"inter_keystroke_seconds": interval},
            ),
            character_dictionary=dictionary,
            session_id=session_id,
        )
        n_letters += 1
        step += 1

        if ch in WORD_BOUNDARY_CHARS:
            if pending:
                record = assemble_word_record(pending)
                chain_word_event(
                    blockchain,
                    record,
                    corpus_check_fn=corpus_check_fn,
                    session_id=session_id,
                )
                n_words += 1
                pending = []
        else:
            pending.append(info)

    # Flush trailing word at end-of-stream.
    if pending:
        record = assemble_word_record(pending)
        chain_word_event(
            blockchain,
            record,
            corpus_check_fn=corpus_check_fn,
            session_id=session_id,
        )
        n_words += 1

    return {
        "letters": n_letters,
        "words": n_words,
        "final_step": step,
        "elapsed_seconds": perf_counter() - start_t,
    }


def capture_line_posix(
    blockchain: Blockchain,
    dictionary,
    corpus_check_fn,
    session_id: str,
    starting_step: int = 0,
):
    """POSIX fallback: read whole lines and process them character-by-character
    after submission. No per-keystroke timing."""
    print(">>> Type lines. Empty line ends the session.", file=sys.stderr)

    pending: List[Dict[str, Any]] = []
    n_letters = 0
    n_words = 0
    step = starting_step
    start_t = perf_counter()

    while True:
        try:
            line = input(">>> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            break

        for ch in line + "\n":  # treat the line break as a boundary
            signal_hash = hashlib.sha256(
                f"{session_id}:{step}:{ch}".encode("utf-8")
            ).hexdigest()
            info = chain_letter_event(
                blockchain,
                LetterEventRecord(
                    predicted_class=ch,
                    confidence=1.0,
                    raw_signal_hash=signal_hash,
                ),
                character_dictionary=dictionary,
                session_id=session_id,
            )
            n_letters += 1
            step += 1

            if ch in WORD_BOUNDARY_CHARS:
                if pending:
                    record = assemble_word_record(pending)
                    chain_word_event(
                        blockchain,
                        record,
                        corpus_check_fn=corpus_check_fn,
                        session_id=session_id,
                    )
                    n_words += 1
                    pending = []
            else:
                pending.append(info)

    if pending:
        record = assemble_word_record(pending)
        chain_word_event(
            blockchain,
            record,
            corpus_check_fn=corpus_check_fn,
            session_id=session_id,
        )
        n_words += 1

    return {
        "letters": n_letters,
        "words": n_words,
        "final_step": step,
        "elapsed_seconds": perf_counter() - start_t,
    }


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument(
        "--chain-out",
        type=Path,
        default=Path("writing_chain.json"),
        help="Path to the persistent writing chain. Created if missing, "
             "appended otherwise. Default: ./writing_chain.json",
    )
    p.add_argument(
        "--session",
        type=str,
        default=None,
        help="Session id stored in every block this run produces. "
             "Defaults to 'writing-<unix-timestamp>'.",
    )
    p.add_argument(
        "--corpus-source",
        type=str,
        default="webtext",
        help="gpt-2-output-dataset source for word validation. Default: webtext",
    )
    p.add_argument(
        "--corpus-split",
        type=str,
        default="test",
        choices=["train", "valid", "test"],
        help="Which split. Default: test (smallest, fastest).",
    )
    p.add_argument(
        "--corpus-data-dir",
        type=Path,
        default=None,
        help="Path to gpt-2-output-dataset/data. Auto-detected if omitted.",
    )
    p.add_argument(
        "--difficulty",
        type=int,
        default=0,
        help="Chain proof-of-work difficulty. Default 0 (no PoW) for live "
             "typing throughput; bump to 1+ if you want stronger anchoring "
             "at the cost of typing-keystroke latency.",
    )
    p.add_argument(
        "--no-special",
        action="store_true",
        help="Use the 62-class base dictionary without punctuation. "
             "Default includes common punctuation and whitespace.",
    )
    args = p.parse_args(argv)

    session_id = args.session or f"writing-{int(time.time())}"

    dictionary = default_dictionary(include_special=not args.no_special)
    print(
        f"Character dictionary: {len(dictionary)} chars, "
        f"id={dictionary_id(dictionary)[:16]}...",
        file=sys.stderr,
    )

    corpus_check_fn = build_corpus_check_fn(
        args.corpus_source, args.corpus_split, args.corpus_data_dir,
    )

    # Load existing chain or create a new one.
    if args.chain_out.exists():
        blockchain = Blockchain.load_from_file(str(args.chain_out))
        starting_step = len([b for b in blockchain.chain[1:]])
        print(
            f"Resuming chain from {args.chain_out} "
            f"({len(blockchain.chain)} blocks already)",
            file=sys.stderr,
        )
    else:
        blockchain = Blockchain(difficulty=args.difficulty)
        starting_step = 0
        print(f"New chain. (difficulty={args.difficulty})", file=sys.stderr)

    print(f"Session: {session_id}", file=sys.stderr)
    print(
        "Type. Ctrl+C, Ctrl+D, or Ctrl+Z saves and exits. Backspace removes "
        "from the in-progress word (not from the chain — the chain is "
        "forward-progress only).",
        file=sys.stderr,
    )
    print(file=sys.stderr)

    if sys.platform == "win32":
        result = capture_keystrokes_windows(
            blockchain, dictionary, corpus_check_fn, session_id, starting_step,
        )
    else:
        result = capture_line_posix(
            blockchain, dictionary, corpus_check_fn, session_id, starting_step,
        )

    blockchain.save_to_file(str(args.chain_out))

    summary = session_summary(blockchain, session_id=session_id)
    print(file=sys.stderr)
    print(f"--- Session {session_id} ---", file=sys.stderr)
    print(f"  Letters chained:        {result['letters']}", file=sys.stderr)
    print(f"  Words chained:          {result['words']}", file=sys.stderr)
    print(f"  Elapsed:                {result['elapsed_seconds']:.1f}s", file=sys.stderr)
    print(
        f"  Letter validity rate:   {summary['letter_validity_rate']:.2%}",
        file=sys.stderr,
    )
    print(
        f"  Word corpus-match rate: {summary['word_corpus_match_rate']:.2%}",
        file=sys.stderr,
    )
    if summary["out_of_dict_chars_seen"]:
        print(
            f"  Out-of-dict chars:      {summary['out_of_dict_chars_seen']}",
            file=sys.stderr,
        )
    print(
        f"  Total chain length:     {len(blockchain.chain)} blocks "
        f"(valid={blockchain.is_chain_valid()})",
        file=sys.stderr,
    )
    print(f"  Saved to:               {args.chain_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
