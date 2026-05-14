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


FEATURE_COLUMNS = [
    "home_xg",
    "away_xg",
    "home_shots",
    "away_shots",
    "home_passes",
    "away_passes",
    "xg_difference_home",
    "shot_difference_home",
]
TARGET_COLUMN = "target"


def gold_match_features_path(competition: str, season: str) -> Path:
    return (
        PROJECT_ROOT
        / "data"
        / "gold"
        / "statsbomb"
        / "match_features"
        / f"competition={competition}"
        / f"season={season}"
        / "match_features.parquet"
    )


def load_gold_datasets(datasets: list[str]) -> pd.DataFrame:
    frames = []
    for dataset in datasets:
        competition, season = dataset.split(":", maxsplit=1)
        path = gold_match_features_path(competition, season)
        if not path.exists():
            raise FileNotFoundError(f"Missing Gold dataset: {path}")
        frame = pd.read_parquet(path)
        frame["competition"] = competition
        frame["season"] = season
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def prepare_training_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    required_columns = FEATURE_COLUMNS + [TARGET_COLUMN]
    missing = [column for column in required_columns if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Missing required ML columns: {missing}")
    return dataframe[required_columns].dropna(subset=[TARGET_COLUMN])


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
                    n_estimators=200,
                    max_depth=5,
                    min_samples_leaf=2,
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


def train_match_result_model(
    datasets: list[str],
    test_size: float,
    random_state: int,
) -> dict:
    raw = load_gold_datasets(datasets)
    training_frame = prepare_training_frame(raw)
    x_train, x_test, y_train, y_test = split_dataset(training_frame, test_size, random_state)

    model = build_model(random_state)
    model.fit(x_train, y_train)

    metrics = evaluate_model(model, x_test, y_test)
    metrics["dummy_most_frequent_accuracy"] = evaluate_dummy_baseline(x_train, y_train, x_test, y_test)
    metrics["datasets"] = datasets
    metrics["row_count"] = len(training_frame)
    metrics["train_rows"] = len(x_train)
    metrics["test_rows"] = len(x_test)
    metrics["feature_columns"] = FEATURE_COLUMNS
    metrics["trained_at_utc"] = datetime.now(timezone.utc).isoformat()
    metrics["model_type"] = "RandomForestClassifier"
    metrics["model_note"] = (
        "Post-match analytical baseline using match performance features, "
        "not a pre-match prediction model."
    )

    model_dir = PROJECT_ROOT / "models"
    reports_dir = PROJECT_ROOT / "reports"
    model_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    model_path = model_dir / "match_result_baseline.joblib"
    metrics_path = reports_dir / "match_result_baseline_metrics.json"
    joblib.dump(model, model_path)
    save_json(metrics_path, metrics)

    logger.info("Rows: {} train={} test={}", len(training_frame), len(x_train), len(x_test))
    logger.info("Accuracy: {:.3f}", metrics["accuracy"])
    logger.info("Dummy baseline accuracy: {:.3f}", metrics["dummy_most_frequent_accuracy"])
    logger.info("Saved model to {}", model_path)
    logger.info("Saved metrics to {}", metrics_path)
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a baseline match result model from Gold features.")
    parser.add_argument(
        "--dataset",
        action="append",
        required=True,
        help="Gold dataset in competition:season format, e.g. world_cup:2022",
    )
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_match_result_model(
        datasets=args.dataset,
        test_size=args.test_size,
        random_state=args.random_state,
    )


if __name__ == "__main__":
    main()
