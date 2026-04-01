"""Centralised configuration loaded from environment / .env file."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")


class Settings(BaseModel):
    """Typed project settings with sensible defaults."""

    data_raw_dir: Path = Path(os.getenv("DATA_RAW_DIR", "./data_raw"))
    data_processed_dir: Path = Path(os.getenv("DATA_PROCESSED_DIR", "./data_processed"))
    artifacts_dir: Path = Path(os.getenv("ARTIFACTS_DIR", "./artifacts"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    sim_initial_cash: float = float(os.getenv("SIM_INITIAL_CASH", "0"))
    sim_position_limit: int = int(os.getenv("SIM_POSITION_LIMIT", "20"))
    sim_time_limit: int = int(os.getenv("SIM_TIME_LIMIT", "1000000"))


def get_settings() -> Settings:
    """Return a fresh Settings instance (re-reads env)."""
    return Settings()
