from datetime import datetime, timezone

from models import Match, TeamStanding
from prompts import format_league_data


def make_match(home="Arsenal", away="Chelsea", matchday=32, hour=15):
    return Match(
        home_team=home,
        away_team=away,
        kickoff=datetime(2026, 10, 31, hour, 0, 0, tzinfo=timezone.utc),
        competition="PL",
        matchday=matchday,
    )


def make_standing(pos, team, pts, played, gd):
    return TeamStanding(position=pos, team=team, points=pts, played=played, goal_difference=gd)


def make_data(league_code="PL", fixtures=None, standings=None):
    return {
        league_code: {
            "fixtures": fixtures or [make_match()],
            "standings": standings or [make_standing(1, "Arsenal", 70, 30, 25)],
        }
    }


class TestFormatLeagueData:
    def test_league_header_present(self):
        output = format_league_data(make_data("PL"))
        assert "=== PL ===" in output

    def test_standings_section_present(self):
        output = format_league_data(make_data())
        assert "Standings:" in output

    def test_fixture_section_present(self):
        output = format_league_data(make_data())
        assert "Weekend Fixtures:" in output

    def test_positive_goal_difference_has_plus_sign(self):
        data = make_data(standings=[make_standing(1, "Arsenal", 70, 30, 25)])
        output = format_league_data(data)
        assert "+25" in output

    def test_negative_goal_difference_has_minus_sign(self):
        data = make_data(standings=[make_standing(18, "Burnley", 20, 30, -20)])
        output = format_league_data(data)
        assert "-20" in output

    def test_zero_goal_difference_has_plus_sign(self):
        data = make_data(standings=[make_standing(10, "Wolves", 40, 30, 0)])
        output = format_league_data(data)
        assert "+0" in output

    def test_fixture_contains_matchday(self):
        data = make_data(fixtures=[make_match(matchday=32)])
        output = format_league_data(data)
        assert "Matchday 32:" in output

    def test_fixture_contains_team_names(self):
        data = make_data(fixtures=[make_match(home="Arsenal", away="Chelsea")])
        output = format_league_data(data)
        assert "Arsenal vs Chelsea" in output

    def test_fixture_contains_kickoff_time(self):
        data = make_data(fixtures=[make_match(hour=15)])
        output = format_league_data(data)
        assert "15:00 UTC" in output

    def test_multiple_leagues_each_have_header(self):
        data = {
            "PL": {"fixtures": [make_match()], "standings": [make_standing(1, "Arsenal", 70, 30, 25)]},
            "BL1": {
                "fixtures": [
                    Match(
                        home_team="Bayern",
                        away_team="Dortmund",
                        kickoff=datetime(2026, 10, 31, 17, 30, 0, tzinfo=timezone.utc),
                        competition="BL1",
                        matchday=10,
                    )
                ],
                "standings": [make_standing(1, "Bayern", 60, 28, 30)],
            },
        }
        output = format_league_data(data)
        assert "=== PL ===" in output
        assert "=== BL1 ===" in output
        assert "Bayern vs Dortmund" in output
