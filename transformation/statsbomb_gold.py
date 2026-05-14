import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
from loguru import logger

from ingestion.azure_blob import AzureBlobUploader
from ingestion.config import configure_local_cert_bundle, load_settings


def configure_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def silver_table_path(silver_dir: Path, table_name: str, competition: str, season: str) -> Path:
    return (
        silver_dir
        / "statsbomb"
        / table_name
        / f"competition={competition}"
        / f"season={season}"
        / f"{table_name}.parquet"
    )


def load_silver_tables(silver_dir: Path, competition: str, season: str) -> dict[str, pd.DataFrame]:
    tables = {}
    for table_name in ["matches", "shots", "passes"]:
        path = silver_table_path(silver_dir, table_name, competition, season)
        if not path.exists():
            raise FileNotFoundError(f"Missing Silver table: {path}")
        tables[table_name] = pd.read_parquet(path)
    return tables


def build_team_match_features(
    matches: pd.DataFrame,
    shots: pd.DataFrame,
    passes: pd.DataFrame,
) -> pd.DataFrame:
    teams = []
    for _, match in matches.iterrows():
        teams.append(
            {
                "match_id": match["match_id"],
                "match_date": match.get("match_date"),
                "team_id": match["home_team_id"],
                "team_name": match["home_team_name"],
                "opponent_team_id": match["away_team_id"],
                "opponent_team_name": match["away_team_name"],
                "is_home": True,
                "goals_for": match["home_score"],
                "goals_against": match["away_score"],
            }
        )
        teams.append(
            {
                "match_id": match["match_id"],
                "match_date": match.get("match_date"),
                "team_id": match["away_team_id"],
                "team_name": match["away_team_name"],
                "opponent_team_id": match["home_team_id"],
                "opponent_team_name": match["home_team_name"],
                "is_home": False,
                "goals_for": match["away_score"],
                "goals_against": match["home_score"],
            }
        )
    team_features = pd.DataFrame(teams)

    shot_features = (
        shots.groupby(["match_id", "team_id", "team_name"], dropna=False)
        .agg(shots=("event_id", "count"), xg=("xg", "sum"), goals_from_shots=("outcome", lambda s: (s == "Goal").sum()))
        .reset_index()
    )
    pass_features = (
        passes.groupby(["match_id", "team_id", "team_name"], dropna=False)
        .agg(passes=("event_id", "count"), completed_passes=("outcome", lambda s: s.isna().sum()))
        .reset_index()
    )

    team_features = team_features.merge(
        shot_features,
        on=["match_id", "team_id", "team_name"],
        how="left",
    ).merge(
        pass_features,
        on=["match_id", "team_id", "team_name"],
        how="left",
    )

    for column in ["shots", "xg", "goals_from_shots", "passes", "completed_passes"]:
        team_features[column] = team_features[column].fillna(0)

    team_features["goal_difference"] = team_features["goals_for"] - team_features["goals_against"]
    team_features["pass_completion_rate"] = team_features["completed_passes"] / team_features["passes"].replace(0, pd.NA)
    team_features["result"] = team_features["goal_difference"].apply(
        lambda value: "win" if value > 0 else "draw" if value == 0 else "loss"
    )
    return team_features


def build_match_features(team_match_features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for match_id, match_rows in team_match_features.groupby("match_id"):
        home = match_rows[match_rows["is_home"]].iloc[0]
        away = match_rows[~match_rows["is_home"]].iloc[0]
        rows.append(
            {
                "match_id": match_id,
                "match_date": home["match_date"],
                "home_team_name": home["team_name"],
                "away_team_name": away["team_name"],
                "home_goals": home["goals_for"],
                "away_goals": away["goals_for"],
                "home_xg": home["xg"],
                "away_xg": away["xg"],
                "home_shots": home["shots"],
                "away_shots": away["shots"],
                "home_passes": home["passes"],
                "away_passes": away["passes"],
                "xg_difference_home": home["xg"] - away["xg"],
                "shot_difference_home": home["shots"] - away["shots"],
                "target": home["result"],
            }
        )
    return pd.DataFrame(rows)


def write_and_upload_parquet(
    uploader: AzureBlobUploader,
    gold_dir: Path,
    table_name: str,
    competition: str,
    season: str,
    dataframe: pd.DataFrame,
) -> Path:
    local_path = (
        gold_dir
        / "statsbomb"
        / table_name
        / f"competition={competition}"
        / f"season={season}"
        / f"{table_name}.parquet"
    )
    local_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_parquet(local_path, index=False)

    blob_name = local_path.relative_to(gold_dir).as_posix()
    uploader.upload_file(blob_name=blob_name, local_path=str(local_path))
    logger.info("Wrote {} rows to {}", len(dataframe), blob_name)
    return local_path


def build_gold_dataset(competition: str, season: str) -> None:
    configure_local_cert_bundle()
    settings = load_settings()
    uploader = AzureBlobUploader(settings, container_name=settings.azure_storage_container_gold)
    tables = load_silver_tables(settings.local_silver_dir, competition, season)

    team_match_features = build_team_match_features(
        matches=tables["matches"],
        shots=tables["shots"],
        passes=tables["passes"],
    )
    match_features = build_match_features(team_match_features)

    write_and_upload_parquet(
        uploader,
        settings.local_gold_dir,
        "team_match_features",
        competition,
        season,
        team_match_features,
    )
    write_and_upload_parquet(
        uploader,
        settings.local_gold_dir,
        "match_features",
        competition,
        season,
        match_features,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build StatsBomb Gold feature datasets.")
    parser.add_argument("--competition", required=True)
    parser.add_argument("--season", required=True)
    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()
    build_gold_dataset(competition=args.competition, season=args.season)


if __name__ == "__main__":
    main()
