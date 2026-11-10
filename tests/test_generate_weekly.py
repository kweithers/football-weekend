import json
import pytest


@pytest.fixture()
def empty_weekends_file(tmp_path, monkeypatch):
    """Redirect EMPTY_WEEKENDS_FILE to a temp path."""
    import generate_weekly
    path = str(tmp_path / "empty_weekends.json")
    monkeypatch.setattr(generate_weekly, "EMPTY_WEEKENDS_FILE", path)
    return path


class TestSetEmptyWeekend:
    def test_creates_file_if_missing(self, empty_weekends_file):
        from generate_weekly import set_empty_weekend
        entry = {"type": "break", "message": "International break."}
        set_empty_weekend("2026-10-31", entry)
        with open(empty_weekends_file) as f:
            data = json.load(f)
        assert data["2026-10-31"] == entry

    def test_adds_to_existing_file(self, empty_weekends_file):
        from generate_weekly import set_empty_weekend
        existing = {"2026-11-07": {"type": "break", "message": "Winter break."}}
        with open(empty_weekends_file, "w") as f:
            json.dump(existing, f)

        set_empty_weekend("2026-10-31", {"type": "error", "message": "Oops."})

        with open(empty_weekends_file) as f:
            data = json.load(f)
        assert "2026-11-07" in data  # existing entry preserved
        assert "2026-10-31" in data

    def test_remove_date_with_none(self, empty_weekends_file):
        from generate_weekly import set_empty_weekend
        initial = {"2026-10-31": {"type": "break", "message": "Break."}}
        with open(empty_weekends_file, "w") as f:
            json.dump(initial, f)

        set_empty_weekend("2026-10-31", None)

        with open(empty_weekends_file) as f:
            data = json.load(f)
        assert "2026-10-31" not in data

    def test_remove_nonexistent_date_is_noop(self, empty_weekends_file):
        from generate_weekly import set_empty_weekend
        initial = {"2026-11-07": {"type": "break", "message": "Break."}}
        with open(empty_weekends_file, "w") as f:
            json.dump(initial, f)

        set_empty_weekend("2026-10-31", None)  # date not in file

        with open(empty_weekends_file) as f:
            data = json.load(f)
        assert data == initial  # unchanged

    def test_overwrites_existing_entry(self, empty_weekends_file):
        from generate_weekly import set_empty_weekend
        initial = {"2026-10-31": {"type": "break", "message": "Old message."}}
        with open(empty_weekends_file, "w") as f:
            json.dump(initial, f)

        new_entry = {"type": "error", "message": "New message."}
        set_empty_weekend("2026-10-31", new_entry)

        with open(empty_weekends_file) as f:
            data = json.load(f)
        assert data["2026-10-31"] == new_entry

    def test_error_type_stored_correctly(self, empty_weekends_file):
        from generate_weekly import set_empty_weekend
        entry = {"type": "error", "message": "Something went wrong."}
        set_empty_weekend("2026-10-31", entry)
        with open(empty_weekends_file) as f:
            data = json.load(f)
        assert data["2026-10-31"]["type"] == "error"


class TestFallbackBreakMessage:
    @pytest.mark.parametrize("date", ["2026-03-27", "2026-09-04", "2026-10-09", "2026-11-13"])
    def test_international_window_months(self, date):
        from generate_weekly import fallback_break_message, INTERNATIONAL_BREAK_MESSAGE
        assert fallback_break_message(date) == INTERNATIONAL_BREAK_MESSAGE

    @pytest.mark.parametrize("date", ["2026-06-12", "2026-07-17"])
    def test_summer_months(self, date):
        from generate_weekly import fallback_break_message, SUMMER_BREAK_MESSAGE
        assert fallback_break_message(date) == SUMMER_BREAK_MESSAGE

    def test_other_months_generic(self):
        from generate_weekly import fallback_break_message, FALLBACK_BREAK_MESSAGE
        assert fallback_break_message("2026-12-25") == FALLBACK_BREAK_MESSAGE


class TestMainExplanationFailure:
    @pytest.fixture()
    def run_main(self, tmp_path, monkeypatch, empty_weekends_file):
        import generate_weekly, pipeline, tools
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(generate_weekly, "next_friday", lambda: "2026-11-13")
        monkeypatch.setattr(pipeline, "run_pipeline", lambda: [])

        def boom(*a):
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        monkeypatch.setattr(pipeline, "explain_empty_weekend", boom)
        monkeypatch.setattr(tools, "_get_weekend_range", lambda: ("2026-11-13", "2026-11-16"))

        def run():
            generate_weekly.main()
            with open(empty_weekends_file) as f:
                return json.load(f)["2026-11-13"]
        return run

    def test_uses_date_based_fallback(self, run_main):
        from generate_weekly import INTERNATIONAL_BREAK_MESSAGE
        assert run_main() == {"type": "break", "message": INTERNATIONAL_BREAK_MESSAGE}

    def test_keeps_existing_break_message(self, run_main, empty_weekends_file):
        existing = {"type": "break", "message": "Nations League weekend."}
        with open(empty_weekends_file, "w") as f:
            json.dump({"2026-11-13": existing}, f)
        assert run_main() == existing
