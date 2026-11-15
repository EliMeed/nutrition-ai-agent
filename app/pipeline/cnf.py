import csv
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "cnf"


def load_foods() -> list[dict[str, str]]:
    path = DATA_DIR / "FOOD NAME.csv"
    with path.open(encoding="cp1252", newline="") as file:
        return list(csv.DictReader(file))

def find_food(food_id: str) -> dict[str, str] | None:
    for food in load_foods():
        if food["FoodID"] == food_id:
            return food
    return None

def find_nutrient_amount(food_id: str, nutrient_id: str) -> str | None:
    path = DATA_DIR / "NUTRIENT AMOUNT.csv"
    with path.open(encoding="cp1252", newline="") as file:
        for row in csv.DictReader(file):
            if row["FoodID"] == food_id and row["NutrientID"] == nutrient_id:
                return row["NutrientValue"]
    return None

def find_nutrient(nutrient_id: str) -> dict[str, str] | None:
    path = DATA_DIR / "NUTRIENT NAME.csv"
    with path.open(encoding="cp1252", newline="") as file:
        for row in csv.DictReader(file):
            if row["NutrientID"] == nutrient_id:
                return row
    return None

def get_food_nutrient(food_id: str, nutrient_id: str) -> dict[str, str | float] | None:
    food = find_food(food_id)
    nutrient = find_nutrient(nutrient_id)
    amount = find_nutrient_amount(food_id, nutrient_id)

    if food is None or nutrient is None or amount is None:
        return None

    try:
             numeric_amount = float(amount)
    except ValueError:

     raise ValueError(f"Invalid nutrient amount: {amount!r}")

    return {
        "food": food["FoodDescription"],
        "nutrient": nutrient["NutrientName"],
        "amount": numeric_amount,
        "unit": nutrient["NutrientUnit"],

    }

if __name__ == "__main__":
    foods = load_foods()
    print(f"Loaded {len(foods)} food records")
    print(f"First food: {foods[0]['FoodID']} - {foods[0]['FoodDescription']}")

    food_id = foods[0]["FoodID"]
    nutrient_id = "203"  # Protein in this dataset

    nutrient = find_nutrient(nutrient_id)
    amount = find_nutrient_amount(food_id, nutrient_id)

    if nutrient is not None and amount is not None:
        print(f"{nutrient['NutrientName']}: {amount} {nutrient['NutrientUnit']} per 100 g")
    else:
        print("Nutrient information not found.")
