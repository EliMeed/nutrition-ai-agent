"""Seeded demo on SQLite; production-shaped PostgreSQL uses MacroChef's source schema."""
import os
import re
import sqlite3
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

IDS = (208, 203, 205, 204)
SEED = (
    (1, "White rice", "Cooked", "Long-grain, plain", ("130", "2.7", "28.2", "0.3")),
    (2, "White rice", "Dry", "Long-grain, uncooked", ("365", "7.1", "80", "0.7")),
    (3, "Rolled oats", "Dry", "Plain, uncooked", ("379", "13", "67.7", "6.5")),
    (4, "Black beans", "Cooked", "Boiled, unsalted", ("132", "8.9", "23.7", "0.5")),
    (5, "Banana", "Raw", "Peeled", ("89", "1.1", "22.8", "0.3")),
    (6, "Green lentils", "Cooked", "Boiled, unsalted", ("116", "9", "20.1", "0.4")),
    (7, "Chickpeas", "Cooked", "Boiled, unsalted", ("164", "8.9", "27.4", "2.6")),
    # Illustrative sample values; not a sourced CNF record.
    (8, "Chicken breast", "Cooked", "Roasted, skinless", ("165", "31", "0", "3.6")),
)
SCHEMA = """
CREATE TABLE foods (food_id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE nutrients (nutrient_id INTEGER PRIMARY KEY, name TEXT NOT NULL, unit TEXT NOT NULL);
CREATE TABLE food_nutrients (
  food_id INTEGER NOT NULL REFERENCES foods(food_id),
  nutrient_id INTEGER NOT NULL REFERENCES nutrients(nutrient_id),
  amount_per_100g NUMERIC NOT NULL,
  PRIMARY KEY(food_id, nutrient_id)
);
"""
DEMO_META = {row[0]: row[1:4] for row in SEED}


def seed_database(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Refuse to overwrite an existing database, including files named by the user.
    path.touch(exist_ok=False)
    with sqlite3.connect(path) as con:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(SCHEMA)
        con.executemany("INSERT INTO foods VALUES (?, ?)",
                        [(i, f"{name}, {prep.lower()}, {notes}") for i, name, prep, notes, _ in SEED])
        con.executemany("INSERT INTO nutrients VALUES (?, ?, ?)", (
            (208, "Energy", "kcal"), (203, "Protein", "g"), (205, "Carbohydrate", "g"), (204, "Fat", "g")))
        con.executemany("INSERT INTO food_nutrients VALUES (?, ?, ?)",
                        [(i, n, v) for i, _, _, _, values in SEED for n, v in zip(IDS, values)])


class DatabaseUnavailable(Exception):
    pass


class FoodRepository:
    def __init__(self, sqlite_path: Path, dsn: str | None = None, catalogue: str | None = None):
        self.sqlite_path = sqlite_path
        self.dsn = dsn
        self.uses_fixtures = not dsn or catalogue == "fixture"
        self.placeholder = "%s" if dsn else "?"

    @property
    def mode(self):
        return "postgresql" if self.dsn else "sqlite-fixtures"

    @contextmanager
    def _connect(self):
        if self.dsn:
            try:
                import psycopg
            except ImportError as exc:
                raise DatabaseUnavailable from exc
            try:
                with psycopg.connect(self.dsn, connect_timeout=3) as con:
                    con.execute("SET TRANSACTION READ ONLY")
                    con.execute("SET LOCAL statement_timeout TO '2500ms'")
                    yield con
            except psycopg.Error as exc:
                raise DatabaseUnavailable from exc
        else:
            try:
                con = sqlite3.connect(self.sqlite_path.resolve().as_uri() + "?mode=ro", uri=True)
                try:
                    yield con
                finally:
                    con.close()
            except sqlite3.Error as exc:
                raise DatabaseUnavailable from exc

    def search(self, query: str):
        terms = re.findall(r"[^\W_]+", query.lower())
        if query.strip() and not terms:
            return []
        needle = [term[:-1] if len(term) > 3 and term.endswith("s") and not term.endswith(("ss", "us", "is")) else term for term in terms]
        p = self.placeholder
        # PostgreSQL and SQLite share this bounded query. LIKE parameters never contain
        # user-supplied wildcard characters; we confirm a whole-word match below.
        clauses = " AND ".join(f"LOWER(name) LIKE {p}" for _ in needle)
        where = f"WHERE {clauses}" if clauses else ""
        with self._connect() as con:
            rows = con.execute(
                f"SELECT food_id, name FROM foods {where} ORDER BY {'food_id' if self.uses_fixtures else 'name, food_id'} LIMIT 200",
                tuple(f"%{word}%" for word in needle)).fetchall()
        results = []
        for i, label in rows:
            words = set(re.findall(r"[^\W_]+", label.lower()))
            if not all(word in words or word + "s" in words for word in needle):
                continue
            if self.uses_fixtures:
                name, preparation, notes = DEMO_META.get(i, (label, "Unspecified", "Demo catalogue"))
            else:
                # Full source label is retained: do not infer a food type if no preparation is specified.
                preparation = next((tag.title() for tag in ("uncooked", "cooked", "dry", "raw")
                                    if tag in words), "Unspecified")
                preparation = "Dry" if preparation == "Uncooked" else preparation
                name, notes = label, "PostgreSQL catalogue"
            results.append({"id": i, "name": name, "preparation": preparation, "notes": notes})
        return results[:30]

    def food_label(self, food_id: int) -> str | None:
        with self._connect() as con:
            row = con.execute(
                f"SELECT name FROM foods WHERE food_id = {self.placeholder}", (food_id,)).fetchone()
        return row[0] if row else None

    def macros_per_100g(self, food_id: int):
        p = self.placeholder
        selected = ", ".join([p] * len(IDS))
        with self._connect() as con:
            rows = con.execute(
                f"""SELECT f.food_id, fn.nutrient_id, fn.amount_per_100g
                    FROM foods AS f LEFT JOIN food_nutrients AS fn
                      ON f.food_id = fn.food_id AND fn.nutrient_id IN ({selected})
                    WHERE f.food_id = {p}""", (*IDS, food_id)).fetchall()
        if not rows:
            return None
        return {n: Decimal(str(v)) for _, n, v in rows if n is not None and v is not None}


def make_repository():
    return FoodRepository(
        Path(os.getenv("MACROCHEF_DEMO_DB", Path.cwd() / ".demo" / "macrochef-fixtures-v2.sqlite3")),
        os.getenv("MACROCHEF_DATABASE_URL"),
        os.getenv("MACROCHEF_CATALOGUE"))
