"""Tests for chainright.phoneme — phoneme dictionary + per-frame chain."""

import pytest

from chainright.blockchain import Blockchain
from chainright.phoneme import (
    ARPABET_BLANK,
    ARPABET_PHONEMES,
    ARPABET_SILENCE,
    PhonemeEventRecord,
    chain_phoneme_event,
    default_phoneme_set,
    is_valid_phoneme,
    phoneme_session_summary,
    phoneme_set_id,
)


# ---------------------------------------------------------------------------
# phoneme_dictionary
# ---------------------------------------------------------------------------

class TestPhonemeDictionary:
    def test_arpabet_size(self):
        assert len(ARPABET_PHONEMES) == 39

    def test_arpabet_contains_canonical_phonemes(self):
        # Spot-check a few well-known phonemes from each category.
        for p in ("AA", "AE", "AH", "B", "CH", "ZH", "NG"):
            assert p in ARPABET_PHONEMES

    def test_default_with_blank_and_silence(self):
        d = default_phoneme_set(include_blank=True, include_silence=True)
        assert len(d) == 41
        assert ARPABET_BLANK in d
        assert ARPABET_SILENCE in d

    def test_default_without_blank_silence(self):
        d = default_phoneme_set(include_blank=False, include_silence=False)
        assert d == ARPABET_PHONEMES
        assert ARPABET_BLANK not in d
        assert ARPABET_SILENCE not in d

    def test_phoneme_set_id_deterministic(self):
        assert phoneme_set_id(default_phoneme_set()) == phoneme_set_id(default_phoneme_set())
        assert len(phoneme_set_id(default_phoneme_set())) == 64

    def test_phoneme_set_id_order_independent(self):
        a = {"AA", "AE", "B"}
        b = {"B", "AE", "AA"}
        assert phoneme_set_id(a) == phoneme_set_id(b)

    def test_phoneme_set_id_changes_with_content(self):
        a = ARPABET_PHONEMES
        b = ARPABET_PHONEMES | {"<NEW>"}
        assert phoneme_set_id(a) != phoneme_set_id(b)

    def test_multi_char_tokens_dont_collide_with_concatenation(self):
        # 'AA' + 'BB' could collide with 'AABB' under naive concatenation.
        # Null-byte joiner in phoneme_set_id should prevent that.
        a = {"AA", "BB"}
        b = {"AABB"}
        assert phoneme_set_id(a) != phoneme_set_id(b)

    def test_is_valid_phoneme(self):
        d = default_phoneme_set()
        assert is_valid_phoneme("AA", d)
        assert is_valid_phoneme("ZH", d)
        assert is_valid_phoneme(ARPABET_BLANK, d)
        assert not is_valid_phoneme("XX", d)
        assert not is_valid_phoneme("", d)
        assert not is_valid_phoneme(None, d)


# ---------------------------------------------------------------------------
# phoneme_chain
# ---------------------------------------------------------------------------

class TestChainPhonemeEvent:
    def test_valid_phoneme_appends(self):
        bc = Blockchain(difficulty=1)
        result = chain_phoneme_event(
            bc,
            PhonemeEventRecord(
                predicted_phoneme="AA",
                confidence=0.92,
                raw_signal_hash="a" * 64,
                frame_index=0,
            ),
            phoneme_set=default_phoneme_set(),
        )
        assert result["valid"] is True
        assert result["block_index"] == 1
        assert result["payload"]["validity_per_phoneme_set"] is True
        assert result["payload"]["predicted_phoneme"] == "AA"
        assert result["payload"]["frame_index"] == 0

    def test_invalid_phoneme_recorded(self):
        bc = Blockchain(difficulty=1)
        result = chain_phoneme_event(
            bc,
            PhonemeEventRecord(
                predicted_phoneme="XYZ",
                confidence=0.4,
                raw_signal_hash="b" * 64,
            ),
            phoneme_set=default_phoneme_set(),
        )
        assert result["valid"] is False
        assert result["payload"]["validity_per_phoneme_set"] is False

    def test_phoneme_set_id_in_payload(self):
        bc = Blockchain(difficulty=1)
        d = default_phoneme_set()
        result = chain_phoneme_event(
            bc,
            PhonemeEventRecord(
                predicted_phoneme="K",
                confidence=0.85,
                raw_signal_hash="c" * 64,
            ),
            phoneme_set=d,
        )
        assert result["payload"]["phoneme_set_id"] == phoneme_set_id(d)

    def test_chain_remains_valid_across_a_full_word(self):
        bc = Blockchain(difficulty=1)
        d = default_phoneme_set()
        # /K AE T/ — "cat"
        for i, p in enumerate(["K", "AE", "T"]):
            chain_phoneme_event(
                bc,
                PhonemeEventRecord(
                    predicted_phoneme=p,
                    confidence=0.9,
                    raw_signal_hash="x" * 64,
                    frame_index=i,
                ),
                phoneme_set=d,
                session_id="utterance-001",
            )
        assert bc.is_chain_valid()
        assert len(bc.chain) == 4


class TestPhonemeSessionSummary:
    def _populate(self, bc, events, session_id="utt-1"):
        d = default_phoneme_set()
        for i, (phoneme, valid) in enumerate(events):
            chain_phoneme_event(
                bc,
                PhonemeEventRecord(
                    predicted_phoneme=phoneme,
                    confidence=0.8 if valid else 0.3,
                    raw_signal_hash="x" * 64,
                    frame_index=i,
                ),
                phoneme_set=(d if valid else {phoneme} - d),
                session_id=session_id,
            )

    def test_aggregates_validity_and_confidence(self):
        bc = Blockchain(difficulty=1)
        # 3 valid (AA, AE, B) + 1 invalid (made-up "XX")
        chain_phoneme_event(
            bc, PhonemeEventRecord("AA", 0.9, "x" * 64),
            phoneme_set=default_phoneme_set(), session_id="s1",
        )
        chain_phoneme_event(
            bc, PhonemeEventRecord("AE", 0.85, "x" * 64),
            phoneme_set=default_phoneme_set(), session_id="s1",
        )
        chain_phoneme_event(
            bc, PhonemeEventRecord("B", 0.95, "x" * 64),
            phoneme_set=default_phoneme_set(), session_id="s1",
        )
        chain_phoneme_event(
            bc, PhonemeEventRecord("XX", 0.2, "x" * 64),
            phoneme_set=default_phoneme_set(), session_id="s1",
        )
        summary = phoneme_session_summary(bc, session_id="s1")
        assert summary["phoneme_events"] == 4
        assert summary["phoneme_valid_count"] == 3
        assert summary["phoneme_validity_rate"] == pytest.approx(0.75)
        assert "XX" in summary["out_of_set_phonemes_seen"]
        assert summary["mean_phoneme_confidence"] == pytest.approx((0.9 + 0.85 + 0.95 + 0.2) / 4)

    def test_filters_by_session_id(self):
        bc = Blockchain(difficulty=1)
        chain_phoneme_event(
            bc, PhonemeEventRecord("AA", 0.9, "x" * 64),
            phoneme_set=default_phoneme_set(), session_id="utt-a",
        )
        chain_phoneme_event(
            bc, PhonemeEventRecord("AE", 0.85, "x" * 64),
            phoneme_set=default_phoneme_set(), session_id="utt-b",
        )
        a = phoneme_session_summary(bc, session_id="utt-a")
        b = phoneme_session_summary(bc, session_id="utt-b")
        assert a["phoneme_events"] == 1
        assert b["phoneme_events"] == 1

    def test_empty_chain(self):
        bc = Blockchain(difficulty=1)
        summary = phoneme_session_summary(bc)
        assert summary["phoneme_events"] == 0
        assert summary["phoneme_validity_rate"] == 0.0
