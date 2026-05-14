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

## Direct Python Orchestrator

Preferred option:

```powershell
python -m orchestration.run_all_statsbomb_pipeline --ingestion-date 2026-05-14 --workers 2
```

This runs:

```text
Bronze ingestion
Silver Parquet
Gold post-match features
Gold pre-match rolling features
post-match baseline model
pre-match baseline model
```

Dry run:

```powershell
python -m orchestration.run_all_statsbomb_pipeline --dry-run
```

Smoke test:

```powershell
python -m orchestration.run_all_statsbomb_pipeline --limit 1 --ingestion-date 2026-05-14 --workers 1
```

Run only Silver, Gold and ML after Bronze already exists:

```powershell
python -m orchestration.run_all_statsbomb_pipeline --skip-bronze --ingestion-date 2026-05-14
```

Run only post-match and pre-match models after all Gold tables already exist:

```powershell
python -m orchestration.run_all_statsbomb_pipeline --skip-bronze --skip-silver --skip-gold --skip-prematch-gold
```

Run selected datasets only:

```powershell
python -m orchestration.run_all_statsbomb_pipeline `
  --dataset world_cup:2022 `
  --dataset champions_league:2018_2019 `
  --skip-bronze `
  --skip-silver `
  --skip-gold
```

Skip post-match model and train only pre-match model:

```powershell
python -m orchestration.run_all_statsbomb_pipeline `
  --skip-bronze `
  --skip-silver `
  --skip-gold `
  --skip-prematch-gold `
  --skip-ml
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
