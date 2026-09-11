from handlers import start


def test_user_reports_is_capped_at_max_reports_shown(tmp_path, monkeypatch):
    monkeypatch.setattr(start, "REPORTS_DIR", tmp_path)
    user_dir = tmp_path / "42"
    user_dir.mkdir()
    for i in range(30):
        (user_dir / f"2024010{i:02d}_000000_query.html").write_text("x", encoding="utf-8")

    reports = start._user_reports(42)

    assert len(reports) == start.MAX_REPORTS_SHOWN


def test_user_reports_returns_empty_list_when_no_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(start, "REPORTS_DIR", tmp_path)
    assert start._user_reports(999) == []
