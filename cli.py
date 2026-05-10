#!/usr/bin/env python3
"""Tokenize input words across every available view and emit JSON with runtimes.

Each tokenization view is stored as a single delimiter-joined string so the
output JSON stays flat and diffable. The wall-clock cost of every view (and
the total) is recorded under "runtime_seconds".

Usage:
    python cli.py "Hello, world! This is ChainRight."
    python cli.py --input notes.txt --out report.json
    echo "piped text" | python cli.py
    python cli.py --delimiter " " hello world how are you
    python cli.py --typing-test
    python cli.py --typing-test --target "the fed raised rates by 25 bps"
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Callable, Dict, List, Optional, Tuple

from chainright.tokenization import (
    TokenizationView,
    tokenize_bytes,
    tokenize_characters,
    tokenize_sentences,
    tokenize_tiktoken,
    tokenize_whitespace,
    tokenize_words_and_punctuation,
)


Tokenizer = Callable[[str], TokenizationView]


def _builtin_tokenizers() -> List[Tuple[str, Tokenizer]]:
    return [
        ("characters", tokenize_characters),
        ("whitespace", tokenize_whitespace),
        ("words_and_punctuation", tokenize_words_and_punctuation),
        ("sentences", tokenize_sentences),
        ("utf8_bytes", tokenize_bytes),
    ]


def tokenize_with_timing(
    text: str,
    delimiter: str = " | ",
    tiktoken_model: str = "cl100k_base",
) -> Dict:
    """Run every tokenizer on `text`, joining tokens with `delimiter`.

    Returns a dict ready to be json.dumps'd:
        input, character_count, byte_count, tokenizations, token_counts,
        runtime_seconds (per view + total), generated_at.
    """
    tokenizations: Dict[str, str] = {}
    token_counts: Dict[str, int] = {}
    runtimes: Dict[str, float] = {}

    total_start = perf_counter()

    for name, fn in _builtin_tokenizers():
        t0 = perf_counter()
        view = fn(text)
        runtimes[name] = perf_counter() - t0
        tokenizations[name] = delimiter.join(view.tokens)
        token_counts[name] = view.count

    t0 = perf_counter()
    tt_view = tokenize_tiktoken(text, model=tiktoken_model)
    tt_elapsed = perf_counter() - t0
    if tt_view is not None:
        tokenizations[tt_view.name] = delimiter.join(tt_view.tokens)
        token_counts[tt_view.name] = tt_view.count
        runtimes[tt_view.name] = tt_elapsed

    runtimes["total"] = perf_counter() - total_start

    return {
        "input": text,
        "character_count": len(text),
        "byte_count": len(text.encode("utf-8")),
        "delimiter": delimiter,
        "tokenizations": tokenizations,
        "token_counts": token_counts,
        "runtime_seconds": runtimes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _read_input(args: argparse.Namespace) -> str:
    if args.input:
        return Path(args.input).read_text(encoding="utf-8")
    if args.words:
        return " ".join(args.words)
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit(
        "No input. Pass words as arguments, --input <file>, --typing-test, "
        "or pipe via stdin."
    )


# ---------------------------------------------------------------------------
# Typing test
# ---------------------------------------------------------------------------

def _capture_keystrokes_windows() -> Tuple[str, List[float], float]:
    """Read until Enter on Windows, returning (typed_text, intervals, total_seconds).

    `intervals[i]` is seconds between keystroke i-1 and i (intervals[0] is
    seconds from start to first keystroke). Backspace removes the last char.
    """
    import msvcrt

    buf: List[str] = []
    intervals: List[float] = []
    start = perf_counter()
    last = start

    while True:
        ch = msvcrt.getwch()
        now = perf_counter()

        if ch in ("\r", "\n"):
            sys.stdout.write("\n")
            sys.stdout.flush()
            break
        if ch == "\x03":
            raise KeyboardInterrupt
        if ch in ("\x08", "\x7f"):
            if buf:
                buf.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
                intervals.append(now - last)
                last = now
            continue
        if ch.isprintable():
            buf.append(ch)
            sys.stdout.write(ch)
            sys.stdout.flush()
            intervals.append(now - last)
            last = now

    return "".join(buf), intervals, perf_counter() - start


def _capture_line_posix() -> Tuple[str, List[float], float]:
    """POSIX fallback: time the whole-line input, no per-keystroke detail."""
    start = perf_counter()
    text = input()
    elapsed = perf_counter() - start
    return text, [], elapsed


def run_typing_test(target: Optional[str]) -> Tuple[str, List[float], float]:
    if target:
        sys.stdout.write(f"\nType this exactly:\n  {target}\n")
    else:
        sys.stdout.write("\nType anything. Press Enter to submit.\n")
    sys.stdout.write("\nPress Enter when ready to start the timer...")
    sys.stdout.flush()
    input()
    sys.stdout.write(">>> ")
    sys.stdout.flush()

    if sys.platform == "win32":
        return _capture_keystrokes_windows()
    return _capture_line_posix()


def typing_summary(
    typed: str,
    target: Optional[str],
    intervals: List[float],
    elapsed: float,
    report: Dict,
) -> Dict:
    chars = len(typed)
    cps = chars / elapsed if elapsed > 0 else 0.0
    wpm = (cps / 5.0) * 60.0  # standard 5-char word

    accuracy: Optional[float] = None
    if target:
        matches = sum(1 for a, b in zip(typed, target) if a == b)
        accuracy = matches / max(len(target), 1)

    interval_stats: Optional[Dict[str, float]] = None
    if intervals:
        interval_stats = {
            "count": len(intervals),
            "median": statistics.median(intervals),
            "mean": statistics.fmean(intervals),
            "max": max(intervals),
            "min": min(intervals),
            "stdev": statistics.pstdev(intervals) if len(intervals) > 1 else 0.0,
        }

    tokens_per_typing_second: Dict[str, float] = {}
    human_to_tokenizer_ratio: Dict[str, float] = {}
    if elapsed > 0:
        for view, count in report["token_counts"].items():
            tokens_per_typing_second[view] = count / elapsed
        for view, runtime in report["runtime_seconds"].items():
            if runtime > 0:
                human_to_tokenizer_ratio[view] = elapsed / runtime

    return {
        "target": target,
        "typed": typed,
        "elapsed_seconds": elapsed,
        "characters": chars,
        "characters_per_second": cps,
        "wpm_5char_standard": wpm,
        "accuracy_vs_target": accuracy,
        "keystroke_intervals": interval_stats,
        "tokens_per_typing_second": tokens_per_typing_second,
        "human_to_tokenizer_ratio": human_to_tokenizer_ratio,
    }


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chainright-tokenize",
        description="Tokenize input across multiple views and record per-view runtimes.",
    )
    p.add_argument(
        "words",
        nargs="*",
        help="Words to tokenize (joined by spaces). Omit to read --input or stdin.",
    )
    p.add_argument(
        "--input",
        "-i",
        type=str,
        help="Read text from a file instead of positional arguments.",
    )
    p.add_argument(
        "--out",
        "-o",
        type=str,
        help="Write JSON to this path. If omitted, prints to stdout.",
    )
    p.add_argument(
        "--delimiter",
        "-d",
        type=str,
        default=" | ",
        help='String used to join tokens in the stored representation. Default: " | "',
    )
    p.add_argument(
        "--tiktoken-model",
        type=str,
        default="cl100k_base",
        help="tiktoken encoding name (only used if tiktoken is installed).",
    )
    p.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indent level. Use 0 for compact output. Default: 2",
    )
    p.add_argument(
        "--typing-test",
        action="store_true",
        help="Interactive typing test: time how fast you type and compare to "
             "tokenization runtime. On Windows, captures per-keystroke timing.",
    )
    p.add_argument(
        "--target",
        type=str,
        help='Target string for the typing test. If supplied, accuracy is '
             'computed by char-by-char comparison.',
    )
    return p


def main(argv: List[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    typing_data: Optional[Dict] = None
    if args.typing_test:
        typed, intervals, elapsed = run_typing_test(args.target)
        text = typed
    else:
        text = _read_input(args)

    report = tokenize_with_timing(
        text,
        delimiter=args.delimiter,
        tiktoken_model=args.tiktoken_model,
    )

    if args.typing_test:
        typing_data = typing_summary(typed, args.target, intervals, elapsed, report)
        report["typing_test"] = typing_data

    indent = args.indent if args.indent > 0 else None
    payload = json.dumps(report, indent=indent, ensure_ascii=False)

    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        print(f"Wrote {args.out} ({report['runtime_seconds']['total']*1000:.3f} ms total)")
    else:
        print(payload)

    if typing_data:
        print()
        print(f"You typed {typing_data['characters']} chars in "
              f"{typing_data['elapsed_seconds']:.2f}s "
              f"({typing_data['characters_per_second']:.2f} cps, "
              f"{typing_data['wpm_5char_standard']:.1f} wpm).")
        if typing_data["accuracy_vs_target"] is not None:
            print(f"Accuracy vs target: {typing_data['accuracy_vs_target']:.2%}")
        if typing_data["human_to_tokenizer_ratio"]:
            words_view = typing_data["human_to_tokenizer_ratio"].get(
                "words_and_punctuation"
            )
            if words_view is not None:
                print(f"You took {words_view:,.0f}x longer than the "
                      f"words+punctuation tokenizer to produce this text.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
