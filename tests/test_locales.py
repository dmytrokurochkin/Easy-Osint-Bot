from locales import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, TEXTS, get_text


def test_default_language_is_english():
    assert DEFAULT_LANGUAGE == "en"


def test_supported_languages_are_exactly_en_uk_pl():
    assert set(SUPPORTED_LANGUAGES) == {"en", "uk", "pl"}


def test_every_language_defines_every_key():
    all_keys = set(TEXTS[DEFAULT_LANGUAGE])
    for lang in SUPPORTED_LANGUAGES:
        assert set(TEXTS[lang]) == all_keys, f"{lang} is missing or has extra keys"


def test_get_text_returns_requested_language():
    assert get_text("uk", "choose_action") == "Обери дію:"
    assert get_text("pl", "choose_action") == "Wybierz akcję:"
    assert get_text("en", "choose_action") == "Choose an action:"


def test_get_text_falls_back_to_english_for_unsupported_language():
    assert get_text("fr", "choose_action") == get_text("en", "choose_action")


def test_get_text_falls_back_to_raw_key_when_missing_everywhere():
    assert get_text("en", "no_such_key") == "no_such_key"


def test_get_text_formats_kwargs():
    assert get_text("en", "report_title", query="mrmozozavr") == "OSINT Report: mrmozozavr"
    assert get_text("uk", "report_title", query="mrmozozavr") == "OSINT Звіт: mrmozozavr"
    assert get_text("pl", "report_title", query="mrmozozavr") == "Raport OSINT: mrmozozavr"
