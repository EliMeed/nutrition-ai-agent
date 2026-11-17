
from app.pipeline import database


def test_default_connection_uses_macrochef(monkeypatch):
    monkeypatch.delenv("MACROCHEF_DATABASE_URL", raising=False)
    seen = []
    expected = object()

    def fake_connect(dsn):
        seen.append(dsn)
        return expected

    monkeypatch.setattr(database.psycopg, "connect", fake_connect)

    assert database.connect_database() is expected
    assert seen == ["dbname=macrochef"]


def test_configured_connection_uses_selected_database(monkeypatch):
    monkeypatch.setenv("MACROCHEF_DATABASE_URL", "dbname=macrochef_test")
    seen = []
    expected = object()

    def fake_connect(dsn):
        seen.append(dsn)
        return expected

    monkeypatch.setattr(database.psycopg, "connect", fake_connect)

    assert database.connect_database() is expected
    assert seen == ["dbname=macrochef_test"]
