"""Runtime settings, read once from the environment.

Model IDs live here so they can change without code edits.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COUNSEL_", env_file=".env", frozen=True)

    env: str = Field(default="dev", pattern=r"^(dev|ci|shadow)$")
    database_url: SecretStr = SecretStr("postgresql://counsel:counsel_dev@localhost:5433/counsel")

    # AWS Mumbai. Keep inference in India via the Bedrock India endpoint.
    aws_region: str = "ap-south-1"

    # Fill in from `aws bedrock list-foundation-models --region ap-south-1 --by-provider anthropic`.
    # If 5.5 models are not served there, use what is and re-run the evaluation
    # (team plan risk table).
    model_triage: str = ""
    model_drafting: str = ""
    model_verifier: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
