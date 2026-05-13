# Day 1 Setup

## Local Python

Create and activate the virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --use-feature=truststore pandas requests python-dotenv azure-storage-blob azure-identity fastapi uvicorn scikit-learn pytest
python -m pip freeze > requirements.txt
```

## Azure Login

If Azure CLI asks for an explicit management scope:

```powershell
az login --scope https://management.core.windows.net//.default
```

For the Microsoft Learn Sandbox tenant used on Day 1:

```powershell
az login --tenant 604c1504-c6a3-4080-81aa-b33091104187 --scope https://management.core.windows.net//.default
```

Verify the active subscription:

```powershell
az account show
```

## Azure Resources

Create the Resource Group:

```powershell
az group create `
  --name rg-worldcup-ai-dev `
  --location canadacentral
```

Create the Storage Account:

```powershell
az storage account create `
  --name stworldcupaifayssaldev `
  --resource-group rg-worldcup-ai-dev `
  --location canadacentral `
  --sku Standard_LRS
```

Create the data layer containers:

```powershell
az storage container create `
  --name bronze `
  --account-name stworldcupaifayssaldev `
  --auth-mode login

az storage container create `
  --name silver `
  --account-name stworldcupaifayssaldev `
  --auth-mode login

az storage container create `
  --name gold `
  --account-name stworldcupaifayssaldev `
  --auth-mode login
```

Run the upload smoke test:

```powershell
python ingestion/upload_test_blob.py
```

## Concepts

- Subscription: billing and access boundary for Azure resources.
- Resource Group: logical container for related Azure resources.
- Storage Account: Azure storage namespace and configuration boundary.
- Blob Container: folder-like boundary for objects inside Blob Storage.
- Azure CLI: terminal tool for creating and managing Azure resources.
- Azure Portal vs CLI: Portal is visual and manual; CLI is scriptable and repeatable.
