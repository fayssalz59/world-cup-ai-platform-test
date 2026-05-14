import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATSBOMB_BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"


def configure_local_cert_bundle() -> None:
    """Use the generated Windows CA bundle when it exists."""
    bundle_path = PROJECT_ROOT / ".azure-certs" / "windows-ca-bundle.pem"
    if bundle_path.exists() and "REQUESTS_CA_BUNDLE" not in os.environ:
        os.environ["REQUESTS_CA_BUNDLE"] = str(bundle_path)


@dataclass(frozen=True)
class Settings:
    azure_storage_account_name: str
    azure_storage_container_bronze: str
    azure_storage_container_silver: str
    azure_storage_container_gold: str
    statsbomb_base_url: str
    local_bronze_dir: Path
    local_silver_dir: Path
    local_gold_dir: Path

    @property
    def azure_storage_account_url(self) -> str:
        return f"https://{self.azure_storage_account_name}.blob.core.windows.net"


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")

    account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    bronze_container = os.getenv("AZURE_STORAGE_CONTAINER_BRONZE")
    silver_container = os.getenv("AZURE_STORAGE_CONTAINER_SILVER", "silver")
    gold_container = os.getenv("AZURE_STORAGE_CONTAINER_GOLD", "gold")

    if not account_name or not bronze_container:
        raise ValueError("Missing Azure storage configuration in .env")

    return Settings(
        azure_storage_account_name=account_name,
        azure_storage_container_bronze=bronze_container,
        azure_storage_container_silver=silver_container,
        azure_storage_container_gold=gold_container,
        statsbomb_base_url=os.getenv(
            "STATSBOMB_OPEN_DATA_BASE_URL",
            DEFAULT_STATSBOMB_BASE_URL,
        ).rstrip("/"),
        local_bronze_dir=PROJECT_ROOT / "data" / "bronze",
        local_silver_dir=PROJECT_ROOT / "data" / "silver",
        local_gold_dir=PROJECT_ROOT / "data" / "gold",
    )
