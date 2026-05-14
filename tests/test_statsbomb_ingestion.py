import json

import pytest

from ingestion.ingest_statsbomb_open_data import (
    as_pretty_json,
    bronze_paths,
    infer_competition_slug,
    match_id_from_match,
    slugify,
    write_local_json,
)
from ingestion.statsbomb_client import StatsBombOpenDataClient


def test_statsbomb_client_builds_raw_github_url() -> None:
    client = StatsBombOpenDataClient("https://example.com/data/")

    assert (
        client.url_for("matches/43/106.json")
        == "https://example.com/data/matches/43/106.json"
    )


def test_as_pretty_json_keeps_valid_json() -> None:
    content = as_pretty_json({"team": "Morocco", "goals": 2})

    assert json.loads(content) == {"team": "Morocco", "goals": 2}
    assert "\n" in content


def test_write_local_json_uses_blob_name_as_relative_path(tmp_path) -> None:
    path = write_local_json(
        local_bronze_dir=tmp_path,
        blob_name="statsbomb/open-data/competitions/competitions.json",
        content='{"ok": true}',
    )

    assert path == tmp_path / "statsbomb/open-data/competitions/competitions.json"
    assert path.read_text(encoding="utf-8") == '{"ok": true}'


def test_match_id_from_match_returns_integer_match_id() -> None:
    assert match_id_from_match({"match_id": 3869685}) == 3869685


def test_match_id_from_match_rejects_missing_match_id() -> None:
    with pytest.raises(ValueError):
        match_id_from_match({"home_team": "France"})


def test_bronze_paths_are_partitioned_for_data_lake() -> None:
    paths = bronze_paths(
        competition_slug="world_cup",
        season_slug="2022",
        ingestion_date="2026-05-14",
        match_id=3857256,
    )

    assert paths["competitions"] == (
        "statsbomb/competitions/ingestion_date=2026-05-14/competitions.json"
    )
    assert paths["matches"] == (
        "statsbomb/matches/competition=world_cup/season=2022/"
        "ingestion_date=2026-05-14/matches.json"
    )
    assert paths["events"] == (
        "statsbomb/events/match_id=3857256/ingestion_date=2026-05-14/events.json"
    )


def test_slugify_makes_path_safe_values() -> None:
    assert slugify("Champions League") == "champions_league"
    assert slugify("2018/2019") == "2018_2019"


def test_infer_competition_slug_keeps_world_cup_label_concise() -> None:
    competitions = [
        {
            "competition_id": 43,
            "season_id": 106,
            "competition_name": "FIFA World Cup",
            "season_name": "2022",
        }
    ]

    assert infer_competition_slug(43, 106, competitions) == ("world_cup", "2022")
