"""Real PostgreSQL tests, restricted to a disposable schema in macrochef_test."""
import os
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

from app.pipeline import cnf, food_lookup, load_cnf


@pytest.fixture
def isolated_database(monkeypatch, tmp_path):
    dsn = os.getenv("MACROCHEF_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("Set MACROCHEF_TEST_DATABASE_URL to run PostgreSQL tests")
    if conninfo_to_dict(dsn).get("dbname") != "macrochef_test":
        pytest.fail("Integration tests require an explicit macrochef_test database")

    # Keep cleanup independent of the patched application connection function.
    real_connect = psycopg.connect
    schema = "test_" + uuid4().hex
    with real_connect(dsn, autocommit=True, connect_timeout=5) as admin:
        if admin.execute("SELECT current_database()").fetchone()[0] != "macrochef_test":
            pytest.fail("Refusing to modify a database other than macrochef_test")
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            def guarded_connect(conninfo="", **kwargs):
                params = conninfo_to_dict(conninfo, **kwargs)
                if params.get("dbname") != "macrochef_test":
                    raise RuntimeError("Test blocked a connection outside macrochef_test")
                # No public-schema fallback; every app connection uses this schema.
                params["options"] = f"-c search_path={schema} -c statement_timeout=10000"
                params["connect_timeout"] = "5"
                return real_connect(**params)

            monkeypatch.setattr(psycopg, "connect", guarded_connect)
            monkeypatch.setenv("MACROCHEF_DATABASE_URL", dsn)
            monkeypatch.setattr(cnf, "DATA_DIR", tmp_path)
            monkeypatch.setattr(load_cnf, "DATA_DIR", tmp_path)

            schema_sql = Path(__file__).resolve().parents[1] / "sql" / "schema.sql"
            with psycopg.connect(dsn) as conn:
                conn.execute(schema_sql.read_text(encoding="utf-8"))
            yield tmp_path, dsn
        finally:
            # Only the unique schema created above is removed, never public/data.
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_csv_import_lookup_macros_and_repeat_import(isolated_database, capsys):
    directory, dsn = isolated_database
    (directory / "FOOD NAME.csv").write_text(
        "FoodID,FoodDescription\n1,Chicken breast\n", encoding="cp1252"
    )
    (directory / "NUTRIENT NAME.csv").write_text(
        "NutrientID,NutrientName,NutrientUnit\n"
        "208,Energy,kcal\n203,Protein,g\n205,Carbohydrate,g\n204,Fat,g\n",
        encoding="cp1252",
    )
    (directory / "NUTRIENT AMOUNT.csv").write_text(
        "FoodID,NutrientID,NutrientValue\n"
        "1,208,120\n1,203,22.5\n1,205,0\n1,204,2.62\n"
        "999,203,10\n1,999,10\n1,203,-1\n1,203,NaN\n",
        encoding="cp1252",
    )

    # Re-importing the same source must not create duplicate records.
    for _ in range(2):
        load_cnf.load_foods_to_db()
        load_cnf.load_nutrients_to_db()
        load_cnf.load_amounts_to_db()
        assert "Loaded or updated: 4; rejected: 4" in capsys.readouterr().out

    with psycopg.connect(dsn) as conn:
        assert conn.execute("SELECT count(*) FROM foods").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM nutrients").fetchone()[0] == 4
        assert conn.execute("SELECT count(*) FROM food_nutrients").fetchone()[0] == 4

    assert food_lookup.search_foods("breast chicken") == [(1, "Chicken breast")]
    assert food_lookup.search_foods("") == []
    assert food_lookup.get_food_nutrient(999, 203) is None
    assert food_lookup.get_food_nutrient(1, 203)["amount_per_100g"] == Decimal("22.5")
    expected = {
        "calories": Decimal("180"), "protein": Decimal("33.75"),
        "carbs": Decimal("0"), "fat": Decimal("3.93"),
    }
    assert food_lookup.calculate_food_macros(1, "150")["amounts"] == expected
    assert food_lookup.calculate_meal_macros([(1, "100"), (1, "50")]) == expected
