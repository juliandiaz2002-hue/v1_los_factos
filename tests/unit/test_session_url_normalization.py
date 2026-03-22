from data.session import normalize_database_url


def test_normalize_database_url_preserves_sqlite():
    url = "sqlite+pysqlite:///./los_factos_v2_local.db"

    assert normalize_database_url(url) == url


def test_normalize_database_url_converts_postgresql_to_psycopg():
    url = "postgresql://postgres:secret@db.example.com:5432/postgres?sslmode=require"

    assert normalize_database_url(url) == (
        "postgresql+psycopg://postgres:secret@db.example.com:5432/postgres?sslmode=require"
    )


def test_normalize_database_url_converts_postgres_alias_to_psycopg():
    url = "postgres://postgres:secret@db.example.com:5432/postgres"

    assert normalize_database_url(url) == "postgresql+psycopg://postgres:secret@db.example.com:5432/postgres"


def test_normalize_database_url_keeps_explicit_psycopg_driver():
    url = "postgresql+psycopg://postgres:secret@db.example.com:5432/postgres"

    assert normalize_database_url(url) == url
