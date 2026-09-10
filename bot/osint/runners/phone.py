import phonenumbers
from phonenumbers import carrier, geocoder, timezone

from bot.osint.types import ToolResult

LINE_TYPE_NAMES = {
    phonenumbers.PhoneNumberType.MOBILE: "mobile",
    phonenumbers.PhoneNumberType.FIXED_LINE: "fixed_line",
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_line_or_mobile",
    phonenumbers.PhoneNumberType.TOLL_FREE: "toll_free",
    phonenumbers.PhoneNumberType.PREMIUM_RATE: "premium_rate",
    phonenumbers.PhoneNumberType.SHARED_COST: "shared_cost",
    phonenumbers.PhoneNumberType.VOIP: "voip",
    phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "personal_number",
    phonenumbers.PhoneNumberType.PAGER: "pager",
    phonenumbers.PhoneNumberType.UAN: "uan",
    phonenumbers.PhoneNumberType.UNKNOWN: "unknown",
}


def get_phone_result(query: str) -> ToolResult:
    try:
        number = phonenumbers.parse(query, None)
    except phonenumbers.NumberParseException:
        return ToolResult(tool="phone", status="failed", error="Не вдалося розпізнати номер")

    if not phonenumbers.is_valid_number(number):
        return ToolResult(tool="phone", status="failed", error="Номер невалідний")

    region = geocoder.description_for_number(number, "en") or "невідомо"
    carrier_name = carrier.name_for_number(number, "en") or "невідомо"
    line_type = LINE_TYPE_NAMES.get(phonenumbers.number_type(number), "unknown")
    timezones = ", ".join(timezone.time_zones_for_number(number)) or "невідомо"

    items = [
        {"label": "Країна", "value": f"+{number.country_code}"},
        {"label": "Регіон", "value": region},
        {"label": "Оператор", "value": carrier_name},
        {"label": "Тип лінії", "value": line_type},
        {"label": "Часові пояси", "value": timezones},
    ]
    return ToolResult(tool="phone", status="ok", items=items)
