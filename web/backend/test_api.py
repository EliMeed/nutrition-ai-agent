import sqlite3
from decimal import Decimal

import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app import create_app, scale_macros
from backend.repository import FoodRepository, seed_database


class ApiTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.tmp_path = Path(temp.name)
        self.db = self.tmp_path / "fixtures.sqlite3"
        seed_database(self.db)
        self.api = TestClient(create_app(FoodRepository(self.db), serve_frontend=False))

    def test_lookup_limits_and_preparation(self):
        api = self.api
        assert api.get("/api/info").json()["storage"] == "sqlite-fixtures"
        assert len(api.get("/api/foods").json()) == 8
        records = api.get("/api/foods", params={"q": "rice"}).json()
        assert [(f["id"], f["preparation"]) for f in records] == [(1, "Cooked"), (2, "Dry")]
        assert [f["id"] for f in api.get("/api/foods", params={"q": "cooked rice"}).json()] == [1]
        empty = api.get("/api/foods", params={"q": "unmatched"})
        assert empty.status_code == 200 and empty.json() == []
        assert api.get("/api/foods", params={"q": "chicken"}).json() == [
            {"id": 8, "name": "Chicken breast", "preparation": "Cooked", "notes": "Roasted, skinless"}]
        assert api.get("/api/foods/8/nutrition", params={"grams": 100}).json()["protein_g"] == 31
        assert api.get("/api/foods", params={"q": "x" * 101}).status_code == 422


    def test_parameters_and_food_not_found(self):
        api = self.api
        assert api.get("/api/foods/999/nutrition", params={"grams": 100}).status_code == 404
        for amount in (0, 2001, 150.5, "NaN"):
            assert api.get("/api/foods/1/nutrition", params={"grams": amount}).status_code == 422
        assert api.get("/api/foods", params={"q": "' OR 'x'='x"}).json() == []
        assert len(api.get("/api/foods").json()) == 8


    def test_serving_scale_and_preparation(self):
        api = self.api
        assert api.get("/api/foods/1/nutrition", params={"grams": 175}).json() == {
            "id": 1, "grams": 175, "kcal": 227.5, "protein_g": 4.725, "carbs_g": 49.35, "fat_g": 0.525}
        assert api.get("/api/foods/2/nutrition", params={"grams": 175}).json()["kcal"] == 638.75
        assert scale_macros({208: Decimal("130")}, 175) == [Decimal("227.5"), None, None, None]


    def test_missing_differs_from_zero(self):
        db, api = self.db, self.api
        with sqlite3.connect(db) as con:
            con.execute("DELETE FROM food_nutrients WHERE food_id=1 AND nutrient_id=203")
            con.execute("UPDATE food_nutrients SET amount_per_100g=0 WHERE food_id=1 AND nutrient_id=204")
        result = api.get("/api/foods/1/nutrition", params={"grams": 150}).json()
        assert result["protein_g"] is None
        assert result["fat_g"] == 0


    def test_unavailable_is_safe(self):
        tmp_path = self.tmp_path
        api = TestClient(create_app(FoodRepository(tmp_path / "missing.sqlite3"), serve_frontend=False))
        result = api.get("/api/foods")
        assert result.status_code == 503
        assert result.json() == {"detail": "Food database temporarily unavailable. Try again."}
