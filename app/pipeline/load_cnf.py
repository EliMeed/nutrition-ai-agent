import csv
import psycopg
from .cnf import DATA_DIR
from .cnf import load_foods
from decimal import Decimal, InvalidOperation


def load_foods_to_db() -> None:
    foods = load_foods()

    with psycopg.connect("dbname=macrochef") as conn:
        with conn.cursor() as cur:
            for food in foods:
                cur.execute(
                    """
                    INSERT INTO foods (food_id, name)
                    VALUES (%s, %s)
                    ON CONFLICT (food_id)
                    DO UPDATE SET name = EXCLUDED.name
                    """,
                    (int(food["FoodID"]), food["FoodDescription"]),
                )

    print(f"Loaded {len(foods)} food records")

def load_nutrients_to_db() -> None:
    path = DATA_DIR / "NUTRIENT NAME.csv"

    with path.open(encoding="cp1252", newline="") as file:
        nutrients = list(csv.DictReader(file))

    with psycopg.connect("dbname=macrochef") as conn:
        with conn.cursor() as cur:
            for nutrient in nutrients:
                cur.execute(
                    """
                    INSERT INTO nutrients (nutrient_id, name, unit)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (nutrient_id)
                    DO UPDATE SET name = EXCLUDED.name, unit = EXCLUDED.unit
                    """,
                    (
                        int(nutrient["NutrientID"]),
                        nutrient["NutrientName"],
                        nutrient["NutrientUnit"],
                    ),
                )

    print(f"Loaded {len(nutrients)} nutrient definitions")

def load_amounts_to_db() -> None:
    path = DATA_DIR / "NUTRIENT AMOUNT.csv"
    loaded = 0
    rejected = 0

    with psycopg.connect("dbname=macrochef") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT food_id FROM foods")
            food_ids = {row[0] for row in cur.fetchall()}
            cur.execute("SELECT nutrient_id FROM nutrients")
            nutrient_ids = {row[0] for row in cur.fetchall()}

            if not food_ids or not nutrient_ids:
                raise ValueError("Load foods and nutrients first")

            sql = """
                INSERT INTO food_nutrients
                    (food_id, nutrient_id, amount_per_100g)
                VALUES (%s, %s, %s)
                ON CONFLICT (food_id, nutrient_id)
                DO UPDATE SET amount_per_100g = EXCLUDED.amount_per_100g
            """

            batch = []
            with path.open(encoding="cp1252", newline="") as file:
                for row in csv.DictReader(file):
                    try:
                        food_id = int(row["FoodID"])
                        nutrient_id = int(row["NutrientID"])
                        amount = Decimal(row["NutrientValue"])
                        if not amount.is_finite() or amount < 0:
                            raise ValueError("Invalid amount")
                        if food_id not in food_ids or nutrient_id not in nutrient_ids:
                            raise ValueError("Unknown food or nutrient ID")
                    except (ValueError, InvalidOperation) as exc:
                        rejected += 1
                        print(f"Rejected food {row['FoodID']}, nutrient {row['NutrientID']}: {exc}")
                        continue

                    batch.append((food_id, nutrient_id, amount))
                    if len(batch) == 1000:
                        cur.executemany(sql, batch)
                        loaded += len(batch)
                        batch.clear()

                if batch:
                    cur.executemany(sql, batch)
                    loaded += len(batch)

    print(f"Loaded or updated: {loaded}; rejected: {rejected}")

if __name__ == "__main__":
    load_foods_to_db()
    load_nutrients_to_db()
    load_amounts_to_db()
