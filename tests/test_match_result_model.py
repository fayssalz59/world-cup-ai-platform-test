import pandas as pd

from ml.train_match_result_model import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_model,
    prepare_training_frame,
    split_dataset,
)


def sample_ml_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "home_xg": 1.2,
                "away_xg": 0.4,
                "home_shots": 10,
                "away_shots": 4,
                "home_passes": 500,
                "away_passes": 300,
                "xg_difference_home": 0.8,
                "shot_difference_home": 6,
                "target": "win",
            },
            {
                "home_xg": 0.3,
                "away_xg": 1.1,
                "home_shots": 4,
                "away_shots": 11,
                "home_passes": 250,
                "away_passes": 450,
                "xg_difference_home": -0.8,
                "shot_difference_home": -7,
                "target": "loss",
            },
            {
                "home_xg": 0.7,
                "away_xg": 0.7,
                "home_shots": 8,
                "away_shots": 8,
                "home_passes": 350,
                "away_passes": 360,
                "xg_difference_home": 0.0,
                "shot_difference_home": 0,
                "target": "draw",
            },
        ]
    )


def test_prepare_training_frame_keeps_only_model_columns() -> None:
    dataframe = sample_ml_frame()
    dataframe["extra"] = "ignored"

    prepared = prepare_training_frame(dataframe)

    assert list(prepared.columns) == FEATURE_COLUMNS + [TARGET_COLUMN]


def test_build_model_can_fit_small_dataset() -> None:
    dataframe = pd.concat([sample_ml_frame()] * 4, ignore_index=True)
    x_train, x_test, y_train, _ = split_dataset(dataframe, test_size=0.25, random_state=42)
    model = build_model(random_state=42)

    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    assert len(predictions) == len(x_test)
