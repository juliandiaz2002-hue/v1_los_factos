"""Jerarquia de errores de aplicacion."""

from __future__ import annotations


class AppError(Exception):
    """Error base para fallas controladas."""


class ConfigurationAppError(AppError):
    """Error de configuracion o infraestructura externa."""


class ValidationAppError(AppError):
    """Error de validacion de entradas."""


class IngestionAppError(AppError):
    """Error en flujo de ingesta."""


class DatabaseAppError(AppError):
    """Error en persistencia."""


def to_user_message(error: Exception) -> str:
    if isinstance(error, ConfigurationAppError):
        return str(error)
    if isinstance(error, ValidationAppError):
        return str(error)
    if isinstance(error, IngestionAppError):
        return f"No fue posible completar la ingesta: {error}"
    if isinstance(error, DatabaseAppError):
        return "Se detecto un problema de base de datos. Intenta nuevamente."
    if isinstance(error, AppError):
        return str(error)
    return "Ocurrio un error inesperado. Revisa logs para detalle tecnico."
