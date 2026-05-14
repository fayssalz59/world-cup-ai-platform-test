# Day 5 ML Baseline

## Goal

Train a first measurable model from Gold match features.

## Important Limitation

This is a post-match analytical baseline. It uses features such as xG, shots and passes, which are only known after the match.

It is useful to validate the ML pipeline, metrics, model persistence and inference shape. It is not yet a true pre-match prediction model.

## Train

```powershell
python -m ml.train_match_result_model `
  --dataset world_cup:2022 `
  --dataset champions_league:2018_2019
```

## Inputs

Gold table:

```text
data/gold/statsbomb/match_features/competition=<competition>/season=<season>/match_features.parquet
```

Features:

- home_xg
- away_xg
- home_shots
- away_shots
- home_passes
- away_passes
- xg_difference_home
- shot_difference_home

Target:

- win
- draw
- loss

## Outputs

Ignored local artifacts:

```text
models/match_result_baseline.joblib
reports/match_result_baseline_metrics.json
```

## Next Step

To build a true pre-match model, create historical team-form features that are known before kickoff:

- rolling xG for last N matches
- rolling goals for and against
- rolling shots
- home/away indicators
- team strength features
