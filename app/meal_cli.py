from app.pipeline.food_lookup import search_foods, calculate_food_macros, calculate_meal_macros


def build_meal() -> None:
    ingredients = []
    selected_foods = []
    while True:
        term = input("\nSearch for a food (or press Enter to finish): ").strip()
        if not term:
            break

        matches = search_foods(term)
        if not matches:
            print("No foods found. Try a different search.")
            continue
        for number, (_, name) in enumerate(matches, start=1):
            print(f"{number}. {name}")

        try:
            choice = int(input("Choose a number (0 to search again): "))
            if choice == 0:
                continue
            if not 1 <= choice <= len(matches):
                raise ValueError("Choice out of range")
            food_id, name = matches[choice - 1]
            grams = input("Amount in grams: ").strip()
            calculate_food_macros(food_id, grams)  # validate before adding
        except ValueError as exc:
            print(f"Invalid selection or weight: {exc}")
            continue

        ingredients.append((food_id, grams))
        selected_foods.append((name, grams))
        print(f"Added: {name} ({grams} g)")

    if not ingredients:
        print("No ingredients added.")
        return

    print("\nSelected ingredients:")
    for name, grams in selected_foods:
        print(f"- {name}: {grams} g")

    totals = calculate_meal_macros(ingredients)
    print("\nMeal nutrition:")
    for nutrient, value in totals.items():
        unit = "kcal" if nutrient == "calories" else "g"
        display = "not available (incomplete)" if value is None else f"{value:.1f} {unit}"
        print(f"{nutrient.title()}: {display}")
