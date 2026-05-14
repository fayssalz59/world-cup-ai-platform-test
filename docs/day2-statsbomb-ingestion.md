# Day 2 StatsBomb Ingestion

## Goal

Ingest raw StatsBomb Open Data JSON into the Azure Blob Storage Bronze layer.

StatsBomb Open Data is provided as JSON files with this structure:

- `competitions.json`
- `matches/{competition_id}/{season_id}.json`
- `events/{match_id}.json`
- `lineups/{match_id}.json`
- `three-sixty/{match_id}.json`

## Default Dataset

The default command targets:

```text
competition_id=43
season_id=106
```

This is intended as the first World Cup dataset for the project.

## Run

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run a small Bronze ingestion smoke test:

```powershell
python -m ingestion.ingest_statsbomb_open_data --competition-id 43 --season-id 106 --max-event-matches 1 --include-lineups
```

Expected Bronze blobs:

```text
statsbomb/open-data/competitions/competitions.json
statsbomb/open-data/matches/43/106.json
statsbomb/open-data/events/<match_id>.json
statsbomb/open-data/lineups/<match_id>.json
```

Local ignored copies are also written under:

```text
data/bronze/statsbomb/open-data/
```

## Notes

- Bronze data stays raw and close to the source payload.
- The `data/` folder is ignored by Git.
- Silver and Gold transformations will start from these Bronze JSON files.
