import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
from loguru import logger

from ingestion.azure_blob import AzureBlobUploader
from ingestion.config import configure_local_cert_bundle, load_settings


ROLLING_COLUMNS = [
    "goals_for",
    "goals_against",
    "goal_difference",
    "xg",
    "shots",
    "passes",
    "completed_passes",
    "pass_completion_rate",
]


def configure_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def gold_table_path(gold_dir: Path, table_name: str, competition: str, season: str) -> Path:
    return (
        gold_dir
        / "statsbomb"
        / table_name
        / f"competition={competition}"
        / f"season={season}"
        / f"{table_name}.parquet"
    )


def result_points(result: str) -> int:
    if result == "win":
        return 3
    if result == "draw":
        return 1
    return 0


def add_team_rolling_features(team_match_features: pd.DataFrame, window: int) -> pd.DataFrame:
    dataframe = team_match_features.copy()
    dataframe["match_date"] = pd.to_datetime(dataframe["match_date"])
    dataframe["points"] = dataframe["result"].map(result_points)
    dataframe = dataframe.sort_values(["team_id", "match_date", "match_id"]).reset_index(drop=True)

    for column in ROLLING_COLUMNS + ["points"]:
        dataframe[f"prematch_avg_{column}_last_{window}"] = (
            dataframe.groupby("team_id")[column]
            .transform(lambda values: values.shift(1).rolling(window=window, min_periods=1).mean())
        )

    dataframe[f"prematch_matches_played_before"] = dataframe.groupby("team_id").cumcount()
    dataframe[f"prematch_win_rate_last_{window}"] = (
        dataframe.groupby("team_id")["result"]
        .transform(lambda values: (values.shift(1) == "win").rolling(window=window, min_periods=1).mean())
    )
    dataframe[f"prematch_unbeaten_rate_last_{window}"] = (
        dataframe.groupby("team_id")["result"]
        .transform(lambda values: (values.shift(1).isin(["win", "draw"])).rolling(window=window, min_periods=1).mean())
    )

    return dataframe


def build_prematch_match_features(team_form: pd.DataFrame, window: int) -> pd.DataFrame:
    base_columns = [
        "match_id",
        "match_date",
        "team_id",
        "team_name",
        "opponent_team_id",
        "opponent_team_name",
        "is_home",
        "goals_for",
        "goals_against",
        "result",
        f"prematch_matches_played_before",
        f"prematch_win_rate_last_{window}",
        f"prematch_unbeaten_rate_last_{window}",
    ]
    rolling_feature_columns = [
        f"prematch_avg_{column}_last_{window}"
        for column in ROLLING_COLUMNS + ["points"]
    ]
    selected_columns = base_columns + rolling_feature_columns

    home = team_form[team_form["is_home"]][selected_columns].copy()
    away = team_form[~team_form["is_home"]][selected_columns].copy()

    home = home.add_prefix("home_")
    away = away.add_prefix("away_")
    home = home.rename(columns={"home_match_id": "match_id"})
    away = away.rename(columns={"away_match_id": "match_id"})

    match_features = home.merge(away, on="match_id", how="inner")
    match_features["match_date"] = match_features["home_match_date"]
    match_features["target"] = match_features["home_result"]
    match_features = match_features.sort_values("match_date").reset_index(drop=True)
    return match_features


def write_and_upload_parquet(
    uploader: AzureBlobUploader,
    gold_dir: Path,
    table_name: str,
    competition: str,
    season: str,
    dataframe: pd.DataFrame,
) -> Path:
    local_path = gold_table_path(gold_dir, table_name, competition, season)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_parquet(local_path, index=False)

    blob_name = local_path.relative_to(gold_dir).as_posix()
    uploader.upload_file(blob_name=blob_name, local_path=str(local_path))
    logger.info("Wrote {} rows to {}", len(dataframe), blob_name)
    return local_path


def build_prematch_gold_dataset(competition: str, season: str, window: int) -> None:
    configure_local_cert_bundle()
    settings = load_settings()
    uploader = AzureBlobUploader(settings, container_name=settings.azure_storage_container_gold)

    team_match_path = gold_table_path(
        settings.local_gold_dir,
        "team_match_features",
        competition,
        season,
    )
    if not team_match_path.exists():
        raise FileNotFoundError(f"Missing Gold team features: {team_match_path}")

    team_match_features = pd.read_parquet(team_match_path)
    team_form = add_team_rolling_features(team_match_features, window)
    prematch_match_features = build_prematch_match_features(team_form, window)

    write_and_upload_parquet(
        uploader,
        settings.local_gold_dir,
        "prematch_team_form",
        competition,
        season,
        team_form,
    )
    write_and_upload_parquet(
        uploader,
        settings.local_gold_dir,
        "prematch_match_features",
        competition,
        season,
        prematch_match_features,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build pre-match Gold features from historical team form.")
    parser.add_argument("--competition", required=True)
    parser.add_argument("--season", required=True)
    parser.add_argument("--window", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()
    build_prematch_gold_dataset(args.competition, args.season, args.window)


if __name__ == "__main__":
    main()
