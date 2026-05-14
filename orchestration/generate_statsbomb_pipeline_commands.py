import argparse
from datetime import UTC, datetime

from ingestion.config import DEFAULT_STATSBOMB_BASE_URL, configure_local_cert_bundle
from ingestion.ingest_statsbomb_open_data import infer_competition_slug
from ingestion.statsbomb_client import StatsBombOpenDataClient


def dataset_key(competition: dict) -> str:
    competition_slug, season_slug = infer_competition_slug(
        competition_id=competition["competition_id"],
        season_id=competition["season_id"],
        competitions=[competition],
    )
    return f"{competition_slug}:{season_slug}"


def generate_commands(limit: int | None, ingestion_date: str, max_event_matches: int) -> list[str]:
    configure_local_cert_bundle()
    client = StatsBombOpenDataClient(DEFAULT_STATSBOMB_BASE_URL)
    competitions = client.get_competitions()
    competitions = sorted(
        competitions,
        key=lambda item: (
            item["competition_name"],
            item["season_name"],
            item["competition_id"],
            item["season_id"],
        ),
    )
    if limit is not None:
        competitions = competitions[:limit]

    commands: list[str] = []
    datasets: list[str] = []
    for competition in competitions:
        competition_slug, season_slug = dataset_key(competition).split(":", maxsplit=1)
        datasets.append(f"{competition_slug}:{season_slug}")
        commands.extend(
            [
                (
                    "python -m ingestion.ingest_statsbomb_open_data "
                    f"--competition-id {competition['competition_id']} "
                    f"--season-id {competition['season_id']} "
                    f"--max-event-matches {max_event_matches} "
                    f"--ingestion-date {ingestion_date} "
                    "--include-lineups"
                ),
                (f"python -m transformation.statsbomb_silver --competition {competition_slug} --season {season_slug}"),
                (f"python -m transformation.statsbomb_gold --competition {competition_slug} --season {season_slug}"),
            ]
        )

    model_command = "python -m ml.train_match_result_model " + " ".join(
        f"--dataset {dataset}" for dataset in sorted(set(datasets))
    )
    commands.append(model_command)
    return commands


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate PowerShell commands for the full StatsBomb Bronze/Silver/Gold/ML pipeline."
    )
    parser.add_argument("--limit", type=int, default=None, help="Generate commands for only the first N datasets.")
    parser.add_argument(
        "--ingestion-date",
        default=datetime.now(UTC).strftime("%Y-%m-%d"),
        help="Bronze ingestion_date partition.",
    )
    parser.add_argument(
        "--max-event-matches",
        type=int,
        default=9999,
        help="High value means ingest every match in each StatsBomb season.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    for command in generate_commands(
        limit=args.limit,
        ingestion_date=args.ingestion_date,
        max_event_matches=args.max_event_matches,
    ):
        print(command)


if __name__ == "__main__":
    main()
