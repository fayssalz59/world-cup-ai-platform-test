import argparse
import json
import logging
from pathlib import Path
from typing import Any

from ingestion.azure_blob import AzureBlobUploader
from ingestion.config import configure_local_cert_bundle, load_settings
from ingestion.statsbomb_client import StatsBombOpenDataClient


logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
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
    logger.info("Uploaded %s from %s", blob_name, local_path)


def match_id_from_match(match: dict[str, Any]) -> int:
    match_id = match.get("match_id")
    if not isinstance(match_id, int):
        raise ValueError(f"Invalid match payload without integer match_id: {match}")
    return match_id


def ingest_statsbomb_open_data(
    competition_id: int,
    season_id: int,
    include_lineups: bool,
    max_event_matches: int,
) -> None:
    configure_local_cert_bundle()
    settings = load_settings()
    statsbomb_client = StatsBombOpenDataClient(settings.statsbomb_base_url)
    uploader = AzureBlobUploader(settings)

    logger.info("Fetching StatsBomb competitions")
    competitions = statsbomb_client.get_competitions()
    persist_raw_json(
        uploader=uploader,
        local_bronze_dir=settings.local_bronze_dir,
        blob_name="statsbomb/open-data/competitions/competitions.json",
        data=competitions,
    )

    logger.info(
        "Fetching StatsBomb matches for competition_id=%s season_id=%s",
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
        blob_name=f"statsbomb/open-data/matches/{competition_id}/{season_id}.json",
        data=matches,
    )

    selected_matches = matches[:max_event_matches]
    logger.info("Fetching events for %s match(es)", len(selected_matches))
    for match in selected_matches:
        match_id = match_id_from_match(match)
        events = statsbomb_client.get_events(match_id)
        persist_raw_json(
            uploader=uploader,
            local_bronze_dir=settings.local_bronze_dir,
            blob_name=f"statsbomb/open-data/events/{match_id}.json",
            data=events,
        )

        if include_lineups:
            lineups = statsbomb_client.get_lineups(match_id)
            persist_raw_json(
                uploader=uploader,
                local_bronze_dir=settings.local_bronze_dir,
                blob_name=f"statsbomb/open-data/lineups/{match_id}.json",
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
    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()
    ingest_statsbomb_open_data(
        competition_id=args.competition_id,
        season_id=args.season_id,
        include_lineups=args.include_lineups,
        max_event_matches=args.max_event_matches,
    )


if __name__ == "__main__":
    main()
