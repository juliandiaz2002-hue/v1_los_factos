"""Carga de configuracion por variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    app_env: str
    log_level: str
    database_url: str
    default_date_formats: tuple[str, ...]
    default_timezone: str
    enable_dev_diagnostics: bool

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("DATABASE_URL no esta configurada")

    date_formats_raw = os.getenv("DEFAULT_DATE_FORMATS", "%Y-%m-%d,%Y-%d-%m")
    date_formats = tuple(item.strip() for item in date_formats_raw.split(",") if item.strip())

    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        database_url=database_url,
        default_date_formats=date_formats,
        default_timezone=os.getenv("DEFAULT_TIMEZONE", "America/Santiago"),
        enable_dev_diagnostics=_parse_bool(os.getenv("ENABLE_DEV_DIAGNOSTICS"), default=True),
    )
