from chainright.tokenization import build_tokenization_report


def test_build_tokenization_report_multiple_views():
    report = build_tokenization_report("Hello, world! This is ChainRight.")

    view_names = [view.name for view in report.views]

    assert "characters" in view_names
    assert "whitespace" in view_names
    assert "words_and_punctuation" in view_names
    assert "sentences" in view_names
    assert "utf8_bytes" in view_names

    words_view = next(view for view in report.views if view.name == "words_and_punctuation")
    assert words_view.tokens == ["Hello", ",", "world", "!", "This", "is", "ChainRight", "."]
