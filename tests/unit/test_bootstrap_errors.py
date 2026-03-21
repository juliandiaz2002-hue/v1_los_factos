from data.bootstrap import _build_database_bootstrap_error
from utils.errors import ConfigurationAppError, to_user_message


def test_build_database_bootstrap_error_identifies_supabase_tenant_issue():
    error = _build_database_bootstrap_error(Exception("FATAL: Tenant or user not found"))

    assert isinstance(error, ConfigurationAppError)
    message = to_user_message(error)
    assert "DATABASE_URL" in message
    assert "Supabase" in message
    assert "Settings > Secrets" in message


def test_build_database_bootstrap_error_falls_back_to_generic_connection_message():
    error = _build_database_bootstrap_error(Exception("socket timeout"))

    assert isinstance(error, ConfigurationAppError)
    message = to_user_message(error)
    assert "No fue posible conectar" in message
    assert "DATABASE_URL" in message
