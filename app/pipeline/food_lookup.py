
import psycopg


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
    with psycopg.connect("dbname=macrochef") as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT food_id, name FROM foods WHERE name ILIKE %s ORDER BY name LIMIT 10",
                (f"%{name}%",),
            )
            return cur.fetchall()
