"""Tests for chainright.character_dictionary and chainright.brain2text_chain."""

import pytest

from chainright.blockchain import Blockchain
from chainright.brain2text_chain import (
    LetterEventRecord,
    WordEventRecord,
    assemble_word_record,
    chain_letter_event,
    chain_word_event,
    session_summary,
)
from chainright.character_dictionary import (
    BASIC_LATIN,
    COMMON_SPECIAL,
    DIGITS,
    LOWERCASE_LATIN,
    UPPERCASE_LATIN,
    coverage_report,
    default_dictionary,
    dictionary_id,
    is_valid_class,
)


# ---------------------------------------------------------------------------
# character_dictionary
# ---------------------------------------------------------------------------

class TestCharacterDictionary:
    def test_base_set_size(self):
        assert len(DIGITS) == 10
        assert len(UPPERCASE_LATIN) == 26
        assert len(LOWERCASE_LATIN) == 26
        assert len(BASIC_LATIN) == 62

    def test_classes_are_disjoint(self):
        assert DIGITS.isdisjoint(UPPERCASE_LATIN)
        assert UPPERCASE_LATIN.isdisjoint(LOWERCASE_LATIN)
        assert DIGITS.isdisjoint(LOWERCASE_LATIN)

    def test_default_dictionary_with_special(self):
        d = default_dictionary(include_special=True)
        assert BASIC_LATIN.issubset(d)
        assert COMMON_SPECIAL.issubset(d)
        assert " " in d

    def test_default_dictionary_without_special(self):
        d = default_dictionary(include_special=False)
        assert d == BASIC_LATIN
        assert " " not in d

    def test_dictionary_id_deterministic(self):
        assert dictionary_id(default_dictionary()) == dictionary_id(default_dictionary())
        assert len(dictionary_id(default_dictionary())) == 64

    def test_dictionary_id_changes_with_content(self):
        a = BASIC_LATIN
        b = BASIC_LATIN | {"@"}
        assert dictionary_id(a) != dictionary_id(b)

    def test_dictionary_id_order_independent(self):
        d1 = set("ABC0123")
        d2 = set("3210CBA")
        assert dictionary_id(d1) == dictionary_id(d2)

    def test_is_valid_class(self):
        d = default_dictionary()
        assert is_valid_class("A", d)
        assert is_valid_class("z", d)
        assert is_valid_class("0", d)
        assert is_valid_class(" ", d)
        assert not is_valid_class("ñ", d)
        assert not is_valid_class("AB", d)
        assert not is_valid_class("", d)

    def test_coverage_report_full_match(self):
        d = default_dictionary()
        report = coverage_report("Hello, World!", d)
        assert report["total_chars"] == 13
        assert report["in_dictionary"] == 13
        assert report["coverage_rate"] == 1.0
        assert report["out_of_dict_chars"] == []

    def test_coverage_report_partial(self):
        d = BASIC_LATIN
        report = coverage_report("Hello!", d)
        assert report["in_dictionary"] == 5
        assert report["out_of_dictionary"] == 1
        assert report["out_of_dict_chars"] == ["!"]
        assert report["coverage_rate"] == pytest.approx(5 / 6)

    def test_coverage_report_empty_text(self):
        report = coverage_report("", default_dictionary())
        assert report["total_chars"] == 0
        assert report["coverage_rate"] == 0.0


class TestNistHandwritingPackage:
    """The NIST package re-aliases the basic Latin set for self-documenting
    chain blocks. Its values must equal the character_dictionary base."""

    def test_sd19_aliases_match_character_dictionary(self):
        from chainright.nist_handwriting import (
            SD19_BASE, SD19_DIGITS, SD19_LOWERCASE, SD19_UPPERCASE,
        )
        assert SD19_DIGITS == DIGITS
        assert SD19_UPPERCASE == UPPERCASE_LATIN
        assert SD19_LOWERCASE == LOWERCASE_LATIN
        assert SD19_BASE == BASIC_LATIN

    def test_sd19_dictionary_returns_62_classes(self):
        from chainright.nist_handwriting import sd19_dictionary
        d = sd19_dictionary()
        assert len(d) == 62
        assert d == BASIC_LATIN
        # Returns a fresh set — mutations don't leak.
        d.add("@")
        assert "@" not in sd19_dictionary()


# ---------------------------------------------------------------------------
# Letter layer
# ---------------------------------------------------------------------------

class TestChainLetterEvent:
    def test_valid_letter_appends(self):
        bc = Blockchain(difficulty=1)
        result = chain_letter_event(
            bc,
            LetterEventRecord(
                predicted_class="H",
                confidence=0.95,
                raw_signal_hash="a" * 64,
            ),
            character_dictionary=default_dictionary(),
        )
        assert result["valid"] is True
        assert result["block_index"] == 1
        assert result["payload"]["validity_per_character_dictionary"] is True
        assert result["payload"]["predicted_class"] == "H"
        assert result["payload"]["confidence"] == 0.95

    def test_invalid_letter_recorded_with_false_validity(self):
        bc = Blockchain(difficulty=1)
        result = chain_letter_event(
            bc,
            LetterEventRecord(
                predicted_class="ñ",
                confidence=0.5,
                raw_signal_hash="b" * 64,
            ),
            character_dictionary=default_dictionary(),
        )
        assert result["valid"] is False
        assert result["payload"]["validity_per_character_dictionary"] is False

    def test_dictionary_id_in_payload(self):
        bc = Blockchain(difficulty=1)
        d = default_dictionary()
        result = chain_letter_event(
            bc,
            LetterEventRecord(
                predicted_class="A",
                confidence=0.9,
                raw_signal_hash="c" * 64,
            ),
            character_dictionary=d,
        )
        assert result["payload"]["character_set_id"] == dictionary_id(d)

    def test_chain_remains_valid_across_many_letter_events(self):
        bc = Blockchain(difficulty=1)
        d = default_dictionary()
        for ch in "Hello, World":
            chain_letter_event(
                bc,
                LetterEventRecord(predicted_class=ch, confidence=0.8, raw_signal_hash="x" * 64),
                character_dictionary=d,
            )
        assert bc.is_chain_valid()
        assert len(bc.chain) == 13

    def test_session_id_propagates(self):
        bc = Blockchain(difficulty=1)
        result = chain_letter_event(
            bc,
            LetterEventRecord(predicted_class="A", confidence=0.9, raw_signal_hash="a" * 64),
            character_dictionary=default_dictionary(),
            session_id="t15-001",
        )
        assert result["payload"]["session_id"] == "t15-001"


# ---------------------------------------------------------------------------
# Word layer
# ---------------------------------------------------------------------------

def _mock_corpus_check(present: bool, source: str = "webtext", split: str = "test"):
    def fn(_word: str):
        return {
            "present": present,
            "first_match_record_index": 142 if present else None,
            "source": source,
            "split": split,
        }
    return fn


class TestChainWordEvent:
    def test_word_event_with_corpus_match(self):
        bc = Blockchain(difficulty=1)
        result = chain_word_event(
            bc,
            WordEventRecord(
                word_string="hello",
                letter_block_indices=[1, 2, 3, 4, 5],
                confidence_min=0.8,
                confidence_mean=0.9,
            ),
            corpus_check_fn=_mock_corpus_check(present=True),
        )
        assert result["corpus_match"] is True
        assert result["payload"]["word_string"] == "hello"
        assert result["payload"]["word_length"] == 5
        assert result["payload"]["letter_block_indices"] == [1, 2, 3, 4, 5]
        assert result["payload"]["corpus_first_match_record_index"] == 142
        assert result["payload"]["corpus_source"] == "webtext"
        assert result["payload"]["confidence_min"] == 0.8
        assert result["payload"]["confidence_mean"] == 0.9

    def test_word_event_without_corpus_match(self):
        bc = Blockchain(difficulty=1)
        result = chain_word_event(
            bc,
            WordEventRecord(word_string="zxqvw", letter_block_indices=[1, 2, 3, 4, 5]),
            corpus_check_fn=_mock_corpus_check(present=False),
        )
        assert result["corpus_match"] is False
        assert result["payload"]["corpus_first_match_record_index"] is None


class TestAssembleWordRecord:
    def test_assembles_from_letter_blocks(self):
        letter_infos = [
            {"block_index": 1, "payload": {"predicted_class": "h", "confidence": 0.9}},
            {"block_index": 2, "payload": {"predicted_class": "i", "confidence": 0.8}},
        ]
        record = assemble_word_record(letter_infos)
        assert record.word_string == "hi"
        assert record.letter_block_indices == [1, 2]
        assert record.confidence_min == 0.8
        assert record.confidence_mean == pytest.approx(0.85)

    def test_assemble_handles_empty_list(self):
        record = assemble_word_record([])
        assert record.word_string == ""
        assert record.letter_block_indices == []
        assert record.confidence_min is None
        assert record.confidence_mean is None


# ---------------------------------------------------------------------------
# Session summary
# ---------------------------------------------------------------------------

class TestSessionSummary:
    def _populate(self, bc, letters, words, session_id="s1"):
        for char, valid_dict in letters:
            d = {char} if valid_dict else set()
            chain_letter_event(
                bc,
                LetterEventRecord(predicted_class=char, confidence=0.8, raw_signal_hash="x" * 64),
                character_dictionary=d,
                session_id=session_id,
            )
        for word, match in words:
            chain_word_event(
                bc,
                WordEventRecord(word_string=word, letter_block_indices=[]),
                corpus_check_fn=_mock_corpus_check(present=match),
                session_id=session_id,
            )

    def test_aggregates_letter_and_word_counts(self):
        bc = Blockchain(difficulty=1)
        self._populate(
            bc,
            letters=[("h", True), ("i", True), ("ñ", False)],
            words=[("hi", True), ("xyz", False)],
        )
        summary = session_summary(bc, session_id="s1")
        assert summary["letter_events"] == 3
        assert summary["letter_valid_count"] == 2
        assert summary["letter_validity_rate"] == pytest.approx(2 / 3)
        assert summary["word_events"] == 2
        assert summary["word_corpus_match_count"] == 1
        assert summary["word_corpus_match_rate"] == 0.5

    def test_filters_by_session_id(self):
        bc = Blockchain(difficulty=1)
        self._populate(bc, [("h", True)], [("hi", True)], session_id="s1")
        self._populate(bc, [("y", True)], [("yo", False)], session_id="s2")
        s1 = session_summary(bc, session_id="s1")
        s2 = session_summary(bc, session_id="s2")
        assert s1["letter_events"] == 1
        assert s2["letter_events"] == 1
        assert s1["word_corpus_match_rate"] == 1.0
        assert s2["word_corpus_match_rate"] == 0.0

    def test_records_out_of_dict_chars(self):
        bc = Blockchain(difficulty=1)
        self._populate(
            bc,
            letters=[("@", False), ("#", False), ("h", True)],
            words=[],
        )
        summary = session_summary(bc, session_id="s1")
        assert "@" in summary["out_of_dict_chars_seen"]
        assert "#" in summary["out_of_dict_chars_seen"]

    def test_empty_chain_summary(self):
        bc = Blockchain(difficulty=1)
        summary = session_summary(bc)
        assert summary["letter_events"] == 0
        assert summary["word_events"] == 0
        assert summary["letter_validity_rate"] == 0.0
        assert summary["word_corpus_match_rate"] == 0.0
