import psycopg

from app.pipeline.food_lookup import (
    search_foods,
    calculate_food_macros,
    calculate_meal_macros,
)


def build_meal() -> dict | None:
    try:
        return _build_meal()
    except psycopg.Error:
        print("Unable to access the food database. Check that PostgreSQL is running and the food data is loaded, then try again.")
        return None


def _build_meal() -> dict | None:
    ingredients = []
    selected_foods = []
    step = "search"
    matches = []
    name = ""
    food_id = None

    while True:
        if step == "search":
            term = input("\nSearch for a food (Enter to finish, back for menu, restart to clear): ").strip()
            command = term.lower()
            if command == "back":
                return None
            if command == "restart":
                ingredients.clear()
                selected_foods.clear()
                print("Meal cleared.")
                continue
            if not term:
                if not ingredients:
                    print("No ingredients added.")
                    return None
                step = "review"
                continue
            matches = search_foods(term)
            if not matches:
                print("No foods found. Try a different search.")
                continue
            step = "choose"

        elif step == "choose":
            for number, (_, food_name) in enumerate(matches, start=1):
                print(f"{number}. {food_name}")
            choice = input("Choose a number (back to search, restart to clear): ").strip().lower()
            if choice == "back" or choice == "0":
                step = "search"
                continue
            if choice == "restart":
                ingredients.clear()
                selected_foods.clear()
                step = "search"
                print("Meal cleared.")
                continue
            try:
                number = int(choice)
                if not 1 <= number <= len(matches):
                    raise ValueError("Choice out of range")
                food_id, name = matches[number - 1]
                step = "grams"
            except ValueError as exc:
                print(f"Invalid selection: {exc}")

        elif step == "grams":
            grams = input("Amount in grams (back to choices, restart to clear): ").strip()
            command = grams.lower()
            if command == "back":
                step = "choose"
                continue
            if command == "restart":
                ingredients.clear()
                selected_foods.clear()
                step = "search"
                print("Meal cleared.")
                continue
            try:
                calculate_food_macros(food_id, grams)
            except ValueError as exc:
                print(f"Invalid weight: {exc}")
                continue
            ingredients.append((food_id, grams))
            selected_foods.append((name, grams))
            print(f"Added: {name} ({grams} g)")
            step = "search"

        elif step == "review":
            print("\nSelected ingredients:")
            for food_name, grams in selected_foods:
                print(f"- {food_name}: {grams} g")
            totals = calculate_meal_macros(ingredients)
            print("\nMeal nutrition:")
            for nutrient, value in totals.items():
                unit = "kcal" if nutrient == "calories" else "g"
                display = "not available (incomplete)" if value is None else f"{value:.1f} {unit}"
                print(f"{nutrient.title()}: {display}")
            print("\n1. Finish")
            print("2. Back — remove last food and search again")
            print("3. Restart meal")
            print("4. Return to menu")
            action = input("Choose an option: ").strip()

            if action == "1":
                return {"ingredients": selected_foods, "totals": totals}
            elif action == "2":
                ingredients.pop()
                removed_name, _ = selected_foods.pop()
                print(f"Removed: {removed_name}")
                step = "search"
            elif action == "3":
                ingredients.clear()
                selected_foods.clear()
                print("Meal cleared.")
                step = "search"
            elif action == "4":
                ingredients.clear()
                selected_foods.clear()
                print("Meal cleared. Returning to menu.")
                return None
            else:
                print("Please choose 1, 2, 3, or 4.")
