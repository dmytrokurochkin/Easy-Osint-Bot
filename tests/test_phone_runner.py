from bot.osint.runners.phone import get_phone_result


def test_valid_ukrainian_mobile_number():
    result = get_phone_result("+380671234567")
    assert result.tool == "phone"
    assert result.status == "ok"
    labels = {item["label"] for item in result.items}
    assert {"Країна", "Регіон", "Оператор", "Тип лінії", "Часові пояси"} <= labels
    country_item = next(i for i in result.items if i["label"] == "Країна")
    assert country_item["value"] == "+380"


def test_invalid_number_returns_failed():
    result = get_phone_result("+10000000")
    assert result.tool == "phone"
    assert result.status == "failed"
    assert result.error


def test_garbage_input_does_not_raise():
    result = get_phone_result("not-a-number-at-all")
    assert result.status == "failed"
