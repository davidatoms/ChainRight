"""Loaders for the OpenAI gpt-2-output-dataset.

The dataset is a pair of parallel corpora — `webtext` (human) and one of
several `{small,medium,large,xl}-{117M,345M,762M,1542M}[-k40]` (model). Each
record is a JSON line with keys: id, ended, length, text. There are no
prompts; all samples are unconditional continuations.

This module gives the rest of ChainRight three things:

1. Streaming iterators over a single source.
2. Index-aligned (human, model) pair iterators for distributional studies.
3. Synthesized (prompt, human_completion, model_completion) triples for the
   equilibrium harness, where the prompt is the first K words of the human
   text and the "model_completion" is the corresponding model record at the
   same index. This is a proxy for an aligned generation, not the real thing.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple


VALID_SOURCES = {
    "webtext",
    "small-117M", "small-117M-k40",
    "medium-345M", "medium-345M-k40",
    "large-762M", "large-762M-k40",
    "xl-1542M", "xl-1542M-k40",
}
VALID_SPLITS = {"train", "valid", "test"}


def default_data_dir() -> Path:
    """Path to the dataset, searched in this order:

    1. `$GPT2_OUTPUT_DATASET_DIR` environment variable.
    2. `../gpt-2-output-dataset/data` relative to ChainRight.
    3. `./gpt-2-output-dataset/data` from the current working directory.

    Returns the first existing path. Raises FileNotFoundError if none exist.
    """
    env = os.environ.get("GPT2_OUTPUT_DATASET_DIR")
    candidates: List[Path] = []
    if env:
        candidates.append(Path(env))

    here = Path(__file__).resolve()
    candidates.append(here.parents[3] / "gpt-2-output-dataset" / "data")
    candidates.append(Path.cwd() / "gpt-2-output-dataset" / "data")
    candidates.append(Path.cwd().parent / "gpt-2-output-dataset" / "data")

    for c in candidates:
        if c.exists():
            return c

    raise FileNotFoundError(
        "Could not locate gpt-2-output-dataset/data. "
        "Set GPT2_OUTPUT_DATASET_DIR or run from a directory next to it. "
        f"Tried: {[str(c) for c in candidates]}"
    )


def split_path(source: str, split: str, data_dir: Optional[Path] = None) -> Path:
    if source not in VALID_SOURCES:
        raise ValueError(f"unknown source {source!r}; valid: {sorted(VALID_SOURCES)}")
    if split not in VALID_SPLITS:
        raise ValueError(f"unknown split {split!r}; valid: {sorted(VALID_SPLITS)}")
    base = data_dir if data_dir is not None else default_data_dir()
    return base / f"{source}.{split}.jsonl"


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------

def iter_records(
    source: str,
    split: str,
    data_dir: Optional[Path] = None,
) -> Iterator[Dict]:
    """Yield raw record dicts {id, ended, length, text} from a split."""
    path = split_path(source, split, data_dir)
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def iter_texts(
    source: str,
    split: str,
    data_dir: Optional[Path] = None,
    n: Optional[int] = None,
    min_length: int = 0,
) -> Iterator[str]:
    """Yield text strings, optionally capped at `n` and filtered by length."""
    yielded = 0
    for record in iter_records(source, split, data_dir):
        text = record.get("text", "")
        if len(text) < min_length:
            continue
        yield text
        yielded += 1
        if n is not None and yielded >= n:
            break


def load_texts(
    source: str,
    split: str,
    data_dir: Optional[Path] = None,
    n: Optional[int] = None,
    min_length: int = 0,
) -> List[str]:
    return list(iter_texts(source, split, data_dir, n=n, min_length=min_length))


# ---------------------------------------------------------------------------
# Pairing — index-aligned human vs model
# ---------------------------------------------------------------------------

def iter_paired_texts(
    human_source: str,
    model_source: str,
    split: str,
    data_dir: Optional[Path] = None,
    n: Optional[int] = None,
    min_length: int = 0,
) -> Iterator[Tuple[str, str]]:
    """Yield (human_text, model_text) pairs at the same line index.

    The two corpora are not aligned by content — only by ordinal position.
    That alignment is sufficient for distributional comparison; it is *not*
    sufficient to claim "the model produced this in response to that prompt."
    """
    h = iter_texts(human_source, split, data_dir, min_length=min_length)
    m = iter_texts(model_source, split, data_dir, min_length=min_length)
    yielded = 0
    for human, model in zip(h, m):
        yield human, model
        yielded += 1
        if n is not None and yielded >= n:
            break


# ---------------------------------------------------------------------------
# Equilibrium triples — synthesized prompts + paired completions
# ---------------------------------------------------------------------------

def split_at_word_boundary(text: str, k_words: int) -> Tuple[str, str]:
    """Return (first k words, remainder). Whitespace splitting; no NLP."""
    words = text.split()
    if len(words) <= k_words:
        return text, ""
    prefix = " ".join(words[:k_words])
    suffix = " ".join(words[k_words:])
    return prefix, suffix


def iter_equilibrium_triples(
    human_source: str = "webtext",
    model_source: str = "small-117M-k40",
    split: str = "test",
    k_words: int = 30,
    data_dir: Optional[Path] = None,
    n: Optional[int] = None,
    min_length: int = 200,
) -> Iterator[Tuple[str, str, str]]:
    """Yield (prompt, human_completion, model_completion) triples.

    Prompt = first `k_words` words of the human record.
    human_completion = remainder of the same human record.
    model_completion = the model-side record at the same index, used as a
        stand-in for an aligned generation.

    Records shorter than `min_length` characters are skipped to avoid empty
    completions.
    """
    yielded = 0
    for human, model in iter_paired_texts(
        human_source, model_source, split, data_dir, min_length=min_length,
    ):
        prompt, human_completion = split_at_word_boundary(human, k_words)
        if not human_completion:
            continue
        yield prompt, human_completion, model
        yielded += 1
        if n is not None and yielded >= n:
            break
