import os
from datetime import timezone
from unittest.mock import MagicMock, patch


def make_mock_response(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


FIXTURE_RESPONSE = {
    "matches": [
        {
            "utcDate": "2026-10-31T15:00:00Z",
            "homeTeam": {"name": "Arsenal"},
            "awayTeam": {"name": "Chelsea"},
            "matchday": 10,
        }
    ]
}

STANDINGS_RESPONSE = {
    "standings": [
        {
            "type": "HOME",
            "table": [{"position": 1, "team": {"name": "Arsenal"}, "points": 40, "playedGames": 15, "goalDifference": 20}],
        },
        {
            "type": "TOTAL",
            "table": [
                {"position": 1, "team": {"name": "Arsenal"}, "points": 70, "playedGames": 30, "goalDifference": 25},
                {"position": 2, "team": {"name": "Chelsea"}, "points": 65, "playedGames": 30, "goalDifference": 15},
            ],
        },
        {
            "type": "AWAY",
            "table": [{"position": 1, "team": {"name": "Arsenal"}, "points": 30, "playedGames": 15, "goalDifference": 5}],
        },
    ]
}


class TestGetWeekendFixturesParsing:
    def _invoke(self, response_data):
        with (
            patch("tools.requests.get", return_value=make_mock_response(response_data)),
            patch("tools.time.sleep"),
            patch.dict(os.environ, {"FOOTBALL_DATA_API_KEY": "test"}),
        ):
            from tools import get_weekend_fixtures
            return get_weekend_fixtures.invoke("PL")

    def test_parses_utc_date_with_z_suffix(self):
        matches = self._invoke(FIXTURE_RESPONSE)
        assert len(matches) == 1
        assert matches[0].kickoff.tzinfo == timezone.utc

    def test_kickoff_values_correct(self):
        matches = self._invoke(FIXTURE_RESPONSE)
        assert matches[0].kickoff.hour == 15
        assert matches[0].kickoff.day == 31

    def test_team_names_parsed(self):
        matches = self._invoke(FIXTURE_RESPONSE)
        assert matches[0].home_team == "Arsenal"
        assert matches[0].away_team == "Chelsea"

    def test_matchday_parsed(self):
        matches = self._invoke(FIXTURE_RESPONSE)
        assert matches[0].matchday == 10

    def test_competition_set_from_league_code(self):
        matches = self._invoke(FIXTURE_RESPONSE)
        assert matches[0].competition == "PL"

    def test_empty_matches_returns_empty_list(self):
        matches = self._invoke({"matches": []})
        assert matches == []

    def test_multiple_matches_returned(self):
        response = {
            "matches": [
                {"utcDate": "2026-10-31T15:00:00Z", "homeTeam": {"name": "A"}, "awayTeam": {"name": "B"}, "matchday": 1},
                {"utcDate": "2026-11-01T12:30:00Z", "homeTeam": {"name": "C"}, "awayTeam": {"name": "D"}, "matchday": 1},
            ]
        }
        matches = self._invoke(response)
        assert len(matches) == 2


class TestGetStandingsParsing:
    def _invoke(self, response_data):
        with (
            patch("tools.requests.get", return_value=make_mock_response(response_data)),
            patch("tools.time.sleep"),
            patch.dict(os.environ, {"FOOTBALL_DATA_API_KEY": "test"}),
        ):
            from tools import get_standings
            return get_standings.invoke("PL")

    def test_only_total_table_returned(self):
        standings = self._invoke(STANDINGS_RESPONSE)
        # HOME table has pts=40, TOTAL has pts=70 — we should get pts=70
        assert all(s.points in (70, 65) for s in standings)

    def test_correct_number_of_entries_from_total(self):
        standings = self._invoke(STANDINGS_RESPONSE)
        assert len(standings) == 2

    def test_fields_mapped_correctly(self):
        standings = self._invoke(STANDINGS_RESPONSE)
        arsenal = standings[0]
        assert arsenal.position == 1
        assert arsenal.team == "Arsenal"
        assert arsenal.points == 70
        assert arsenal.played == 30
        assert arsenal.goal_difference == 25

    def test_no_total_table_returns_empty(self):
        response = {
            "standings": [
                {"type": "HOME", "table": [{"position": 1, "team": {"name": "A"}, "points": 40, "playedGames": 15, "goalDifference": 10}]},
            ]
        }
        standings = self._invoke(response)
        assert standings == []

    def test_empty_standings_returns_empty(self):
        standings = self._invoke({"standings": []})
        assert standings == []
