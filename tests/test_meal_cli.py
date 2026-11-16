import psycopg

from app import meal_cli


def test_database_failure_shows_message(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "chicken")

    def fail_search(_term):
        raise psycopg.OperationalError("database unavailable")

    monkeypatch.setattr(meal_cli, "search_foods", fail_search)
    meal_cli.build_meal()

    output = capsys.readouterr().out
    assert "Unable to access the food database" in output
    assert "No foods found" not in output
