import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger
from tqdm import tqdm

from ingestion.azure_blob import AzureBlobUploader
from ingestion.config import configure_local_cert_bundle, load_settings
from ingestion.statsbomb_client import StatsBombOpenDataClient


def configure_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def as_pretty_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def write_local_json(local_bronze_dir: Path, blob_name: str, content: str) -> Path:
    local_path = local_bronze_dir / blob_name
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(content, encoding="utf-8")
    return local_path


def persist_raw_json(
    uploader: AzureBlobUploader,
    local_bronze_dir: Path,
    blob_name: str,
    data: Any,
) -> None:
    content = as_pretty_json(data)
    local_path = write_local_json(local_bronze_dir, blob_name, content)
    uploader.upload_text(blob_name=blob_name, content=content)
    logger.info("Uploaded {} from {}", blob_name, local_path)


def match_id_from_match(match: dict[str, Any]) -> int:
    match_id = match.get("match_id")
    if not isinstance(match_id, int):
        raise ValueError(f"Invalid match payload without integer match_id: {match}")
    return match_id


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def infer_competition_slug(competition_id: int, season_id: int, competitions: list[dict[str, Any]]) -> tuple[str, str]:
    for competition in competitions:
        if (
            competition.get("competition_id") == competition_id
            and competition.get("season_id") == season_id
        ):
            competition_name = str(competition["competition_name"])
            season_name = str(competition["season_name"])
            if competition_name == "FIFA World Cup":
                return "world_cup", slugify(season_name)
            return slugify(competition_name), slugify(season_name)
    return f"competition_{competition_id}", f"season_{season_id}"


def bronze_paths(
    competition_slug: str,
    season_slug: str,
    ingestion_date: str,
    match_id: int | None = None,
) -> dict[str, str]:
    paths = {
        "competitions": (
            "statsbomb/competitions/"
            f"ingestion_date={ingestion_date}/"
            "competitions.json"
        ),
        "matches": (
            "statsbomb/matches/"
            f"competition={competition_slug}/"
            f"season={season_slug}/"
            f"ingestion_date={ingestion_date}/"
            "matches.json"
        ),
    }
    if match_id is not None:
        paths["events"] = (
            "statsbomb/events/"
            f"match_id={match_id}/"
            f"ingestion_date={ingestion_date}/"
            "events.json"
        )
        paths["lineups"] = (
            "statsbomb/lineups/"
            f"match_id={match_id}/"
            f"ingestion_date={ingestion_date}/"
            "lineups.json"
        )
    return paths


def ingest_statsbomb_open_data(
    competition_id: int,
    season_id: int,
    include_lineups: bool,
    max_event_matches: int,
    ingestion_date: str,
) -> None:
    configure_local_cert_bundle()
    settings = load_settings()
    statsbomb_client = StatsBombOpenDataClient(settings.statsbomb_base_url)
    uploader = AzureBlobUploader(settings)

    logger.info("Fetching StatsBomb competitions")
    competitions = statsbomb_client.get_competitions()
    competition_slug, season_slug = infer_competition_slug(
        competition_id=competition_id,
        season_id=season_id,
        competitions=competitions,
    )
    logger.info("Using Bronze partition competition={} season={}", competition_slug, season_slug)
    persist_raw_json(
        uploader=uploader,
        local_bronze_dir=settings.local_bronze_dir,
        blob_name=bronze_paths(competition_slug, season_slug, ingestion_date)["competitions"],
        data=competitions,
    )

    logger.info(
        "Fetching StatsBomb matches for competition_id={} season_id={}",
        competition_id,
        season_id,
    )
    matches = statsbomb_client.get_matches(
        competition_id=competition_id,
        season_id=season_id,
    )
    persist_raw_json(
        uploader=uploader,
        local_bronze_dir=settings.local_bronze_dir,
        blob_name=bronze_paths(competition_slug, season_slug, ingestion_date)["matches"],
        data=matches,
    )

    selected_matches = matches[:max_event_matches]
    logger.info("Fetching events for {} match(es)", len(selected_matches))
    for match in tqdm(selected_matches, desc="StatsBomb events"):
        match_id = match_id_from_match(match)
        match_paths = bronze_paths(competition_slug, season_slug, ingestion_date, match_id)
        events = statsbomb_client.get_events(match_id)
        persist_raw_json(
            uploader=uploader,
            local_bronze_dir=settings.local_bronze_dir,
            blob_name=match_paths["events"],
            data=events,
        )

        if include_lineups:
            lineups = statsbomb_client.get_lineups(match_id)
            persist_raw_json(
                uploader=uploader,
                local_bronze_dir=settings.local_bronze_dir,
                blob_name=match_paths["lineups"],
                data=lineups,
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest StatsBomb Open Data raw JSON into Azure Bronze.",
    )
    parser.add_argument("--competition-id", type=int, default=43)
    parser.add_argument("--season-id", type=int, default=106)
    parser.add_argument(
        "--max-event-matches",
        type=int,
        default=1,
        help="Number of matches for which event JSON should be uploaded.",
    )
    parser.add_argument(
        "--include-lineups",
        action="store_true",
        help="Also upload lineup JSON for selected matches.",
    )
    parser.add_argument(
        "--ingestion-date",
        default=None,
        help="Partition date in YYYY-MM-DD. Defaults to today's UTC date.",
    )
    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()
    ingest_statsbomb_open_data(
        competition_id=args.competition_id,
        season_id=args.season_id,
        include_lineups=args.include_lineups,
        max_event_matches=args.max_event_matches,
        ingestion_date=args.ingestion_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    )


if __name__ == "__main__":
    main()
