import pandas as pd
import pytest

from transformation.statsbomb_prematch import (
    add_team_rolling_features,
    build_prematch_match_features,
)


def sample_team_match_features() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "match_id": 1,
                "match_date": "2022-01-01",
                "team_id": 10,
                "team_name": "Team A",
                "opponent_team_id": 20,
                "opponent_team_name": "Team B",
                "is_home": True,
                "goals_for": 2,
                "goals_against": 1,
                "shots": 10,
                "xg": 1.5,
                "passes": 400,
                "completed_passes": 320,
                "goal_difference": 1,
                "pass_completion_rate": 0.8,
                "result": "win",
            },
            {
                "match_id": 1,
                "match_date": "2022-01-01",
                "team_id": 20,
                "team_name": "Team B",
                "opponent_team_id": 10,
                "opponent_team_name": "Team A",
                "is_home": False,
                "goals_for": 1,
                "goals_against": 2,
                "shots": 8,
                "xg": 0.8,
                "passes": 350,
                "completed_passes": 280,
                "goal_difference": -1,
                "pass_completion_rate": 0.8,
                "result": "loss",
            },
            {
                "match_id": 2,
                "match_date": "2022-01-05",
                "team_id": 10,
                "team_name": "Team A",
                "opponent_team_id": 30,
                "opponent_team_name": "Team C",
                "is_home": False,
                "goals_for": 0,
                "goals_against": 0,
                "shots": 6,
                "xg": 0.4,
                "passes": 300,
                "completed_passes": 210,
                "goal_difference": 0,
                "pass_completion_rate": 0.7,
                "result": "draw",
            },
            {
                "match_id": 2,
                "match_date": "2022-01-05",
                "team_id": 30,
                "team_name": "Team C",
                "opponent_team_id": 10,
                "opponent_team_name": "Team A",
                "is_home": True,
                "goals_for": 0,
                "goals_against": 0,
                "shots": 7,
                "xg": 0.6,
                "passes": 320,
                "completed_passes": 250,
                "goal_difference": 0,
                "pass_completion_rate": 0.78,
                "result": "draw",
            },
        ]
    )


def test_rolling_features_use_only_previous_matches() -> None:
    dataframe = add_team_rolling_features(sample_team_match_features(), window=5)
    team_a = dataframe[dataframe["team_id"] == 10].sort_values("match_date")

    first = team_a.iloc[0]
    second = team_a.iloc[1]

    assert pd.isna(first["prematch_avg_xg_last_5"])
    assert first["prematch_matches_played_before"] == 0
    assert second["prematch_avg_xg_last_5"] == pytest.approx(1.5)
    assert second["prematch_avg_goals_for_last_5"] == pytest.approx(2)
    assert second["prematch_matches_played_before"] == 1


def test_build_prematch_match_features_has_target_and_home_away_history() -> None:
    team_form = add_team_rolling_features(sample_team_match_features(), window=5)
    match_features = build_prematch_match_features(team_form, window=5)

    assert "home_prematch_avg_xg_last_5" in match_features.columns
    assert "away_prematch_avg_xg_last_5" in match_features.columns
    assert "target" in match_features.columns
    assert len(match_features) == 2
