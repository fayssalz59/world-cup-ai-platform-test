# Day 3 Silver Layer

## Goal

Transform raw StatsBomb Bronze JSON into clean Silver Parquet datasets.

## Silver Tables

- `matches`
- `events`
- `shots`
- `passes`
- `lineups`

## Run

World Cup 2022:

```powershell
python -m transformation.statsbomb_silver --competition world_cup --season 2022
```

Champions League 2018/2019:

```powershell
python -m transformation.statsbomb_silver --competition champions_league --season 2018_2019
```

## Output

Local ignored files:

```text
data/silver/statsbomb/<table>/competition=<competition>/season=<season>/<table>.parquet
```

Azure Blob Storage:

```text
silver/statsbomb/<table>/competition=<competition>/season=<season>/<table>.parquet
```

## Notes

- Bronze keeps raw JSON.
- Silver is analytics-ready Parquet.
- Gold will use Silver to build ML and business features.
