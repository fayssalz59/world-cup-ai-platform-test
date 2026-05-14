import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from ingestion.azure_blob import AzureBlobUploader
from ingestion.config import configure_local_cert_bundle, load_settings


def configure_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def nested(payload: dict[str, Any], *keys: str) -> Any:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def location_value(value: Any, index: int) -> float | None:
    if isinstance(value, list) and len(value) > index:
        return value[index]
    return None


def normalize_matches(matches: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for match in matches:
        rows.append(
            {
                "match_id": match.get("match_id"),
                "match_date": match.get("match_date"),
                "kick_off": match.get("kick_off"),
                "competition_id": nested(match, "competition", "competition_id"),
                "competition_name": nested(match, "competition", "competition_name"),
                "season_id": nested(match, "season", "season_id"),
                "season_name": nested(match, "season", "season_name"),
                "home_team_id": nested(match, "home_team", "home_team_id"),
                "home_team_name": nested(match, "home_team", "home_team_name"),
                "away_team_id": nested(match, "away_team", "away_team_id"),
                "away_team_name": nested(match, "away_team", "away_team_name"),
                "home_score": match.get("home_score"),
                "away_score": match.get("away_score"),
                "match_status": match.get("match_status"),
            }
        )
    return pd.DataFrame(rows)


def normalize_events(events_by_match: dict[int, list[dict[str, Any]]]) -> pd.DataFrame:
    rows = []
    for match_id, events in events_by_match.items():
        for event in events:
            location = event.get("location")
            rows.append(
                {
                    "match_id": match_id,
                    "event_id": event.get("id"),
                    "event_index": event.get("index"),
                    "period": event.get("period"),
                    "timestamp": event.get("timestamp"),
                    "minute": event.get("minute"),
                    "second": event.get("second"),
                    "type_id": nested(event, "type", "id"),
                    "type_name": nested(event, "type", "name"),
                    "possession": event.get("possession"),
                    "possession_team_id": nested(event, "possession_team", "id"),
                    "possession_team_name": nested(event, "possession_team", "name"),
                    "team_id": nested(event, "team", "id"),
                    "team_name": nested(event, "team", "name"),
                    "player_id": nested(event, "player", "id"),
                    "player_name": nested(event, "player", "name"),
                    "position_id": nested(event, "position", "id"),
                    "position_name": nested(event, "position", "name"),
                    "location_x": location_value(location, 0),
                    "location_y": location_value(location, 1),
                    "duration": event.get("duration"),
                    "under_pressure": event.get("under_pressure", False),
                }
            )
    return pd.DataFrame(rows)


def normalize_shots(events_by_match: dict[int, list[dict[str, Any]]]) -> pd.DataFrame:
    rows = []
    for match_id, events in events_by_match.items():
        for event in events:
            if nested(event, "type", "name") != "Shot":
                continue
            shot = event.get("shot", {})
            location = event.get("location")
            end_location = shot.get("end_location")
            rows.append(
                {
                    "match_id": match_id,
                    "event_id": event.get("id"),
                    "minute": event.get("minute"),
                    "second": event.get("second"),
                    "team_id": nested(event, "team", "id"),
                    "team_name": nested(event, "team", "name"),
                    "player_id": nested(event, "player", "id"),
                    "player_name": nested(event, "player", "name"),
                    "xg": shot.get("statsbomb_xg"),
                    "outcome": nested(shot, "outcome", "name"),
                    "body_part": nested(shot, "body_part", "name"),
                    "technique": nested(shot, "technique", "name"),
                    "location_x": location_value(location, 0),
                    "location_y": location_value(location, 1),
                    "end_location_x": location_value(end_location, 0),
                    "end_location_y": location_value(end_location, 1),
                    "end_location_z": location_value(end_location, 2),
                }
            )
    return pd.DataFrame(rows)


def normalize_passes(events_by_match: dict[int, list[dict[str, Any]]]) -> pd.DataFrame:
    rows = []
    for match_id, events in events_by_match.items():
        for event in events:
            if nested(event, "type", "name") != "Pass":
                continue
            pass_payload = event.get("pass", {})
            location = event.get("location")
            end_location = pass_payload.get("end_location")
            rows.append(
                {
                    "match_id": match_id,
                    "event_id": event.get("id"),
                    "minute": event.get("minute"),
                    "second": event.get("second"),
                    "team_id": nested(event, "team", "id"),
                    "team_name": nested(event, "team", "name"),
                    "player_id": nested(event, "player", "id"),
                    "player_name": nested(event, "player", "name"),
                    "recipient_id": nested(pass_payload, "recipient", "id"),
                    "recipient_name": nested(pass_payload, "recipient", "name"),
                    "length": pass_payload.get("length"),
                    "angle": pass_payload.get("angle"),
                    "height": nested(pass_payload, "height", "name"),
                    "outcome": nested(pass_payload, "outcome", "name"),
                    "body_part": nested(pass_payload, "body_part", "name"),
                    "location_x": location_value(location, 0),
                    "location_y": location_value(location, 1),
                    "end_location_x": location_value(end_location, 0),
                    "end_location_y": location_value(end_location, 1),
                }
            )
    return pd.DataFrame(rows)


def normalize_lineups(lineups_by_match: dict[int, list[dict[str, Any]]]) -> pd.DataFrame:
    rows = []
    for match_id, teams in lineups_by_match.items():
        for team in teams:
            for player in team.get("lineup", []):
                rows.append(
                    {
                        "match_id": match_id,
                        "team_id": team.get("team_id"),
                        "team_name": team.get("team_name"),
                        "player_id": player.get("player_id"),
                        "player_name": player.get("player_name"),
                        "player_nickname": player.get("player_nickname"),
                        "jersey_number": player.get("jersey_number"),
                        "country": nested(player, "country", "name"),
                        "positions": json.dumps(player.get("positions", []), ensure_ascii=False),
                    }
                )
    return pd.DataFrame(rows)


def latest_ingestion_path(base_dir: Path, file_name: str) -> Path:
    candidates = sorted(base_dir.glob(f"ingestion_date=*/{file_name}"))
    if not candidates:
        raise FileNotFoundError(f"No {file_name} found under {base_dir}")
    return candidates[-1]


def load_bronze_dataset(bronze_dir: Path, competition: str, season: str) -> tuple[list[dict[str, Any]], dict[int, list[dict[str, Any]]], dict[int, list[dict[str, Any]]]]:
    matches_path = latest_ingestion_path(
        bronze_dir / "statsbomb" / "matches" / f"competition={competition}" / f"season={season}",
        "matches.json",
    )
    matches = load_json(matches_path)
    match_ids = [int(match["match_id"]) for match in matches]

    events_by_match: dict[int, list[dict[str, Any]]] = {}
    lineups_by_match: dict[int, list[dict[str, Any]]] = {}
    for match_id in match_ids:
        events_base = bronze_dir / "statsbomb" / "events" / f"match_id={match_id}"
        lineups_base = bronze_dir / "statsbomb" / "lineups" / f"match_id={match_id}"
        try:
            events_by_match[match_id] = load_json(latest_ingestion_path(events_base, "events.json"))
        except FileNotFoundError:
            continue
        try:
            lineups_by_match[match_id] = load_json(latest_ingestion_path(lineups_base, "lineups.json"))
        except FileNotFoundError:
            pass

    return matches, events_by_match, lineups_by_match


def write_and_upload_parquet(
    uploader: AzureBlobUploader,
    silver_dir: Path,
    table_name: str,
    competition: str,
    season: str,
    dataframe: pd.DataFrame,
) -> Path:
    local_path = (
        silver_dir
        / "statsbomb"
        / table_name
        / f"competition={competition}"
        / f"season={season}"
        / f"{table_name}.parquet"
    )
    local_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_parquet(local_path, index=False)

    blob_name = local_path.relative_to(silver_dir).as_posix()
    uploader.upload_file(blob_name=blob_name, local_path=str(local_path))
    logger.info("Wrote {} rows to {}", len(dataframe), blob_name)
    return local_path


def build_silver_dataset(competition: str, season: str) -> None:
    configure_local_cert_bundle()
    settings = load_settings()
    uploader = AzureBlobUploader(settings, container_name=settings.azure_storage_container_silver)

    matches, events_by_match, lineups_by_match = load_bronze_dataset(
        bronze_dir=settings.local_bronze_dir,
        competition=competition,
        season=season,
    )

    tables = {
        "matches": normalize_matches(matches),
        "events": normalize_events(events_by_match),
        "shots": normalize_shots(events_by_match),
        "passes": normalize_passes(events_by_match),
        "lineups": normalize_lineups(lineups_by_match),
    }

    for table_name, dataframe in tables.items():
        if dataframe.empty:
            logger.warning("Skipping empty Silver table {}", table_name)
            continue
        write_and_upload_parquet(
            uploader=uploader,
            silver_dir=settings.local_silver_dir,
            table_name=table_name,
            competition=competition,
            season=season,
            dataframe=dataframe,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build StatsBomb Silver Parquet datasets.")
    parser.add_argument("--competition", required=True, help="Bronze competition partition, e.g. world_cup")
    parser.add_argument("--season", required=True, help="Bronze season partition, e.g. 2022")
    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()
    build_silver_dataset(competition=args.competition, season=args.season)


if __name__ == "__main__":
    main()
