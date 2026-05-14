import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from loguru import logger
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from ingestion.config import PROJECT_ROOT


WINDOW = 5
FEATURE_COLUMNS = [
    f"home_prematch_avg_goals_for_last_{WINDOW}",
    f"home_prematch_avg_goals_against_last_{WINDOW}",
    f"home_prematch_avg_goal_difference_last_{WINDOW}",
    f"home_prematch_avg_xg_last_{WINDOW}",
    f"home_prematch_avg_shots_last_{WINDOW}",
    f"home_prematch_avg_passes_last_{WINDOW}",
    f"home_prematch_avg_completed_passes_last_{WINDOW}",
    f"home_prematch_avg_pass_completion_rate_last_{WINDOW}",
    f"home_prematch_avg_points_last_{WINDOW}",
    f"home_prematch_win_rate_last_{WINDOW}",
    f"home_prematch_unbeaten_rate_last_{WINDOW}",
    "home_prematch_matches_played_before",
    f"away_prematch_avg_goals_for_last_{WINDOW}",
    f"away_prematch_avg_goals_against_last_{WINDOW}",
    f"away_prematch_avg_goal_difference_last_{WINDOW}",
    f"away_prematch_avg_xg_last_{WINDOW}",
    f"away_prematch_avg_shots_last_{WINDOW}",
    f"away_prematch_avg_passes_last_{WINDOW}",
    f"away_prematch_avg_completed_passes_last_{WINDOW}",
    f"away_prematch_avg_pass_completion_rate_last_{WINDOW}",
    f"away_prematch_avg_points_last_{WINDOW}",
    f"away_prematch_win_rate_last_{WINDOW}",
    f"away_prematch_unbeaten_rate_last_{WINDOW}",
    "away_prematch_matches_played_before",
]
TARGET_COLUMN = "target"


def prematch_features_path(competition: str, season: str) -> Path:
    return (
        PROJECT_ROOT
        / "data"
        / "gold"
        / "statsbomb"
        / "prematch_match_features"
        / f"competition={competition}"
        / f"season={season}"
        / "prematch_match_features.parquet"
    )


def load_prematch_datasets(datasets: list[str]) -> pd.DataFrame:
    frames = []
    for dataset in datasets:
        competition, season = dataset.split(":", maxsplit=1)
        path = prematch_features_path(competition, season)
        if not path.exists():
            raise FileNotFoundError(f"Missing pre-match Gold dataset: {path}")
        frame = pd.read_parquet(path)
        frame["competition"] = competition
        frame["season"] = season
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def prepare_training_frame(dataframe: pd.DataFrame, min_history: int) -> pd.DataFrame:
    required_columns = FEATURE_COLUMNS + [TARGET_COLUMN]
    missing = [column for column in required_columns if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Missing required pre-match ML columns: {missing}")

    prepared = dataframe[required_columns].copy()
    prepared = prepared.dropna(subset=[TARGET_COLUMN])
    prepared = prepared[
        (prepared["home_prematch_matches_played_before"] >= min_history)
        & (prepared["away_prematch_matches_played_before"] >= min_history)
    ]
    return prepared


def split_dataset(dataframe: pd.DataFrame, test_size: float, random_state: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    x = dataframe[FEATURE_COLUMNS]
    y = dataframe[TARGET_COLUMN]
    stratify = y if y.value_counts().min() >= 2 else None
    return train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify,
    )


def build_model(random_state: int) -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=300,
                    max_depth=6,
                    min_samples_leaf=3,
                    random_state=random_state,
                    class_weight="balanced",
                ),
            ),
        ]
    )


def evaluate_model(model: Pipeline, x_test: pd.DataFrame, y_test: pd.Series) -> dict:
    predictions = model.predict(x_test)
    labels = sorted(y_test.unique())
    return {
        "accuracy": accuracy_score(y_test, predictions),
        "classification_report": classification_report(
            y_test,
            predictions,
            labels=labels,
            output_dict=True,
            zero_division=0,
        ),
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=labels).tolist(),
        "labels": labels,
    }


def evaluate_dummy_baseline(x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame, y_test: pd.Series) -> float:
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(x_train, y_train)
    return accuracy_score(y_test, dummy.predict(x_test))


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def train_prematch_result_model(
    datasets: list[str],
    min_history: int,
    test_size: float,
    random_state: int,
) -> dict:
    raw = load_prematch_datasets(datasets)
    training_frame = prepare_training_frame(raw, min_history=min_history)
    if len(training_frame) < 10:
        raise ValueError(
            f"Not enough rows after min_history={min_history}: {len(training_frame)}"
        )

    x_train, x_test, y_train, y_test = split_dataset(training_frame, test_size, random_state)
    model = build_model(random_state)
    model.fit(x_train, y_train)

    metrics = evaluate_model(model, x_test, y_test)
    metrics["dummy_most_frequent_accuracy"] = evaluate_dummy_baseline(x_train, y_train, x_test, y_test)
    metrics["datasets"] = datasets
    metrics["row_count"] = len(training_frame)
    metrics["raw_row_count"] = len(raw)
    metrics["train_rows"] = len(x_train)
    metrics["test_rows"] = len(x_test)
    metrics["min_history"] = min_history
    metrics["feature_columns"] = FEATURE_COLUMNS
    metrics["trained_at_utc"] = datetime.now(timezone.utc).isoformat()
    metrics["model_type"] = "RandomForestClassifier"
    metrics["model_note"] = "Pre-match model using only historical rolling features known before kickoff."

    model_dir = PROJECT_ROOT / "models"
    reports_dir = PROJECT_ROOT / "reports"
    model_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    model_path = model_dir / "prematch_result_baseline.joblib"
    metrics_path = reports_dir / "prematch_result_baseline_metrics.json"
    joblib.dump(model, model_path)
    save_json(metrics_path, metrics)

    logger.info("Rows: {} raw={} train={} test={}", len(training_frame), len(raw), len(x_train), len(x_test))
    logger.info("Accuracy: {:.3f}", metrics["accuracy"])
    logger.info("Dummy baseline accuracy: {:.3f}", metrics["dummy_most_frequent_accuracy"])
    logger.info("Saved model to {}", model_path)
    logger.info("Saved metrics to {}", metrics_path)
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a pre-match result model from Gold rolling features.")
    parser.add_argument("--dataset", action="append", required=True)
    parser.add_argument("--min-history", type=int, default=1)
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_prematch_result_model(
        datasets=args.dataset,
        min_history=args.min_history,
        test_size=args.test_size,
        random_state=args.random_state,
    )


if __name__ == "__main__":
    main()
