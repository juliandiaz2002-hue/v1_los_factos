"""Carga de configuracion por variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_env: str
    log_level: str
    database_url: str
    default_date_formats: tuple[str, ...]
    default_timezone: str
    enable_dev_diagnostics: bool
    assume_all_expenses: bool

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _load_env_file_if_present() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            os.environ.setdefault(key, value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_env_file_if_present()
    app_env = os.getenv("APP_ENV", "development")
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        if app_env.lower() in {"development", "dev", "local", "test"}:
            database_url = os.getenv("LOCAL_DATABASE_URL", "sqlite+pysqlite:///./los_factos_v2_local.db")
        else:
            raise RuntimeError("DATABASE_URL no esta configurada")

    date_formats_raw = os.getenv("DEFAULT_DATE_FORMATS", "%Y-%m-%d,%Y-%d-%m")
    date_formats = tuple(item.strip() for item in date_formats_raw.split(",") if item.strip())

    return Settings(
        app_env=app_env,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        database_url=database_url,
        default_date_formats=date_formats,
        default_timezone=os.getenv("DEFAULT_TIMEZONE", "America/Santiago"),
        enable_dev_diagnostics=_parse_bool(os.getenv("ENABLE_DEV_DIAGNOSTICS"), default=True),
        assume_all_expenses=_parse_bool(os.getenv("ASSUME_ALL_EXPENSES"), default=True),
    )
