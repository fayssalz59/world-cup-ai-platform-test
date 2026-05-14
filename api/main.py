import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ingestion.config import PROJECT_ROOT
from ml.train_prematch_result_model import FEATURE_COLUMNS


MODEL_PATH = PROJECT_ROOT / "models" / "prematch_result_baseline.joblib"
METRICS_PATH = PROJECT_ROOT / "reports" / "prematch_result_baseline_metrics.json"


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    features: dict[str, float] = Field(
        ...,
        description="Pre-match model features keyed by feature column name.",
    )
    home_team_name: str | None = Field(default=None, examples=["France"])
    away_team_name: str | None = Field(default=None, examples=["Argentina"])


class PredictionResponse(BaseModel):
    model_name: str
    model_type: str
    predicted_class: str
    probabilities: dict[str, float]
    feature_count: int
    home_team_name: str | None = None
    away_team_name: str | None = None


class TeamsPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    competition: str = Field(..., examples=["world_cup"])
    season: str = Field(..., examples=["2022"])
    home_team_name: str = Field(..., examples=["France"])
    away_team_name: str = Field(..., examples=["Argentina"])


class TeamFeatureSource(BaseModel):
    team_name: str
    source_match_id: int | str
    source_match_date: str
    source_opponent_team_name: str
    prematch_matches_played_before: int


class TeamsPredictionResponse(PredictionResponse):
    competition: str
    season: str
    home_feature_source: TeamFeatureSource
    away_feature_source: TeamFeatureSource


def read_metrics(path: Path = METRICS_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def expected_feature_columns(metrics: dict[str, Any] | None = None) -> list[str]:
    metrics = metrics or {}
    columns = metrics.get("feature_columns")
    if isinstance(columns, list) and all(isinstance(column, str) for column in columns):
        return columns
    return FEATURE_COLUMNS


def validate_features(features: dict[str, float], expected_columns: list[str]) -> None:
    provided = set(features)
    expected = set(expected_columns)
    missing = [column for column in expected_columns if column not in provided]
    unexpected = sorted(provided - expected)

    if missing or unexpected:
        detail: dict[str, list[str]] = {}
        if missing:
            detail["missing_features"] = missing
        if unexpected:
            detail["unexpected_features"] = unexpected
        raise HTTPException(status_code=422, detail=detail)


def normalize_team_name(team_name: str) -> str:
    return " ".join(team_name.casefold().strip().split())


def team_form_path(competition: str, season: str) -> Path:
    return (
        PROJECT_ROOT
        / "data"
        / "gold"
        / "statsbomb"
        / "prematch_team_form"
        / f"competition={competition}"
        / f"season={season}"
        / "prematch_team_form.parquet"
    )


@lru_cache(maxsize=32)
def load_team_form_dataset(competition: str, season: str) -> pd.DataFrame:
    path = team_form_path(competition, season)
    if not path.exists():
        raise FileNotFoundError(f"Pre-match team-form dataset not found: {path}")
    return pd.read_parquet(path)


def available_teams(dataframe: pd.DataFrame) -> list[str]:
    return sorted(dataframe["team_name"].dropna().astype(str).unique().tolist())


def latest_team_row(dataframe: pd.DataFrame, team_name: str) -> pd.Series:
    normalized = normalize_team_name(team_name)
    matches = dataframe[
        dataframe["team_name"].astype(str).map(normalize_team_name) == normalized
    ].copy()

    if matches.empty:
        raise HTTPException(
            status_code=404,
            detail={
                "message": f"Team not found in pre-match team-form dataset: {team_name}",
                "available_teams": available_teams(dataframe),
            },
        )

    matches["match_date"] = pd.to_datetime(matches["match_date"])
    matches = matches.sort_values(["match_date", "match_id"])
    return matches.iloc[-1]


def build_features_from_team_rows(
    home_row: pd.Series,
    away_row: pd.Series,
    feature_columns: list[str],
) -> dict[str, float]:
    features: dict[str, float] = {}
    for column in feature_columns:
        if column.startswith("home_"):
            source_column = column.removeprefix("home_")
            features[column] = float(home_row[source_column])
        elif column.startswith("away_"):
            source_column = column.removeprefix("away_")
            features[column] = float(away_row[source_column])
        else:
            raise ValueError(f"Unsupported model feature prefix: {column}")
    return features


def team_feature_source(row: pd.Series) -> TeamFeatureSource:
    match_date = pd.to_datetime(row["match_date"]).date().isoformat()
    return TeamFeatureSource(
        team_name=str(row["team_name"]),
        source_match_id=int(row["match_id"]),
        source_match_date=match_date,
        source_opponent_team_name=str(row["opponent_team_name"]),
        prematch_matches_played_before=int(row["prematch_matches_played_before"]),
    )


@lru_cache(maxsize=1)
def load_model_bundle() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model artifact not found: {MODEL_PATH}")

    metrics = read_metrics()
    model = joblib.load(MODEL_PATH)
    feature_columns = expected_feature_columns(metrics)
    labels = list(getattr(model, "classes_", [])) or metrics.get("labels", [])

    return {
        "model": model,
        "metrics": metrics,
        "feature_columns": feature_columns,
        "labels": labels,
    }


app = FastAPI(
    title="World Cup AI Platform API",
    description="Inference API for pre-match football result probabilities.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model_available": MODEL_PATH.exists(),
        "metrics_available": METRICS_PATH.exists(),
    }


@app.get("/model/info")
def model_info() -> dict[str, Any]:
    metrics = read_metrics()
    feature_columns = expected_feature_columns(metrics)
    payload: dict[str, Any] = {
        "model_name": "prematch_result_baseline",
        "model_path": str(MODEL_PATH),
        "model_available": MODEL_PATH.exists(),
        "metrics_path": str(METRICS_PATH),
        "metrics_available": METRICS_PATH.exists(),
        "feature_count": len(feature_columns),
        "feature_columns": feature_columns,
        "model_type": metrics.get("model_type", "unknown"),
        "trained_at_utc": metrics.get("trained_at_utc"),
        "datasets": metrics.get("datasets", []),
        "labels": metrics.get("labels", []),
        "accuracy": metrics.get("accuracy"),
        "dummy_most_frequent_accuracy": metrics.get("dummy_most_frequent_accuracy"),
        "model_note": metrics.get("model_note"),
    }
    return payload


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    try:
        bundle = load_model_bundle()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    feature_columns = bundle["feature_columns"]
    validate_features(request.features, feature_columns)

    row = pd.DataFrame([{column: request.features[column] for column in feature_columns}])
    model = bundle["model"]
    labels = list(getattr(model, "classes_", [])) or bundle["labels"]
    prediction = str(model.predict(row)[0])

    if not hasattr(model, "predict_proba"):
        raise HTTPException(status_code=500, detail="Loaded model does not expose predict_proba.")

    probabilities = model.predict_proba(row)[0]
    probability_map = {
        str(label): round(float(probability), 6)
        for label, probability in zip(labels, probabilities, strict=True)
    }

    metrics = bundle["metrics"]
    return PredictionResponse(
        model_name="prematch_result_baseline",
        model_type=metrics.get("model_type", type(model).__name__),
        predicted_class=prediction,
        probabilities=probability_map,
        feature_count=len(feature_columns),
        home_team_name=request.home_team_name,
        away_team_name=request.away_team_name,
    )


@app.post("/predict/from-teams", response_model=TeamsPredictionResponse)
def predict_from_teams(request: TeamsPredictionRequest) -> TeamsPredictionResponse:
    try:
        team_form = load_team_form_dataset(request.competition, request.season)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    home_row = latest_team_row(team_form, request.home_team_name)
    away_row = latest_team_row(team_form, request.away_team_name)

    try:
        bundle = load_model_bundle()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    feature_columns = bundle["feature_columns"]
    features = build_features_from_team_rows(home_row, away_row, feature_columns)

    prediction = predict(
        PredictionRequest(
            home_team_name=request.home_team_name,
            away_team_name=request.away_team_name,
            features=features,
        )
    )

    return TeamsPredictionResponse(
        **prediction.model_dump(),
        competition=request.competition,
        season=request.season,
        home_feature_source=team_feature_source(home_row),
        away_feature_source=team_feature_source(away_row),
    )
