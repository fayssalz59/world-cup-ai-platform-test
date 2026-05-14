# Day 7 Pre-Match Model

## Goal

Train a match-result model using only pre-match rolling features.

Unlike the previous post-match baseline, this model does not use current-match xG, shots or passes.

## Train

```powershell
python -m ml.train_prematch_result_model `
  --dataset world_cup:2022 `
  --dataset champions_league:2018_2019 `
  --min-history 1
```

## Features

The model uses home and away rolling features known before kickoff:

- average goals for last 5 matches
- average goals against last 5 matches
- average goal difference last 5 matches
- average xG last 5 matches
- average shots last 5 matches
- average passes last 5 matches
- average completed passes last 5 matches
- average points last 5 matches
- win rate last 5 matches
- unbeaten rate last 5 matches
- matches played before

## Outputs

```text
models/prematch_result_baseline.joblib
reports/prematch_result_baseline_metrics.json
```

## Expected Behavior

This model may score lower than the post-match model, but it is more honest for future match prediction.
