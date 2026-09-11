import re

import phonenumbers

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{2,32}$")


def detect_query_type(text: str) -> str | None:
    text = text.strip()
    if not text:
        return None

    if EMAIL_RE.match(text):
        return "email"

    if text.startswith("+"):
        try:
            number = phonenumbers.parse(text, None)
            if phonenumbers.is_valid_number(number):
                return "phone"
        except phonenumbers.NumberParseException:
            pass

    if USERNAME_RE.match(text):
        return "username"

    return None
