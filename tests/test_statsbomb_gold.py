import pandas as pd
import pytest

from transformation.statsbomb_gold import build_match_features, build_team_match_features


def test_build_team_match_features_adds_xg_passes_and_result() -> None:
    matches = pd.DataFrame(
        [
            {
                "match_id": 1,
                "match_date": "2022-12-18",
                "home_team_id": 10,
                "home_team_name": "Team A",
                "away_team_id": 20,
                "away_team_name": "Team B",
                "home_score": 2,
                "away_score": 1,
            }
        ]
    )
    shots = pd.DataFrame(
        [
            {"match_id": 1, "team_id": 10, "team_name": "Team A", "event_id": "s1", "xg": 0.4, "outcome": "Goal"},
            {"match_id": 1, "team_id": 10, "team_name": "Team A", "event_id": "s2", "xg": 0.2, "outcome": "Saved"},
            {"match_id": 1, "team_id": 20, "team_name": "Team B", "event_id": "s3", "xg": 0.1, "outcome": "Goal"},
        ]
    )
    passes = pd.DataFrame(
        [
            {"match_id": 1, "team_id": 10, "team_name": "Team A", "event_id": "p1", "outcome": None},
            {"match_id": 1, "team_id": 10, "team_name": "Team A", "event_id": "p2", "outcome": "Incomplete"},
            {"match_id": 1, "team_id": 20, "team_name": "Team B", "event_id": "p3", "outcome": None},
        ]
    )

    dataframe = build_team_match_features(matches, shots, passes)
    home = dataframe[dataframe["is_home"]].iloc[0]

    assert len(dataframe) == 2
    assert home["xg"] == pytest.approx(0.6)
    assert home["shots"] == 2
    assert home["completed_passes"] == 1
    assert home["result"] == "win"


def test_build_match_features_creates_ml_ready_match_row() -> None:
    team_match_features = pd.DataFrame(
        [
            {
                "match_id": 1,
                "match_date": "2022-12-18",
                "team_name": "Team A",
                "is_home": True,
                "goals_for": 2,
                "xg": 0.8,
                "shots": 5,
                "passes": 100,
                "result": "win",
            },
            {
                "match_id": 1,
                "match_date": "2022-12-18",
                "team_name": "Team B",
                "is_home": False,
                "goals_for": 1,
                "xg": 0.4,
                "shots": 3,
                "passes": 90,
                "result": "loss",
            },
        ]
    )

    dataframe = build_match_features(team_match_features)

    assert dataframe.loc[0, "home_team_name"] == "Team A"
    assert dataframe.loc[0, "xg_difference_home"] == pytest.approx(0.4)
    assert dataframe.loc[0, "target"] == "win"
