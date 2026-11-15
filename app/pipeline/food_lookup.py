
import psycopg
import re
from decimal import Decimal, InvalidOperation


def get_food_nutrient(food_id: int, nutrient_id: int) -> dict | None:
    with psycopg.connect("dbname=macrochef") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT f.name, n.name, n.unit, fn.amount_per_100g
                FROM food_nutrients AS fn
                JOIN foods AS f ON f.food_id = fn.food_id
                JOIN nutrients AS n ON n.nutrient_id = fn.nutrient_id
                WHERE fn.food_id = %s AND fn.nutrient_id = %s
                """,
                (food_id, nutrient_id),
            )
            row = cur.fetchone()

    if row is None:
        return None

    return {
        "food": row[0],
        "nutrient": row[1],
        "unit": row[2],
        "amount_per_100g": row[3],
    }

def search_foods(name: str) -> list[tuple[int, str]]:
    """Return up to 30 foods matching every search word, in any order.

    Matches whole words with a basic trailing-s plural rule. Empty input
    returns no results; this does not handle all plurals or synonyms.
    """
    words = name.split()
    if not words:
        return []

    conditions = " AND ".join("name ~* %s" for _ in words)
    patterns = []
    for word in words:
        base = word[:-1] if len(word) > 3 and word.lower().endswith("s") else word
        patterns.append(r"\m" + re.escape(base) + r"s?\M")

    with psycopg.connect("dbname=macrochef") as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT food_id, name FROM foods WHERE {conditions} ORDER BY name LIMIT 30",
                tuple(patterns),
            )
            return cur.fetchall()


def calculate_food_macros(food_id: int, grams: str) -> dict:
    try:
        weight = Decimal(grams)
    except InvalidOperation as exc:
        raise ValueError("Enter a valid weight in grams") from exc
    if not weight.is_finite() or weight <= 0:
        raise ValueError("Weight must be a positive, finite number")

    nutrient_ids = {
        "calories": 208,
        "protein": 203,
        "carbs": 205,
        "fat": 204,
    }
    amounts = {}
    for label, nutrient_id in nutrient_ids.items():
        nutrient = get_food_nutrient(food_id, nutrient_id)
        amounts[label] = (
            nutrient["amount_per_100g"] * weight / Decimal("100")
            if nutrient is not None else None
        )

    return {"food_id": food_id, "grams": weight, "amounts": amounts}

def calculate_meal_macros(ingredients: list[tuple[int, str]]) -> dict:
    if not ingredients:
        raise ValueError("Add at least one ingredient")

    totals = {name: Decimal("0") for name in ("calories", "protein", "carbs", "fat")}
    missing = {name: False for name in totals}

    for food_id, grams in ingredients:
        amounts = calculate_food_macros(food_id, grams)["amounts"]
        for name, value in amounts.items():
            if value is None:
                missing[name] = True
            else:
                totals[name] += value

    return {
        name: None if missing[name] else total
        for name, total in totals.items()
    }
