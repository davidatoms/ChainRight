# ChainRight applied to Brain2Text: a letter→word→corpus chain

A plan for using ChainRight's primitives to build a two-layer audit chain
over Brain2Text's decoder output: every decoded character is validated
against NIST handwriting's character dictionary, every assembled word is
validated against the gpt-2-output-dataset pretraining corpus, and both
layers are cryptographically chained so any output is retraceable to the
character recognitions and corpus matches that produced it.

## What exists, briefly

**ChainRight side** (this repo):
- `chainright.blockchain` — append-only chain primitive
- `chainright.provenance` — `chain_corpus_check`, `chain_equilibrium_run`
- `chainright.training_chain` — per-step training-trajectory logging with
  `sha256_text`, `chain_training_step`, `find_step_by_data_hash`
- `chainright.datasets` — gpt-2-output-dataset corpus iteration
- `check_corpus.py` — per-substring membership test against any source

**Brain2Text side** (`G:\My Drive\Brain2Text`):
- A BCI-style phoneme pipeline (T15 copyTask data; `t15_*.pkl` files)
- Phoneme analysis scripts (`scripts/analyze_phoneme_*.py`,
  `scripts/inspect_phonemes.py`)
- Pretraining corpus already on disk: `data/medium-*.jsonl` and
  `data/small-*.jsonl` slices from gpt-2-output-dataset
- `data/rnn_logits/` — decoder output candidates, one of the natural
  hookpoints for the chain
- Phoneme-to-text: `scripts/text_to_phonemes.py`,
  `scripts/process_corpus_to_phonemes*.py`,
  `scripts/phonemize_gpt2_output_dataset.py`

**Missing**:
- NIST handwriting class dictionary (Special Database 19's 62-class label
  set, optionally extended with special-character classes)
- The two-layer chain that ties letter events to word events to corpus
  validation
- The bridge script that consumes Brain2Text's decoder output and produces
  chain blocks

## Two-layer architecture

```
   ┌──────────────────────────────────────────────────────────────┐
   │  Word layer (per-word block)                                 │
   │  fields: word_string, letter_block_indices, corpus_match,    │
   │          first_match_record_index, validity_per_corpus       │
   └────────────────────────┬─────────────────────────────────────┘
                            │ references via block_index
                            ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  Letter layer (per-character block)                          │
   │  fields: timestamp, predicted_class, confidence,             │
   │          raw_signal_hash, validity_per_nist_dictionary       │
   └──────────────────────────────────────────────────────────────┘
```

Letters are written to the chain as they're decoded. Words are written
when a word-boundary is detected (whitespace, punctuation, or end of
utterance). Each word block carries a list of pointers (block indices)
back to the letter blocks that composed it.

## Data sources

### NIST handwriting class dictionary (the letter-layer oracle)

**NIST Special Database 19** (the user's "training set for NIST
handwriting") provides hand-printed character data with a 62-class label
set:

- 10 digit classes: `0`–`9`
- 26 uppercase classes: `A`–`Z`
- 26 lowercase classes: `a`–`z`

This is what the user calls "their dictionary on numbers, letters." For
"special characters," NIST SD 19 does not include them by default; the
plan extends the dictionary with a small caller-defined set:

- whitespace: ` `
- common punctuation: `. , ! ? ; : ' " - ( )`
- (extensible per Brain2Text's actual output alphabet)

The dictionary is just a Python `set[str]` of legal characters. The
chain block for a letter records `validity_per_nist_dictionary = True`
iff the predicted class is in this set.

### Pretraining corpus (the word-layer oracle)

Brain2Text already has `data/medium-117M-k40.train.jsonl`,
`data/small-*.jsonl`, etc. — these are gpt-2-output-dataset slices. They
serve as the pretraining-corpus reference. A word is "validated" if it
appears as a substring in any of these slices, using
`chainright.check_corpus.check_membership` exactly as we already use it
for the MNPI absence-attestation primitive.

This reuses the corpus iteration code already in `chainright.datasets`,
just pointed at Brain2Text's local data directory via the existing
`--data-dir` flag.

## Chain primitives needed

Most of what's needed is already in the repo. Two new modules give the
specific block shapes:

### `src/chainright/brain2text_chain.py` (new)

```python
@dataclass
class LetterEventRecord:
    timestamp: str          # ISO UTC
    predicted_class: str    # one character
    confidence: float       # decoder's softmax probability
    raw_signal_hash: str    # sha256 of the BCI window or image bytes
    nist_class_set_id: str  # which version of the dictionary was applied

def chain_letter_event(
    blockchain: Blockchain,
    record: LetterEventRecord,
    nist_dictionary: Set[str],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Append one letter-recognition event to the chain.

    The block payload includes `validity_per_nist_dictionary`, computed
    by checking `record.predicted_class in nist_dictionary`.
    """

@dataclass
class WordEventRecord:
    timestamp: str
    word_string: str
    letter_block_indices: List[int]   # pointers to letter-layer blocks
    confidence_min: float             # min over composing letters
    confidence_mean: float

def chain_word_event(
    blockchain: Blockchain,
    record: WordEventRecord,
    corpus_check_fn: Callable[[str], Dict[str, Any]],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Append one word-assembly event. `corpus_check_fn` returns the
    corpus-membership result (substring match across one or more
    sources), and the result is embedded in the block payload."""
```

### `src/chainright/nist_dictionary.py` (new)

A trivial helper module that exposes the SD 19 62-class set plus the
optional extensions:

```python
NIST_SD19_DIGITS = set("0123456789")
NIST_SD19_UPPERCASE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
NIST_SD19_LOWERCASE = set("abcdefghijklmnopqrstuvwxyz")
NIST_SD19_BASE = NIST_SD19_DIGITS | NIST_SD19_UPPERCASE | NIST_SD19_LOWERCASE
COMMON_SPECIAL = set(" .,!?;:'\"-()")

def default_dictionary(include_special: bool = True) -> Set[str]:
    return NIST_SD19_BASE | (COMMON_SPECIAL if include_special else set())

def dictionary_id(d: Set[str]) -> str:
    """Hash of the sorted dictionary, so chain blocks can certify which
    version of the alphabet was applied."""
```

A regulator with a chain block sees `nist_class_set_id = sha256(...)`
and can confirm exactly which alphabet the validator used.

## Validation pipeline

Per Brain2Text decoded utterance:

```
for character_event in decoder_output:
    block_idx = chain_letter_event(
        chain,
        LetterEventRecord(
            timestamp=now_utc(),
            predicted_class=character_event.char,
            confidence=character_event.softmax_prob,
            raw_signal_hash=sha256(character_event.signal_window),
            nist_class_set_id=DICT_ID,
        ),
        nist_dictionary=NIST_SD19_BASE | COMMON_SPECIAL,
        session_id=utterance_id,
    )
    pending_letter_blocks.append(block_idx)
    if character_event.char in WORD_BOUNDARY_CHARS:
        word = "".join(decode_buffer)
        chain_word_event(
            chain,
            WordEventRecord(
                timestamp=now_utc(),
                word_string=word,
                letter_block_indices=pending_letter_blocks[:-1],
                confidence_min=min_confidence(pending_letter_blocks[:-1]),
                confidence_mean=mean_confidence(pending_letter_blocks[:-1]),
            ),
            corpus_check_fn=lambda w: check_membership(
                w, source="webtext", split="train",
                data_dir=Path("/g/My Drive/Brain2Text/data"),
            ),
            session_id=utterance_id,
        )
        pending_letter_blocks = []
```

End of utterance flushes any remaining letter blocks into a final word
block. Punctuation can either close a word or stand on its own — the
plan supports both via the `WORD_BOUNDARY_CHARS` set.

## Integration with Brain2Text scripts

Specific Brain2Text scripts that should consume or feed the chain:

| Brain2Text script | How it interacts with the chain |
|---|---|
| `analyze_lexicon.py` | Read the chain after a session; report distribution of word-block validation rates per pretraining corpus |
| `analyze_phoneme_distributions.py` | Cross-reference per-letter chain blocks with phoneme decisions; count where the phoneme→letter map produced an out-of-NIST class |
| `phonemize_gpt2_output_dataset.py` | Already produces the corpus side of the chain; ensure the data hashes used here match the hashes the chain would record |
| `process_corpus_to_phonemes*.py` | Same — the corpus hashes are the audit anchor for word-layer validation |
| `inspect_phonemes.py` | Could be augmented to include "which words I'm decoding actually appear in the pretraining corpus" |
| `analyze_kmeans_clustering.py` | The chain provides session-level confidence stats per cluster; orthogonal but useful |

A single new bridge script ties this together:

**`scripts/chain_decoder_output.py`** (in Brain2Text/scripts/) —
consumes `data/rnn_logits/` (Brain2Text's existing decoder output
directory) and produces a `chain.json` per session.

## Concrete implementation steps

1. **New ChainRight modules** (in this repo):
   - `src/chainright/nist_dictionary.py` (~30 lines, no deps).
   - `src/chainright/brain2text_chain.py` (~120 lines, depends only on
     `chainright.blockchain` and `chainright.provenance`).
   - `tests/test_brain2text_chain.py` covering: letter-event payload
     fields, word-event with letter_block_indices, dictionary lookups,
     chain integrity across many letter+word events.

2. **Brain2Text bridge script** (write into Brain2Text/scripts/, not
   here):
   - `scripts/chain_decoder_output.py` reads
     `data/rnn_logits/{session}.npy` (or however the decoder writes
     candidates), iterates per-character recognition events, calls the
     ChainRight helpers above, emits `runs/chain_<session>.json`.
   - One-shot per session, no streaming required for first cut.

3. **Pretraining corpus pointer**: Brain2Text's `data/` directory
   already contains the gpt-2-output-dataset slices. Set
   `chainright.datasets.default_data_dir()` to find them via the
   `GPT2_OUTPUT_DATASET_DIR` environment variable
   (`G:\My Drive\Brain2Text\data`), so the corpus check works
   without copying data.

4. **Reporting layer**: extend `examples/` in this repo with
   `examples/brain2text_chain_audit.py` that reads a session chain and
   reports:
   - Per-letter NIST-validity rate
   - Per-word corpus-validity rate
   - Confidence-conditional accuracy (does low-confidence chain better
     correlate with corpus-invalid words?)
   - Top-K most frequently corpus-validated words
   - Top-K most frequently corpus-invalid words (likely decoder
     hallucinations)

## Testable hypotheses (paper-shaped)

Following the H1-H9 style in `reports/hypotheses_to_test.md`:

**HB1 — NIST-validity rate is a quality-floor indicator.**
Brain2Text's decoder is constrained to produce characters in the NIST
dictionary; the per-letter chain should show ≥99% validity unless the
decoder is broken. Falsifier: validity rate < 90% on a healthy session.

**HB2 — Word-level corpus membership rate distinguishes
in-distribution from out-of-distribution sessions.** On T15
copy-task data (the user is reproducing known sentences), the
word-corpus-validation rate should be substantially higher than on
free-form generation. Falsifier: rate is invariant across copy-task
vs. free-generation sessions.

**HB3 — Confidence-conditional corpus validity.** Words assembled
from low-mean-confidence letter chains should have a lower corpus-
match rate than high-confidence words. Falsifier: confidence
correlates poorly with corpus validity.

**HB4 — Per-character chain throughput is BCI-real-time-feasible.**
The chain at difficulty=1 should be able to mine 50+ letter blocks
per second on a 3070 Ti's CPU. Falsifier: throughput < 10 letters/s
forces difficulty=0 (no proof-of-work) for live deployment, which is
acceptable but should be measured.

**HB5 — Two-layer audit composes.** A regulator with the session
chain can independently:
  (a) Verify each letter event against the NIST dictionary id.
  (b) Verify each word event against the gpt-2-output-dataset slice.
  (c) Walk word blocks back to letter blocks via the index pointers
      and confirm composition consistency.
Falsifier: any of the three audit paths fails on healthy session
data.

## Risks and open questions

1. **Word-boundary detection.** Brain2Text's decoder may not emit
   spaces explicitly — phonemes assemble into utterance text without
   reliable word boundaries. The plan needs the bridge script to
   reconstruct boundaries (whitespace heuristic, or use the phoneme
   pipeline's existing word segmentation). If word boundaries are
   unreliable, the word layer becomes noisy.

2. **Corpus path canonicalization.** Brain2Text's `data/` has the
   medium and small dataset slices but possibly not webtext. If
   Brain2Text doesn't have webtext locally, the chain can either
   reference our existing webtext download in
   `gpt-2-output-dataset/data/` or the bridge script can look for
   either path.

3. **NIST dictionary fidelity.** The 62-class SD 19 set is exact for
   handwriting recognition; for BCI decoding, Brain2Text may emit a
   different alphabet (phoneme-derived characters can include
   IPA-like extensions). The dictionary may need to be the
   *intersection* of NIST SD 19 and Brain2Text's emitted alphabet, or
   a Brain2Text-specific extension certified separately.

4. **Per-character signal hash.** `raw_signal_hash` references the
   neural input window that produced the character. Brain2Text's
   pipeline may not surface that window directly — the bridge script
   may need to hash a session-level identifier plus the time index
   instead, which weakens the cryptographic anchor but stays
   workable.

5. **Chain throughput at session scale.** A 30-minute T15 session
   might produce 10⁴ letter events. At difficulty=1 with PoW, that's
   ~3 minutes of mining overhead. For research workloads this is
   fine; for production it's worth using difficulty=0 (no PoW) since
   the cryptographic continuity matters more than the proof-of-work.

## What this plan would let Brain2Text claim

The integration would let Brain2Text say, of any decoded utterance:

> *Each character was a recognition event in the NIST SD 19 character
> set (or its certified extension), with its confidence, signal hash,
> and dictionary-validity recorded. Each word was assembled from the
> recorded letters and validated against the pretraining corpus
> (gpt-2-output-dataset webtext slice). The full session chain
> certifies both layers; an auditor can independently verify that
> any reported word came from the recorded letters and that the
> letters came from the recorded signals — without re-running the
> decoder.*

That's the audit shape Brain2Text doesn't currently have, and it's
exactly the integration of ChainRight's primitives the user has been
building toward in the financial-services context, transferred to
brain-decoded text.

## Where to put the plan and which scripts to write next

1. **This file**: `notes/brain2text_letter_word_chain.md` —
   conceptual home in ChainRight, parallel to the other four notes.
2. **Suggested copy** in Brain2Text: paste this file as
   `G:\My Drive\Brain2Text\docs\chainright_integration_plan.md` (not
   created automatically — write requires confirmation since the
   path is on a Google Drive mount).
3. **Next code commits** in ChainRight (in order):
   - `src/chainright/nist_dictionary.py`
   - `src/chainright/brain2text_chain.py`
   - `tests/test_brain2text_chain.py`
4. **Next code commit** in Brain2Text:
   - `scripts/chain_decoder_output.py` — the bridge.

If you want me to land any of these now, say which.
