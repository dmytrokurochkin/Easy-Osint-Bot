import pytest
from bot.osint.detect import detect_query_type


@pytest.mark.parametrize(
    "text,expected",
    [
        ("+380501234567", "phone"),
        ("+14155552671", "phone"),
        ("test@example.com", "email"),
        ("mrmozozavr", "username"),
        ("mrmozozavr_08.30", "username"),
        ("", None),
        ("   ", None),
        ("not a valid query!!", None),
        ("@", None),
    ],
)
def test_detect_query_type(text, expected):
    assert detect_query_type(text) == expected
