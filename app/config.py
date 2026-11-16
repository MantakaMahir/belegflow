from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: SecretStr = SecretStr("")
    openai_base_url: str = "https://freellm.gotiq.co/v1"
    openai_model: str = "auto"
    data_dir: Path = Path("data")
    seed_demo: bool = True
    public_host: str = ""
    cloudflare_access_required: bool = False
    public_access_email: str = ""
    max_upload_bytes: int = Field(default=15 * 1024 * 1024, ge=1024)
    max_pages: int = Field(default=10, ge=1, le=30)
    google_credentials_file: str = ""
    google_drive_folder_id: str = ""
    google_sheet_id: str = ""
    google_sheet_range: str = "Sheet1!A:Y"

    @field_validator("openai_base_url")
    @classmethod
    def trusted_endpoint(cls, value):
        parsed = urlparse(value)
        local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not (local and parsed.scheme == "http"):
            raise ValueError("AI endpoint must use HTTPS (HTTP allowed only for loopback)")
        if (
            not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("AI endpoint must not contain credentials, query, or fragment")
        return value.rstrip("/")

    @property
    def live_ready(self):
        return bool(self.openai_api_key.get_secret_value())
