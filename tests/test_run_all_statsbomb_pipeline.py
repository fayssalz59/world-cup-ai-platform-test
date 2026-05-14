from orchestration.run_all_statsbomb_pipeline import dataset_key_from_competition, dataset_metadata


def test_dataset_metadata_uses_readable_dataset_key() -> None:
    metadata = dataset_metadata(
        {
            "competition_id": 16,
            "season_id": 4,
            "competition_name": "Champions League",
            "season_name": "2018/2019",
        }
    )

    assert metadata["competition_slug"] == "champions_league"
    assert metadata["season_slug"] == "2018_2019"
    assert metadata["dataset"] == "champions_league:2018_2019"


def test_dataset_key_from_competition() -> None:
    assert (
        dataset_key_from_competition(
            {
                "competition_id": 43,
                "season_id": 106,
                "competition_name": "FIFA World Cup",
                "season_name": "2022",
            }
        )
        == "world_cup:2022"
    )
