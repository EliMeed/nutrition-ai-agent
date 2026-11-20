"""Insert one explicit mock recipe through the same private API as the live app."""
import argparse
import json
import os

from .reuse import RecipeCache, RecipeRequest, ValidRecipe, prepare_context

PROFILE = {
    "weight_value": 75, "weight_unit": "kg", "height_value": 175, "height_unit": "cm",
    "age": 30, "gender": "male", "activity_level": "moderately_active",
    "goal": "maintenance", "meals_per_day": 3, "dietary_restrictions": [],
}
DEMO_REQUEST = {"profile": PROFILE, "request": "A lemon and herb chicken rice bowl", "ingredients": []}
DEMO_RECIPE = {
    "title": "Lemon and herb chicken rice bowl",
    "total_calories": 580,
    "macros": {"protein": 48, "carbs": 55, "fats": 18},
    "cooking_time": 25,
    "ingredients": [
        {"name": "cooked chicken breast", "amount": "140 g"},
        {"name": "cooked brown rice", "amount": "160 g"},
        {"name": "cooked peas", "amount": "75 g"},
        {"name": "olive oil", "amount": "1 tbsp"},
        {"name": "lemon juice and chopped parsley", "amount": "1 tbsp each"},
    ],
    "instructions": [
        "Warm the cooked chicken, rice, and peas.",
        "Whisk the lemon juice, oil, and parsley into a dressing.",
        "Serve the chicken and peas over the rice and spoon over the dressing.",
    ],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-request", action="store_true", help="Print an exact cache-hit request without saving")
    args = parser.parse_args()
    if args.print_request:
        print(json.dumps(DEMO_REQUEST))
        return
    if os.getenv("MACROCHEF_CATALOGUE", "fixture") != "fixture" or os.getenv(
        "MACROCHEF_CATALOGUE_REVISION", "fixture-v2"
    ) != "fixture-v2":
        parser.error("This mock recipe is only for the isolated fixture-v2 catalogue.")
    payload = RecipeRequest.model_validate(DEMO_REQUEST)
    _, key, safe_context = prepare_context(payload, [], "fixture")
    saved = RecipeCache().put(key, ValidRecipe.model_validate(DEMO_RECIPE), safe_context)
    print(f"Demo recipe ready: {saved.recipe.title} (saved {saved.created_at.isoformat()})")


if __name__ == "__main__":
    main()
