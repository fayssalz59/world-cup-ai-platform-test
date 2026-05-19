import pandas as pd

from transformation.statsbomb_silver import (
    location_value,
    normalize_events,
    normalize_lineups,
    normalize_matches,
    normalize_passes,
    normalize_shots,
)


def sample_events() -> dict[int, list[dict]]:
    return {
        1: [
            {
                "id": "event-pass",
                "index": 1,
                "period": 1,
                "timestamp": "00:01:00.000",
                "minute": 1,
                "second": 0,
                "type": {"id": 30, "name": "Pass"},
                "team": {"id": 10, "name": "Team A"},
                "player": {"id": 100, "name": "Player A"},
                "location": [20.0, 30.0],
                "pass": {
                    "recipient": {"id": 101, "name": "Player B"},
                    "length": 12.5,
                    "angle": 0.4,
                    "height": {"name": "Ground Pass"},
                    "end_location": [35.0, 31.0],
                },
            },
            {
                "id": "event-shot",
                "index": 2,
                "period": 1,
                "timestamp": "00:02:00.000",
                "minute": 2,
                "second": 0,
                "type": {"id": 16, "name": "Shot"},
                "team": {"id": 10, "name": "Team A"},
                "player": {"id": 100, "name": "Player A"},
                "location": [102.0, 40.0],
                "shot": {
                    "statsbomb_xg": 0.35,
                    "outcome": {"name": "Goal"},
                    "body_part": {"name": "Right Foot"},
                    "end_location": [120.0, 40.0, 1.2],
                },
            },
        ]
    }


def test_location_value_handles_missing_coordinates() -> None:
    assert location_value([1.0, 2.0], 1) == 2.0
    assert location_value([], 0) is None
    assert location_value(None, 0) is None


def test_normalize_matches_extracts_team_and_score_columns() -> None:
    dataframe = normalize_matches(
        [
            {
                "match_id": 1,
                "match_date": "2022-12-18",
                "competition": {"competition_id": 43, "competition_name": "FIFA World Cup"},
                "season": {"season_id": 106, "season_name": "2022"},
                "home_team": {"home_team_id": 1, "home_team_name": "Argentina"},
                "away_team": {"away_team_id": 2, "away_team_name": "France"},
                "home_score": 3,
                "away_score": 3,
            }
        ]
    )

    assert dataframe.loc[0, "home_team_name"] == "Argentina"
    assert dataframe.loc[0, "away_score"] == 3


def test_normalize_events_shots_and_passes() -> None:
    events = sample_events()

    events_df = normalize_events(events)
    shots_df = normalize_shots(events)
    passes_df = normalize_passes(events)

    assert set(events_df["type_name"]) == {"Pass", "Shot"}
    assert shots_df.loc[0, "xg"] == 0.35
    assert passes_df.loc[0, "recipient_name"] == "Player B"


def test_normalize_lineups_one_row_per_player() -> None:
    dataframe = normalize_lineups(
        {
            1: [
                {
                    "team_id": 10,
                    "team_name": "Team A",
                    "lineup": [
                        {
                            "player_id": 100,
                            "player_name": "Player A",
                            "jersey_number": 9,
                            "country": {"name": "France"},
                            "positions": [],
                        }
                    ],
                }
            ]
        }
    )

    assert dataframe.loc[0, "player_name"] == "Player A"
    assert dataframe.loc[0, "country"] == "France"


def test_parquet_round_trip(tmp_path) -> None:
    path = tmp_path / "sample.parquet"
    expected = pd.DataFrame([{"match_id": 1, "team_name": "Team A"}])

    expected.to_parquet(path, index=False)
    actual = pd.read_parquet(path)

    assert actual.to_dict("records") == expected.to_dict("records")
