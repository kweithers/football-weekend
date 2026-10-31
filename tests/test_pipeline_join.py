import pytest
from datetime import datetime, timezone

from models import LLMMatchRanking, LLMRankedMatchList, Match
from pipeline import _build_ranked_matches


def make_match(home="Arsenal", away="Chelsea", competition="PL", matchday=10):
    return Match(
        home_team=home,
        away_team=away,
        kickoff=datetime(2026, 10, 31, 15, 0, 0, tzinfo=timezone.utc),
        competition=competition,
        matchday=matchday,
    )


def make_llm_ranking(home="Arsenal", away="Chelsea", competition="PL", score=7, category="other"):
    return LLMMatchRanking(
        home_team=home,
        away_team=away,
        competition=competition,
        excitement_score=score,
        category=category,
        reasoning="test reasoning",
    )


class TestBuildRankedMatches:
    def test_known_match_is_included(self):
        match = make_match()
        all_matches = {("Arsenal", "Chelsea", "PL"): match}
        result = LLMRankedMatchList(matches=[make_llm_ranking(score=7)])
        ranked = _build_ranked_matches(all_matches, result)
        assert len(ranked) == 1
        assert ranked[0].match is match

    def test_hallucinated_match_is_skipped(self):
        match = make_match()
        all_matches = {("Arsenal", "Chelsea", "PL"): match}
        result = LLMRankedMatchList(matches=[
            make_llm_ranking(home="Ghost FC", away="Phantom United", score=9),
        ])
        ranked = _build_ranked_matches(all_matches, result)
        assert ranked == []

    def test_mix_of_known_and_hallucinated(self):
        match = make_match()
        all_matches = {("Arsenal", "Chelsea", "PL"): match}
        result = LLMRankedMatchList(matches=[
            make_llm_ranking(home="Ghost FC", away="Phantom United", score=9),
            make_llm_ranking(score=6),
        ])
        ranked = _build_ranked_matches(all_matches, result)
        assert len(ranked) == 1
        assert ranked[0].match is match

    def test_sorted_by_score_descending(self):
        m1 = make_match(home="Arsenal", away="Chelsea")
        m2 = make_match(home="Liverpool", away="Man City")
        m3 = make_match(home="Spurs", away="Everton")
        all_matches = {
            ("Arsenal", "Chelsea", "PL"): m1,
            ("Liverpool", "Man City", "PL"): m2,
            ("Spurs", "Everton", "PL"): m3,
        }
        result = LLMRankedMatchList(matches=[
            make_llm_ranking("Arsenal", "Chelsea", score=5),
            make_llm_ranking("Liverpool", "Man City", score=9),
            make_llm_ranking("Spurs", "Everton", score=3),
        ])
        ranked = _build_ranked_matches(all_matches, result)
        scores = [r.excitement_score for r in ranked]
        assert scores == [9, 5, 3]

    def test_original_kickoff_preserved(self):
        # The LLM should not be the source of kickoff time — the original Match must be used
        original_kickoff = datetime(2026, 10, 31, 15, 0, 0, tzinfo=timezone.utc)
        match = Match(
            home_team="Arsenal", away_team="Chelsea",
            kickoff=original_kickoff, competition="PL", matchday=10,
        )
        all_matches = {("Arsenal", "Chelsea", "PL"): match}
        result = LLMRankedMatchList(matches=[make_llm_ranking(score=7)])
        ranked = _build_ranked_matches(all_matches, result)
        assert ranked[0].match.kickoff == original_kickoff

    def test_all_hallucinated_returns_empty_list(self):
        all_matches = {("Arsenal", "Chelsea", "PL"): make_match()}
        result = LLMRankedMatchList(matches=[
            make_llm_ranking("X", "Y", score=8),
            make_llm_ranking("A", "B", score=5),
        ])
        ranked = _build_ranked_matches(all_matches, result)
        assert ranked == []

    def test_empty_llm_result_returns_empty_list(self):
        all_matches = {("Arsenal", "Chelsea", "PL"): make_match()}
        result = LLMRankedMatchList(matches=[])
        assert _build_ranked_matches(all_matches, result) == []

    def test_category_and_reasoning_carried_through(self):
        match = make_match()
        all_matches = {("Arsenal", "Chelsea", "PL"): match}
        ranking = LLMMatchRanking(
            home_team="Arsenal", away_team="Chelsea", competition="PL",
            excitement_score=8, category="relegation", reasoning="Fighting to stay up"
        )
        result = LLMRankedMatchList(matches=[ranking])
        ranked = _build_ranked_matches(all_matches, result)
        assert ranked[0].category == "relegation"
        assert ranked[0].reasoning == "Fighting to stay up"
        assert ranked[0].excitement_score == 8


class TestRunPipelineRaisesOnEmptyRanking:
    def test_raises_when_fixtures_fetched_but_none_ranked(self):
        """run_pipeline() should raise RuntimeError if LLM returns no matching rankings."""
        from unittest.mock import MagicMock, patch
        from datetime import datetime, timezone
        from models import LLMRankedMatchList

        match = make_match()
        league_data = {"PL": {"fixtures": [match], "standings": []}}

        with (
            patch("pipeline.fetch_all_leagues_data", return_value=league_data),
            patch("pipeline.format_league_data", return_value="formatted"),
            patch("pipeline.ChatGoogleGenerativeAI") as mock_llm_cls,
        ):
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = LLMRankedMatchList(matches=[])
            mock_llm_cls.return_value.with_structured_output.return_value.__ror__ = MagicMock(return_value=mock_chain)

            # Patch the chain construction directly
            with patch("pipeline.ranking_prompt") as mock_prompt:
                mock_prompt.__or__ = MagicMock(return_value=mock_chain)
                from pipeline import run_pipeline
                with pytest.raises(RuntimeError, match="Ranking failed"):
                    run_pipeline()
