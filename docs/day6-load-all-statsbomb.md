# Load All StatsBomb Open Data

## Goal

Generate commands to ingest every available StatsBomb Open Data season, transform Bronze to Silver, build Gold features and retrain the ML baseline.

## Smoke Test

Generate commands for only two datasets:

```powershell
python -m orchestration.generate_statsbomb_pipeline_commands --limit 2 --ingestion-date 2026-05-14
```

## Full Command Generation

```powershell
python -m orchestration.generate_statsbomb_pipeline_commands --ingestion-date 2026-05-14
```

To save the commands:

```powershell
python -m orchestration.generate_statsbomb_pipeline_commands --ingestion-date 2026-05-14 > run_all_statsbomb.ps1
```

Then inspect `run_all_statsbomb.ps1` before running it.

## Run

```powershell
.\run_all_statsbomb.ps1
```

## Notes

- `--max-event-matches 9999` means every available match for each season.
- Bronze ingestion uses StatsBomb IDs.
- Silver and Gold use readable partitions such as `competition=world_cup/season=2022`.
- The final generated command retrains the ML model on every Gold dataset.
