# World Cup AI Platform

Azure-based AI/Data Platform for football match intelligence.

## Goal

This project demonstrates an end-to-end data and AI platform using Azure, Python, Docker, CI/CD and MLOps principles.

## Architecture

- Bronze layer: raw football data stored in Azure Blob Storage
- Silver layer: cleaned and standardized datasets
- Gold layer: model-ready features and analytics tables
- ML layer: match prediction model
- API layer: FastAPI inference service
- Deployment: Docker + Azure Container Apps
- CI/CD: GitHub Actions
- Monitoring: Azure Monitor / Application Insights
- Infrastructure: Terraform

## Day 1 Status

- Project repository initialized
- Python environment created
- Azure CLI installed and configured
- Azure Resource Group created
- Azure Storage Account created
- Bronze/Silver/Gold containers created
- First test file uploaded to Azure Blob Storage

## Day 2 Status

- Reusable StatsBomb Open Data ingestion added
- Bronze JSON is saved locally under `data/bronze/`
- Bronze JSON is uploaded to Azure Blob Storage
- Unit tests added for ingestion helpers

## Day 3 Status

- Bronze StatsBomb JSON transformed into Silver Parquet
- Silver tables added for matches, events, shots, passes and lineups
- Silver Parquet uploaded to Azure Blob Storage

## Day 4 Status

- Gold feature tables built from Silver
- Team-match and match-level feature datasets added
- Gold Parquet uploaded to Azure Blob Storage

## Day 5 Status

- Baseline match-result ML pipeline added
- Random Forest classifier trained from Gold match features
- Metrics and model artifacts generated locally

## Day 6 Status

- Pre-match rolling team-form features added
- Prediction-safe match features created with no current-match leakage
- Pre-match Gold Parquet uploaded to Azure Blob Storage
