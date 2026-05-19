# Day 6 Pre-Match Gold Features

## Goal

Create prediction-safe Gold features that are known before kickoff.

## Why

Post-match features such as match xG explain what happened. Pre-match features use only historical matches before the current match, so they can be used for real prediction.

## Tables

- `prematch_team_form`: one row per team per match with rolling historical form
- `prematch_match_features`: one row per match with home/away pre-match features

## Features

For each team:

- average goals for last N matches
- average goals against last N matches
- average goal difference last N matches
- average xG last N matches
- average shots last N matches
- average passes last N matches
- average completed passes last N matches
- average points last N matches
- win rate last N matches
- unbeaten rate last N matches
- matches played before this match

## Run

```powershell
python -m transformation.statsbomb_prematch --competition world_cup --season 2022 --window 5
```

```powershell
python -m transformation.statsbomb_prematch --competition champions_league --season 2018_2019 --window 5
```

## Output

```text
gold/statsbomb/prematch_team_form/competition=<competition>/season=<season>/prematch_team_form.parquet
gold/statsbomb/prematch_match_features/competition=<competition>/season=<season>/prematch_match_features.parquet
```

## Anti-Leakage Rule

Every rolling feature uses `shift(1)` before rolling, so the current match is never used to predict itself.
