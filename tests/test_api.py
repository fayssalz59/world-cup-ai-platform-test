from typing import ClassVar

import pandas as pd
import pytest
from fastapi import HTTPException

from api.main import (
    PredictionRequest,
    TeamsPredictionRequest,
    build_features_from_team_rows,
    latest_team_row,
    load_model_bundle,
    model_info,
    predict,
    predict_from_teams,
    validate_features,
)
from ml.train_prematch_result_model import FEATURE_COLUMNS


class StubModel:
    classes_: ClassVar[list[str]] = ["draw", "loss", "win"]

    def predict(self, dataframe):
        return ["win"]

    def predict_proba(self, dataframe):
        return [[0.2, 0.3, 0.5]]


def sample_team_form_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "match_id": 1,
                "match_date": "2022-11-22",
                "team_name": "France",
                "opponent_team_name": "Australia",
                "prematch_matches_played_before": 1,
                "prematch_avg_goals_for_last_5": 1.0,
                "prematch_avg_goals_against_last_5": 0.5,
                "prematch_avg_goal_difference_last_5": 0.5,
                "prematch_avg_xg_last_5": 1.2,
                "prematch_avg_shots_last_5": 10.0,
                "prematch_avg_passes_last_5": 500.0,
                "prematch_avg_completed_passes_last_5": 440.0,
                "prematch_avg_pass_completion_rate_last_5": 0.88,
                "prematch_avg_points_last_5": 3.0,
                "prematch_win_rate_last_5": 1.0,
                "prematch_unbeaten_rate_last_5": 1.0,
            },
            {
                "match_id": 2,
                "match_date": "2022-12-18",
                "team_name": "France",
                "opponent_team_name": "Argentina",
                "prematch_matches_played_before": 6,
                "prematch_avg_goals_for_last_5": 2.0,
                "prematch_avg_goals_against_last_5": 1.0,
                "prematch_avg_goal_difference_last_5": 1.0,
                "prematch_avg_xg_last_5": 1.7,
                "prematch_avg_shots_last_5": 12.0,
                "prematch_avg_passes_last_5": 530.0,
                "prematch_avg_completed_passes_last_5": 470.0,
                "prematch_avg_pass_completion_rate_last_5": 0.89,
                "prematch_avg_points_last_5": 2.4,
                "prematch_win_rate_last_5": 0.8,
                "prematch_unbeaten_rate_last_5": 1.0,
            },
            {
                "match_id": 3,
                "match_date": "2022-12-18",
                "team_name": "Argentina",
                "opponent_team_name": "France",
                "prematch_matches_played_before": 6,
                "prematch_avg_goals_for_last_5": 2.2,
                "prematch_avg_goals_against_last_5": 0.8,
                "prematch_avg_goal_difference_last_5": 1.4,
                "prematch_avg_xg_last_5": 1.9,
                "prematch_avg_shots_last_5": 13.0,
                "prematch_avg_passes_last_5": 520.0,
                "prematch_avg_completed_passes_last_5": 455.0,
                "prematch_avg_pass_completion_rate_last_5": 0.87,
                "prematch_avg_points_last_5": 2.2,
                "prematch_win_rate_last_5": 0.7,
                "prematch_unbeaten_rate_last_5": 0.9,
            },
        ]
    )


def test_model_info_returns_expected_features() -> None:
    payload = model_info()

    assert payload["model_name"] == "prematch_result_baseline"
    assert payload["feature_count"] == len(FEATURE_COLUMNS)


def test_predict_returns_probabilities(monkeypatch) -> None:
    load_model_bundle.cache_clear()

    def fake_bundle():
        return {
            "model": StubModel(),
            "metrics": {"model_type": "StubClassifier"},
            "feature_columns": FEATURE_COLUMNS,
            "labels": ["draw", "loss", "win"],
        }

    monkeypatch.setattr("api.main.load_model_bundle", fake_bundle)
    features = {column: 1.0 for column in FEATURE_COLUMNS}

    response = predict(
        PredictionRequest(
            home_team_name="France",
            away_team_name="Argentina",
            features=features,
        )
    )

    payload = response.model_dump()
    assert payload["predicted_class"] == "win"
    assert payload["probabilities"] == {"draw": 0.2, "loss": 0.3, "win": 0.5}
    assert payload["feature_count"] == len(FEATURE_COLUMNS)


def test_predict_rejects_missing_features(monkeypatch) -> None:
    def fake_bundle():
        return {
            "model": StubModel(),
            "metrics": {},
            "feature_columns": FEATURE_COLUMNS,
            "labels": ["draw", "loss", "win"],
        }

    monkeypatch.setattr("api.main.load_model_bundle", fake_bundle)
    features = {column: 1.0 for column in FEATURE_COLUMNS[:-1]}

    with pytest.raises(HTTPException) as exc_info:
        predict(PredictionRequest(features=features))

    assert exc_info.value.status_code == 422
    assert "missing_features" in exc_info.value.detail


def test_validate_features_rejects_unexpected_feature() -> None:
    features = {column: 1.0 for column in FEATURE_COLUMNS}
    features["extra"] = 1.0

    with pytest.raises(HTTPException) as exc_info:
        validate_features(features, FEATURE_COLUMNS)

    assert exc_info.value.status_code == 422


def test_latest_team_row_is_case_insensitive_and_uses_latest_match() -> None:
    row = latest_team_row(sample_team_form_frame(), " france ")

    assert row["match_id"] == 2
    assert row["opponent_team_name"] == "Argentina"


def test_build_features_from_team_rows_maps_home_and_away_prefixes() -> None:
    dataframe = sample_team_form_frame()
    home_row = latest_team_row(dataframe, "France")
    away_row = latest_team_row(dataframe, "Argentina")

    features = build_features_from_team_rows(home_row, away_row, FEATURE_COLUMNS)

    assert set(features) == set(FEATURE_COLUMNS)
    assert features["home_prematch_avg_goals_for_last_5"] == 2.0
    assert features["away_prematch_avg_goals_for_last_5"] == 2.2


def test_predict_from_teams_returns_prediction_with_sources(monkeypatch) -> None:
    def fake_bundle():
        return {
            "model": StubModel(),
            "metrics": {"model_type": "StubClassifier"},
            "feature_columns": FEATURE_COLUMNS,
            "labels": ["draw", "loss", "win"],
        }

    monkeypatch.setattr("api.main.load_model_bundle", fake_bundle)
    monkeypatch.setattr("api.main.load_team_form_dataset", lambda competition, season: sample_team_form_frame())

    response = predict_from_teams(
        TeamsPredictionRequest(
            competition="world_cup",
            season="2022",
            home_team_name="France",
            away_team_name="Argentina",
        )
    )

    payload = response.model_dump()
    assert payload["predicted_class"] == "win"
    assert payload["competition"] == "world_cup"
    assert payload["home_feature_source"]["source_match_id"] == 2
    assert payload["away_feature_source"]["source_match_id"] == 3


def test_predict_from_teams_rejects_unknown_team(monkeypatch) -> None:
    monkeypatch.setattr("api.main.load_team_form_dataset", lambda competition, season: sample_team_form_frame())

    with pytest.raises(HTTPException) as exc_info:
        predict_from_teams(
            TeamsPredictionRequest(
                competition="world_cup",
                season="2022",
                home_team_name="Spain",
                away_team_name="Argentina",
            )
        )

    assert exc_info.value.status_code == 404
    assert "available_teams" in exc_info.value.detail
