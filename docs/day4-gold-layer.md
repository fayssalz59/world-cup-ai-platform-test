# Day 4 Gold Layer

## Goal

Build business and ML-ready features from Silver Parquet datasets.

## Gold Tables

- `team_match_features`: one row per team per match
- `match_features`: one row per match, suitable as a first ML dataset

## Features

`team_match_features` includes:

- goals for and against
- xG
- shot count
- goals from shots
- pass count
- completed passes
- pass completion rate
- result: win, draw or loss

`match_features` includes:

- home and away teams
- home and away goals
- home and away xG
- home and away shots
- home and away passes
- home xG difference
- home shot difference
- target result

## Run

World Cup 2022:

```powershell
python -m transformation.statsbomb_gold --competition world_cup --season 2022
```

Champions League 2018/2019:

```powershell
python -m transformation.statsbomb_gold --competition champions_league --season 2018_2019
```

## Output

Local ignored files:

```text
data/gold/statsbomb/<table>/competition=<competition>/season=<season>/<table>.parquet
```

Azure Blob Storage:

```text
gold/statsbomb/<table>/competition=<competition>/season=<season>/<table>.parquet
```
