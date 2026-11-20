import json
import os
import sqlite3
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from .app import create_app
from .repository import FoodRepository, seed_database
from .reuse import CachedRecipe, RecipeCache, ReuseError

PROFILE = {
    "weight_value": 80, "weight_unit": "kg", "height_value": 180, "height_unit": "cm",
    "age": 30, "gender": "male", "goal": "maintenance", "activity_level": "moderately_active",
    "dietary_restrictions": [" Dairy Free "], "meals_per_day": 3,
}
REQUEST = {"profile": PROFILE, "request": "Something quick", "ingredients": [{"food_id": 8, "grams": 100}]}
RECIPE = {
    "title": "Roast chicken", "total_calories": 900, "macros": {"protein": 53, "carbs": 120, "fats": 25},
    "cooking_time": 10, "ingredients": [{"name": "Chicken", "amount": "100 g"}], "instructions": ["Serve cooked chicken."],
}


class TestStore:
    def __init__(self):
        self.saved, self.contexts = {}, []

    def get(self, key):
        return self.saved.get(key)

    def put(self, key, recipe, context):
        self.contexts.append(context)
        return self.saved.setdefault(key, CachedRecipe(recipe=recipe, created_at=datetime.now(timezone.utc)))


class RecipeTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.db = Path(directory.name, "fixtures.sqlite3")
        seed_database(self.db)
        self.repository = FoodRepository(self.db)
        self.store, self.requests = TestStore(), []
        self.api = TestClient(create_app(self.repository, serve_frontend=False, cache=self.store, generator=self.generate))

    def generate(self, request, context):
        self.requests.append((request, context))
        return RECIPE

    def test_miss_then_hit_and_minimal_private_context(self):
        first = self.api.post("/api/recipes", json=REQUEST)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertFalse(first.json()["reused"])
        second = self.api.post("/api/recipes", json=REQUEST)
        self.assertTrue(second.json()["reused"])
        self.assertEqual(first.json()["created_at"], second.json()["created_at"])
        self.assertEqual(len(self.requests), 1)
        prompt, context = self.requests[0]
        self.assertIn("100 g of Chicken breast", prompt)
        self.assertAlmostEqual(context.meal_targets.target_calories, context.targets.target_calories / 3)
        safe = self.store.contexts[0]
        self.assertEqual(set(safe), {"schema_revision", "request_sha256", "ingredients", "dietary_restrictions"})
        self.assertEqual(len(safe["request_sha256"]), 64)
        self.assertEqual(safe["dietary_restrictions"], ["dairy free"])
        self.assertEqual(safe["ingredients"], [{"food_id": 8, "grams": 100}])

    def test_context_separates_constraints_amount_and_request(self):
        rows = [
            REQUEST,
            dict(REQUEST, ingredients=[{"food_id": 8, "grams": 60}, {"food_id": 8, "grams": 40}]),
            dict(REQUEST, ingredients=[{"food_id": 8, "grams": 75}]),
            dict(REQUEST, profile=dict(PROFILE, dietary_restrictions=["peanut free"])),
            dict(REQUEST, request="Something spicy"),
        ]
        for row, reused in zip(rows, [False, True, False, False, False]):
            response = self.api.post("/api/recipes", json=row)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["reused"], reused)
        self.assertEqual(len(self.requests), 4)

    def test_no_generation_if_store_unavailable(self):
        class Down(TestStore):
            def get(self, key):
                raise ReuseError(503, "Recipe storage is unavailable")
        client = TestClient(create_app(self.repository, cache=Down(), generator=self.generate))
        self.assertEqual(client.post("/api/recipes", json=REQUEST).status_code, 503)
        self.assertEqual(self.requests, [])

    def test_known_miss_does_not_enable_live_generation(self):
        client = TestClient(create_app(self.repository, cache=self.store))
        with patch.dict(os.environ, {"MACROCHEF_GENERATION_ENABLED": "0"}):
            response = client.post("/api/recipes", json=REQUEST)
        self.assertEqual(response.status_code, 503, response.text)
        self.assertIn("disabled", response.json()["detail"])
        self.assertEqual(self.store.saved, {})

    def test_fake_404_does_not_allow_generation(self):
        class Missing(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(404)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Route not found."}).encode())
            def log_message(self, *_):
                pass
        with ThreadingHTTPServer(("127.0.0.1", 0), Missing) as listener:
            thread = threading.Thread(target=listener.serve_forever, daemon=True)
            thread.start()
            try:
                client = TestClient(create_app(self.repository, cache=RecipeCache(f"http://127.0.0.1:{listener.server_port}"), generator=self.generate))
                self.assertEqual(client.post("/api/recipes", json=REQUEST).status_code, 502)
                self.assertEqual(self.requests, [])
            finally:
                listener.shutdown()
                thread.join()

    def test_invalid_model_output_is_not_saved(self):
        client = TestClient(create_app(self.repository, cache=self.store, generator=lambda *_: dict(RECIPE, instructions=[" "])))
        self.assertEqual(client.post("/api/recipes", json=REQUEST).status_code, 502)
        self.assertEqual(self.store.saved, {})

    def test_ingredient_validation_and_meal_totals(self):
        invalid = dict(REQUEST, ingredients=[{"food_id": 999999, "grams": 100}])
        self.assertEqual(self.api.post("/api/recipes", json=invalid).status_code, 404)
        invalid["ingredients"] = [{"food_id": 8, "grams": 1000}, {"food_id": 8, "grams": 1001}]
        self.assertEqual(self.api.post("/api/recipes", json=invalid).status_code, 422)
        payload = {"ingredients": [{"food_id": 8, "grams": 100}, {"food_id": 1, "grams": 50}]}
        result = self.api.post("/api/meals/nutrition", json=payload)
        self.assertEqual(result.json(), {
            "grams": 150, "kcal": 230.0, "protein_g": 32.35, "carbs_g": 14.1, "fat_g": 3.75})
        with sqlite3.connect(self.db) as con:
            con.execute("DELETE FROM food_nutrients WHERE food_id=8 AND nutrient_id=203")
        number = self.api.post("/api/meals/nutrition", json=payload).json()
        self.assertIsNone(number["protein_g"])
        self.assertEqual(number["kcal"], 230.0)
