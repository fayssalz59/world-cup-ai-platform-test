import os
from datetime import UTC, datetime

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
container_name = os.getenv("AZURE_STORAGE_CONTAINER_BRONZE")

if not account_name or not container_name:
    raise ValueError("Missing Azure storage configuration in .env")

account_url = f"https://{account_name}.blob.core.windows.net"

credential = DefaultAzureCredential()
blob_service_client = BlobServiceClient(
    account_url=account_url,
    credential=credential,
)

content = f"World Cup AI Platform test upload - {datetime.now(UTC).isoformat()}"
blob_name = "test/day1_upload.txt"

blob_client = blob_service_client.get_blob_client(
    container=container_name,
    blob=blob_name,
)

blob_client.upload_blob(content, overwrite=True)

print(f"Uploaded blob: {container_name}/{blob_name}")
