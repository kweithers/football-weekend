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
