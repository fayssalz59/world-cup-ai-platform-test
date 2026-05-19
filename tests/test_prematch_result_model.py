import pandas as pd

from ml.train_prematch_result_model import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_model,
    prepare_training_frame,
    split_dataset,
)


def sample_prematch_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for index, target in enumerate(["win", "loss", "draw", "win", "loss", "draw"]):
        row: dict[str, object] = {column: float(index + 1) for column in FEATURE_COLUMNS}
        row["home_prematch_matches_played_before"] = index
        row["away_prematch_matches_played_before"] = index
        row[TARGET_COLUMN] = target
        rows.append(row)
    return pd.DataFrame(rows)


def test_prepare_training_frame_filters_min_history() -> None:
    prepared = prepare_training_frame(sample_prematch_frame(), min_history=2)

    assert len(prepared) == 4
    assert prepared["home_prematch_matches_played_before"].min() >= 2
    assert list(prepared.columns) == [*FEATURE_COLUMNS, TARGET_COLUMN]


def test_prematch_model_can_fit_small_dataset() -> None:
    dataframe = pd.concat([sample_prematch_frame()] * 4, ignore_index=True)
    prepared = prepare_training_frame(dataframe, min_history=1)
    x_train, x_test, y_train, _ = split_dataset(prepared, test_size=0.25, random_state=42)
    model = build_model(random_state=42)

    model.fit(x_train, y_train)

    assert len(model.predict(x_test)) == len(x_test)
