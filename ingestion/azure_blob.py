from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from ingestion.config import Settings


class AzureBlobUploader:
    def __init__(self, settings: Settings, container_name: str | None = None) -> None:
        credential = DefaultAzureCredential()
        self._container_name = container_name or settings.azure_storage_container_bronze
        self._blob_service_client = BlobServiceClient(
            account_url=settings.azure_storage_account_url,
            credential=credential,
        )

    def upload_text(self, blob_name: str, content: str) -> None:
        blob_client = self._blob_service_client.get_blob_client(
            container=self._container_name,
            blob=blob_name,
        )
        blob_client.upload_blob(content, overwrite=True)

    def upload_file(self, blob_name: str, local_path: str) -> None:
        blob_client = self._blob_service_client.get_blob_client(
            container=self._container_name,
            blob=blob_name,
        )
        with open(local_path, "rb") as file:
            blob_client.upload_blob(file, overwrite=True)
