import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

from loguru import logger

from ingestion.config import DEFAULT_STATSBOMB_BASE_URL, configure_local_cert_bundle
from ingestion.ingest_statsbomb_open_data import (
    infer_competition_slug,
    ingest_statsbomb_open_data,
)
from ingestion.statsbomb_client import StatsBombOpenDataClient
from ml.train_match_result_model import train_match_result_model
from ml.train_prematch_result_model import train_prematch_result_model
from transformation.statsbomb_gold import build_gold_dataset
from transformation.statsbomb_prematch import build_prematch_gold_dataset
from transformation.statsbomb_silver import build_silver_dataset


def get_available_datasets(limit: int | None = None, selected_datasets: list[str] | None = None) -> list[dict]:
    configure_local_cert_bundle()
    client = StatsBombOpenDataClient(DEFAULT_STATSBOMB_BASE_URL)
    competitions = sorted(
        client.get_competitions(),
        key=lambda item: (
            item["competition_name"],
            item["season_name"],
            item["competition_id"],
            item["season_id"],
        ),
    )
    if limit is not None:
        competitions = competitions[:limit]
    if selected_datasets:
        selected = set(selected_datasets)
        competitions = [
            competition for competition in competitions if dataset_key_from_competition(competition) in selected
        ]
    return competitions


def dataset_key_from_competition(competition: dict) -> str:
    competition_slug, season_slug = infer_competition_slug(
        competition_id=competition["competition_id"],
        season_id=competition["season_id"],
        competitions=[competition],
    )
    return f"{competition_slug}:{season_slug}"


def dataset_metadata(competition: dict) -> dict:
    competition_slug, season_slug = dataset_key_from_competition(competition).split(":", maxsplit=1)
    return {
        "competition_id": competition["competition_id"],
        "season_id": competition["season_id"],
        "competition_slug": competition_slug,
        "season_slug": season_slug,
        "dataset": f"{competition_slug}:{season_slug}",
    }


def ingest_one(dataset: dict, ingestion_date: str, max_event_matches: int, include_lineups: bool) -> dict:
    logger.info(
        "Bronze start {}:{}",
        dataset["competition_id"],
        dataset["season_id"],
    )
    ingest_statsbomb_open_data(
        competition_id=dataset["competition_id"],
        season_id=dataset["season_id"],
        include_lineups=include_lineups,
        max_event_matches=max_event_matches,
        ingestion_date=ingestion_date,
    )
    logger.info("Bronze done {}", dataset["dataset"])
    return dataset


def run_ingestion(
    datasets: list[dict],
    ingestion_date: str,
    max_event_matches: int,
    include_lineups: bool,
    workers: int,
) -> None:
    if workers <= 1:
        for dataset in datasets:
            ingest_one(dataset, ingestion_date, max_event_matches, include_lineups)
        return

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                ingest_one,
                dataset,
                ingestion_date,
                max_event_matches,
                include_lineups,
            )
            for dataset in datasets
        ]
        for future in as_completed(futures):
            future.result()


def run_silver(datasets: list[dict]) -> None:
    for dataset in datasets:
        logger.info("Silver start {}", dataset["dataset"])
        build_silver_dataset(dataset["competition_slug"], dataset["season_slug"])
        logger.info("Silver done {}", dataset["dataset"])


def run_gold(datasets: list[dict]) -> None:
    for dataset in datasets:
        logger.info("Gold start {}", dataset["dataset"])
        build_gold_dataset(dataset["competition_slug"], dataset["season_slug"])
        logger.info("Gold done {}", dataset["dataset"])


def run_prematch_gold(datasets: list[dict], window: int) -> None:
    for dataset in datasets:
        logger.info("Pre-match Gold start {}", dataset["dataset"])
        build_prematch_gold_dataset(
            dataset["competition_slug"],
            dataset["season_slug"],
            window=window,
        )
        logger.info("Pre-match Gold done {}", dataset["dataset"])


def run_pipeline(
    limit: int | None,
    selected_datasets: list[str] | None,
    ingestion_date: str,
    max_event_matches: int,
    include_lineups: bool,
    workers: int,
    skip_bronze: bool,
    skip_silver: bool,
    skip_gold: bool,
    skip_prematch_gold: bool,
    skip_ml: bool,
    skip_prematch_ml: bool,
    dry_run: bool,
    prematch_window: int,
    prematch_min_history: int,
) -> list[str]:
    datasets = [
        dataset_metadata(item) for item in get_available_datasets(limit=limit, selected_datasets=selected_datasets)
    ]
    dataset_keys = sorted({dataset["dataset"] for dataset in datasets})

    logger.info("Datasets selected: {}", len(datasets))
    for dataset in datasets:
        logger.info(
            "{}:{} -> {}",
            dataset["competition_id"],
            dataset["season_id"],
            dataset["dataset"],
        )

    if dry_run:
        return dataset_keys

    if not skip_bronze:
        run_ingestion(datasets, ingestion_date, max_event_matches, include_lineups, workers)
    if not skip_silver:
        run_silver(datasets)
    if not skip_gold:
        run_gold(datasets)
    if not skip_prematch_gold:
        run_prematch_gold(datasets, window=prematch_window)
    if not skip_ml:
        train_match_result_model(
            datasets=dataset_keys,
            test_size=0.25,
            random_state=42,
        )
    if not skip_prematch_ml:
        train_prematch_result_model(
            datasets=dataset_keys,
            min_history=prematch_min_history,
            test_size=0.25,
            random_state=42,
        )
    return dataset_keys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full StatsBomb Bronze/Silver/Gold/ML pipeline.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--dataset",
        action="append",
        default=None,
        help="Only run selected dataset key, e.g. world_cup:2022. Can be repeated.",
    )
    parser.add_argument(
        "--ingestion-date",
        default=datetime.now(UTC).strftime("%Y-%m-%d"),
    )
    parser.add_argument("--max-event-matches", type=int, default=9999)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--skip-bronze", action="store_true")
    parser.add_argument("--skip-silver", action="store_true")
    parser.add_argument("--skip-gold", action="store_true")
    parser.add_argument("--skip-prematch-gold", action="store_true")
    parser.add_argument("--skip-ml", action="store_true")
    parser.add_argument("--skip-prematch-ml", action="store_true")
    parser.add_argument("--no-lineups", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--prematch-window", type=int, default=5)
    parser.add_argument("--prematch-min-history", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_pipeline(
        limit=args.limit,
        selected_datasets=args.dataset,
        ingestion_date=args.ingestion_date,
        max_event_matches=args.max_event_matches,
        include_lineups=not args.no_lineups,
        workers=args.workers,
        skip_bronze=args.skip_bronze,
        skip_silver=args.skip_silver,
        skip_gold=args.skip_gold,
        skip_prematch_gold=args.skip_prematch_gold,
        skip_ml=args.skip_ml,
        skip_prematch_ml=args.skip_prematch_ml,
        dry_run=args.dry_run,
        prematch_window=args.prematch_window,
        prematch_min_history=args.prematch_min_history,
    )


if __name__ == "__main__":
    main()
