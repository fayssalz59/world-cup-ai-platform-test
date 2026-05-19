variable "project_name" {
  description = "Short project name used for Azure resource names."
  type        = string
  default     = "worldcupai"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region."
  type        = string
  default     = "canadacentral"
}

variable "resource_group_name" {
  description = "Resource group name."
  type        = string
  default     = "rg-worldcup-ai-dev"
}

variable "storage_account_name" {
  description = "Globally unique storage account name."
  type        = string
  default     = "stworldcupaifayssaldev"
}

variable "container_registry_name" {
  description = "Globally unique Azure Container Registry name. Alphanumeric only."
  type        = string
  default     = "acrworldcupaidev"
}

variable "key_vault_name" {
  description = "Globally unique Key Vault name."
  type        = string
  default     = "kv-worldcup-ai-dev"
}

variable "container_app_name" {
  description = "Azure Container App name for the FastAPI service."
  type        = string
  default     = "ca-worldcup-ai-api-dev"
}

variable "container_image" {
  description = "Container image deployed to Azure Container Apps."
  type        = string
  default     = "acrworldcupaidev.azurecr.io/world-cup-ai-platform-api:latest"
}

variable "api_cpu" {
  description = "CPU allocated to the API container."
  type        = number
  default     = 0.5
}

variable "api_memory" {
  description = "Memory allocated to the API container."
  type        = string
  default     = "1Gi"
}
