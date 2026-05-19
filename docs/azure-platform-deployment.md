# Azure Platform Deployment

This project uses Terraform to define the target Azure platform for the football AI API.

## Resources

- Resource Group
- Storage Account with `bronze`, `silver`, and `gold` containers
- Azure Container Registry
- Key Vault
- Log Analytics Workspace
- Application Insights
- Azure Container Apps Environment
- Azure Container App for the FastAPI inference service

## First-Time Setup

Install Terraform, then authenticate:

```powershell
az login
az account set --subscription "<subscription-id>"
```

Prepare variables:

```powershell
Copy-Item infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
```

If the Resource Group or Storage Account already exists, import them before `apply`:

```powershell
terraform -chdir=infra/terraform import azurerm_resource_group.main /subscriptions/<subscription-id>/resourceGroups/rg-worldcup-ai-dev
terraform -chdir=infra/terraform import azurerm_storage_account.data_lake /subscriptions/<subscription-id>/resourceGroups/rg-worldcup-ai-dev/providers/Microsoft.Storage/storageAccounts/stworldcupaifayssaldev
```

Validate the deployment:

```powershell
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform fmt
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan
```

Apply only after reviewing the plan:

```powershell
terraform -chdir=infra/terraform apply
```

## Container Image Flow

Build and push the API image:

```powershell
az acr login --name acrworldcupaidev
docker build -t acrworldcupaidev.azurecr.io/world-cup-ai-platform-api:latest .
docker push acrworldcupaidev.azurecr.io/world-cup-ai-platform-api:latest
```

Then update the Container App:

```powershell
az containerapp update `
  --name ca-worldcup-ai-api-dev `
  --resource-group rg-worldcup-ai-dev `
  --image acrworldcupaidev.azurecr.io/world-cup-ai-platform-api:latest
```

## GitHub Actions Deployment

The repository includes a manual deployment workflow:

```text
.github/workflows/deploy-api.yml
```

Required GitHub secrets:

```text
AZURE_CLIENT_ID
AZURE_TENANT_ID
AZURE_SUBSCRIPTION_ID
AZURE_RESOURCE_GROUP
AZURE_CONTAINER_APP_NAME
AZURE_CONTAINER_REGISTRY_NAME
AZURE_CONTAINER_REGISTRY_LOGIN_SERVER
```

Use a federated credential from Azure Entra ID to GitHub Actions OIDC instead of storing an Azure password.

Terraform validation runs in:

```text
.github/workflows/terraform-validate.yml
```

## Current Limitation

The local Docker Compose setup mounts `data/`, `models/`, and `reports/` from the workstation. Azure Container Apps cannot use those local mounts. For production, model artifacts should be packaged into the image, pulled from Blob Storage, or mounted from an Azure Files share.
