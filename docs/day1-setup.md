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

After changing Azure accounts, clear the previous session:

```powershell
az logout
az account clear
```

Then log in to the active Azure account:

```powershell
az login --scope https://management.core.windows.net//.default
```

Only use `--tenant` if Azure shows several tenants and you know the correct tenant ID for the new account:

```powershell
az login --tenant <your-tenant-id> --scope https://management.core.windows.net//.default
```

Verify the active subscription:

```powershell
az account list --output table
az account show
```

## Azure Resources

On Day 1, the active Azure subscription was:

```text
Azure subscription 1
958fe4cd-d482-4e4c-8f45-22c52452137f
```

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

Expected output:

```text
Uploaded blob: bronze/test/day1_upload.txt
```

## Concepts

- Subscription: billing and access boundary for Azure resources.
- Resource Group: logical container for related Azure resources.
- Storage Account: Azure storage namespace and configuration boundary.
- Blob Container: folder-like boundary for objects inside Blob Storage.
- Azure CLI: terminal tool for creating and managing Azure resources.
- Azure Portal vs CLI: Portal is visual and manual; CLI is scriptable and repeatable.
