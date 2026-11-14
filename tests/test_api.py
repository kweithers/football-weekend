import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    """Redirect api.DATA_DIR and api.EMPTY_WEEKENDS_FILE to a temp directory."""
    import api
    monkeypatch.setattr(api, "DATA_DIR", tmp_path)
    monkeypatch.setattr(api, "EMPTY_WEEKENDS_FILE", tmp_path / "empty_weekends.json")
    return tmp_path


@pytest.fixture()
def client(data_dir):
    from api import app
    return TestClient(app)


SAMPLE_MATCHES = [
    {
        "home_team": "Arsenal", "away_team": "Chelsea",
        "kickoff": "2026-11-01T15:00:00+00:00",
        "competition": "PL", "matchday": 10,
        "excitement_score": 8, "category": "relegation",
        "reasoning": "Big stakes",
    },
    {
        "home_team": "Liverpool", "away_team": "Man City",
        "kickoff": "2026-10-31T12:30:00+00:00",
        "competition": "PL", "matchday": 10,
        "excitement_score": 6, "category": "other",
        "reasoning": "Mild interest",
    },
    {
        "home_team": "Spurs", "away_team": "Everton",
        "kickoff": "2026-10-31T17:30:00+00:00",
        "competition": "PL", "matchday": 10,
        "excitement_score": 9, "category": "title",
        "reasoning": "Title decider",
    },
]


class TestLatestDataFile:
    def test_returns_none_when_dir_missing(self, tmp_path, monkeypatch):
        import api
        missing = tmp_path / "nonexistent"
        monkeypatch.setattr(api, "DATA_DIR", missing)
        assert api._latest_data_file() is None

    def test_returns_none_when_no_matching_files(self, data_dir):
        (data_dir / "other.json").write_text("{}")
        import api
        assert api._latest_data_file() is None

    def test_returns_most_recent_file(self, data_dir):
        older = data_dir / "weekend_2026-10-24.json"
        newer = data_dir / "weekend_2026-10-31.json"
        older.write_text("[]")
        newer.write_text("[]")
        import api
        assert api._latest_data_file() == newer

    def test_returns_only_file_when_one_exists(self, data_dir):
        f = data_dir / "weekend_2026-10-31.json"
        f.write_text("[]")
        import api
        assert api._latest_data_file() == f


class TestEmptyWeekend:
    def test_default_when_no_file(self, data_dir):
        import api
        result = api._empty_weekend("2026-10-31")
        assert result == api.DEFAULT_EMPTY_WEEKEND

    def test_default_when_weekend_date_none(self, data_dir):
        import api
        result = api._empty_weekend(None)
        assert result == api.DEFAULT_EMPTY_WEEKEND

    def test_default_when_date_not_in_file(self, data_dir):
        (data_dir / "empty_weekends.json").write_text(
            json.dumps({"2026-11-07": {"type": "break", "message": "Winter break"}})
        )
        import api
        result = api._empty_weekend("2026-10-31")
        assert result == api.DEFAULT_EMPTY_WEEKEND

    def test_returns_stored_entry(self, data_dir):
        entry = {"type": "error", "message": "Something went wrong."}
        (data_dir / "empty_weekends.json").write_text(
            json.dumps({"2026-10-31": entry})
        )
        import api
        result = api._empty_weekend("2026-10-31")
        assert result == entry

    def test_break_type_returned(self, data_dir):
        entry = {"type": "break", "message": "International break."}
        (data_dir / "empty_weekends.json").write_text(
            json.dumps({"2026-10-31": entry})
        )
        import api
        assert api._empty_weekend("2026-10-31")["type"] == "break"


class TestApiWeekendEndpoint:
    def test_404_when_no_data(self, client):
        response = client.get("/api/weekend")
        assert response.status_code == 404

    def test_returns_json_payload(self, client, data_dir):
        (data_dir / "weekend_2026-10-31.json").write_text(json.dumps(SAMPLE_MATCHES))
        response = client.get("/api/weekend")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["home_team"] == "Arsenal"


class TestIndexEndpoint:
    def test_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_league_names_enriched(self, client, data_dir):
        (data_dir / "weekend_2026-10-31.json").write_text(json.dumps(SAMPLE_MATCHES))
        response = client.get("/")
        assert response.status_code == 200
        assert "Premier League" in response.text

    def test_league_flags_rendered(self, client, data_dir):
        (data_dir / "weekend_2026-10-31.json").write_text(json.dumps(SAMPLE_MATCHES))
        response = client.get("/")
        assert response.status_code == 200
        assert "fi fi-gb-eng" in response.text

    def test_matches_sorted_by_day_then_score_desc(self, client, data_dir):
        (data_dir / "weekend_2026-10-31.json").write_text(json.dumps(SAMPLE_MATCHES))
        # Import app and call the index function directly to inspect template context
        from api import index
        from starlette.testclient import TestClient as TC
        from api import app

        # Use the API response to verify ordering indirectly:
        # Sat Oct 31: Spurs(9) before Liverpool(6); Sun Nov 1: Arsenal(8)
        response = client.get("/")
        text = response.text
        pos_spurs = text.find("Spurs")
        pos_liverpool = text.find("Liverpool")
        pos_arsenal = text.find("Arsenal")
        # Both Oct 31 matches appear before the Nov 1 match
        assert pos_spurs < pos_arsenal, "Oct 31 matches should appear before Nov 1"
        assert pos_liverpool < pos_arsenal, "Oct 31 matches should appear before Nov 1"
        # Within Oct 31, Spurs (score 9) should appear before Liverpool (score 6)
        assert pos_spurs < pos_liverpool, "Higher score should appear first within a day"

    def test_empty_matches_includes_empty_weekend_context(self, client, data_dir):
        (data_dir / "weekend_2026-10-31.json").write_text("[]")
        entry = {"type": "break", "message": "International break this weekend."}
        (data_dir / "empty_weekends.json").write_text(
            json.dumps({"2026-10-31": entry})
        )
        response = client.get("/")
        assert response.status_code == 200
        assert "International break this weekend." in response.text

    def test_non_empty_matches_no_break_message(self, client, data_dir):
        (data_dir / "weekend_2026-10-31.json").write_text(json.dumps(SAMPLE_MATCHES))
        (data_dir / "empty_weekends.json").write_text(
            json.dumps({"2026-10-31": {"type": "break", "message": "Should not appear"}})
        )
        response = client.get("/")
        assert "Should not appear" not in response.text


class TestPastWeeks:
    def _write_weeks(self, data_dir):
        (data_dir / "weekend_2026-10-24.json").write_text(json.dumps(SAMPLE_MATCHES[:1]))
        (data_dir / "weekend_2026-10-31.json").write_text(json.dumps(SAMPLE_MATCHES))
        (data_dir / "weekend_2026-11-07.json").write_text("[]")

    def test_list_weekends_newest_first(self, client, data_dir):
        self._write_weeks(data_dir)
        assert client.get("/api/weekends").json() == ["2026-11-07", "2026-10-31", "2026-10-24"]

    def test_api_weekend_by_date(self, client, data_dir):
        self._write_weeks(data_dir)
        response = client.get("/api/weekend/2026-10-24")
        assert response.status_code == 200
        assert response.json()[0]["home_team"] == "Arsenal"

    def test_api_weekend_by_date_404(self, client, data_dir):
        self._write_weeks(data_dir)
        assert client.get("/api/weekend/2026-01-01").status_code == 404
        assert client.get("/api/weekend/..%2Fsecret").status_code == 404

    def test_week_page_renders_that_week(self, client, data_dir):
        self._write_weeks(data_dir)
        response = client.get("/week/2026-10-24")
        assert response.status_code == 200
        assert "Arsenal" in response.text
        assert "Spurs" not in response.text
        assert "Weekend of 24 Oct 2026" in response.text

    def test_week_page_picker_and_neighbours(self, client, data_dir):
        self._write_weeks(data_dir)
        text = client.get("/week/2026-10-31").text
        assert 'value="2026-10-31" selected' in text
        assert 'href="/week/2026-10-24"' in text  # older
        assert 'href="/week/2026-11-07"' in text  # newer

    def test_week_page_404_for_unknown_week(self, client, data_dir):
        self._write_weeks(data_dir)
        assert client.get("/week/2026-01-01").status_code == 404

    def test_index_has_past_weeks_link_and_no_picker(self, client, data_dir):
        self._write_weeks(data_dir)
        text = client.get("/").text
        assert 'href="/history"' in text
        assert 'id="week-picker"' not in text

    def test_history_lists_all_weeks(self, client, data_dir):
        self._write_weeks(data_dir)
        (data_dir / "empty_weekends.json").write_text(
            json.dumps({"2026-11-07": {"type": "break", "message": "International break."}})
        )
        response = client.get("/history")
        assert response.status_code == 200
        text = response.text
        for d in ["2026-11-07", "2026-10-31", "2026-10-24"]:
            assert f'href="/week/{d}"' in text
        assert "International break." in text
        assert "Spurs" in text  # top match of 2026-10-31

    def test_history_empty(self, client):
        response = client.get("/history")
        assert response.status_code == 200
        assert "No rankings generated yet." in response.text
