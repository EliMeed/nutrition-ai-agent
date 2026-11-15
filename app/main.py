import os
import re
import sys

import logfire
from pydantic import ValidationError

from app.agents import generate_recipe
from app.models import NutritionContext, PhysicalProfile
from app.nutrition import calculate_meal_targets, calculate_targets
from rich.table import Table
from rich.console import Console

os.environ.setdefault("LOGFIRE_SEND_TO_LOGFIRE", "false")
logfire.configure(send_to_logfire=False)


_ACTIVITY_MAP = {
    "s": "sedentary",
    "l": "lightly_active",
    "m": "moderately_active",
    "v": "very_active",
}

_BODY_FAT_SOURCES = {
    "1": "dxa",
    "2": "calipers",
    "3": "smart_scale",
    "4": "visual_estimate",
    "5": "other",
}


def parse_weight_input(prompt: str) -> tuple[float, str]:
    while True:
        raw = input(prompt).strip().lower()
        match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*(kg|lbs)", raw)
        if match:
            return float(match.group(1)), match.group(2)
        print("Format error. Try '180 lbs' or '80 kg'.")


def parse_height_input(prompt: str) -> tuple[float, str, float]:
    while True:
        raw = input(prompt).strip().lower()
        feet_match = re.fullmatch(r"([0-9]+)\s*ft(?:\s*([0-9]+)\s*in)?", raw)
        if feet_match:
            feet = float(feet_match.group(1))
            inches = float(feet_match.group(2) or 0)
            if inches < 12:
                return feet, "ft", inches
            print("Extra inches must be between 0 and 11.")
            continue

        simple_match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*(cm|in)", raw)
        if simple_match:
            return float(simple_match.group(1)), simple_match.group(2), 0

        print("Format error. Try '70 in', '180 cm', or '5 ft 10 in'.")


def parse_age(prompt: str) -> int:
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 10 <= int(raw) <= 120:
            return int(raw)
        print("Please enter a realistic age between 10 and 120.")
        

def parse_meals_per_day(prompt: str) -> int:
    while True:
        raw = input(prompt).strip()
        if not raw:
            return 3
        if raw.isdigit() and 1 <= int(raw) <= 6:
            return int(raw)
        print("Enter a number from 1 to 6, or press Enter for 3.")        
        
def parse_gender(prompt: str) -> str:
    while True:
        raw = input(prompt).strip().lower()
        if raw in {"male", "female"}:
            return raw
        print("Please enter 'male' or 'female'.")


def parse_activity(prompt: str) -> str:
    while True:
        raw = input(prompt).strip().lower()
        activity = _ACTIVITY_MAP.get(raw[:1], raw) if raw else ""
        if activity in {"sedentary", "lightly_active", "moderately_active", "very_active"}:
            return activity
        print("Choose sedentary, lightly active, moderately active, or very active.")


def parse_goal(prompt: str) -> str:
    raw = input(prompt).strip().lower()
    if any(word in raw for word in ["fat", "lose", "weight"]):
        return "weight_loss"
    if any(word in raw for word in ["muscle", "gain", "bulk"]):
        return "muscle_gain"
    return "maintenance"


def parse_body_fat() -> tuple[float | None, str | None]:
    raw = input("Body fat % (optional, press Enter to skip): ").strip().lower()
    if not raw:
        return None, None

    try:
        value = float(raw)
    except ValueError:
        print("Skipping body fat input because the value was not a number.")
        return None, None

    print("How was it measured? 1) DXA  2) Calipers  3) Smart scale  4) Visual estimate  5) Other")
    source = _BODY_FAT_SOURCES.get(input("Choose 1-5: ").strip(), "other")
    return value, source


def get_user_input() -> PhysicalProfile:
    print("\n--- MacroChef Public Demo ---")
    try:
        weight_value, weight_unit = parse_weight_input("Weight (e.g. 180 lbs): ")
        height_value, height_unit, height_inches_extra = parse_height_input("Height (e.g. 180 cm, 70 in, 5 ft 10 in): ")
        age = parse_age("Age: ")

        print("\nActivity levels: sedentary, lightly active, moderately active, very active")
        activity_level = parse_activity("Activity level: ")
        goal = parse_goal("Goal (lose, maintain, gain): ")
        meals_per_day = parse_meals_per_day("Meals per day (1-6, Enter for 3): ")
        restrictions =input("Dietary restrictions (comma-separated, optional): ").strip()
        dietary_restrictions = [item.strip() for item in restrictions.split(",") if item.strip()]
        body_fat_percentage, body_fat_source = parse_body_fat()

        gender = parse_gender("Sex for calculation (male/female): ")

        return PhysicalProfile(
            weight_value=weight_value,
            weight_unit=weight_unit,
            height_value=height_value,
            height_unit=height_unit,
            height_inches_extra=height_inches_extra,
            age=age,
            gender=gender,
            activity_level=activity_level,
            goal=goal,
            meals_per_day=meals_per_day,
            dietary_restrictions=dietary_restrictions,
            body_fat_percentage=body_fat_percentage,
            body_fat_source=body_fat_source,
        )
    except Exception as exc:
        print(f"Setup error: {exc}")
        sys.exit(1)


def print_targets(profile: PhysicalProfile) -> NutritionContext:
    targets = calculate_targets(profile)
    meal_targets = calculate_meal_targets(targets, profile.meals_per_day)

    table = Table(title="Your Nutrition Profile")
    table.add_column("Measure", style="cyan")
    table.add_column("Daily", justify="right")
    table.add_column("Per meal", justify="right")
    table.add_row("Calories", f"{targets.target_calories} kcal", f"{meal_targets.target_calories:.1f} kcal")
    table.add_row("Protein", f"{targets.protein} g", f"{meal_targets.protein:.1f} g")
    table.add_row("Carbs", f"{targets.carbs} g", f"{meal_targets.carbs:.1f} g")
    table.add_row("Fat", f"{targets.fats} g", f"{meal_targets.fats:.1f} g")

    console = Console()
    console.print(f"Equation: {targets.equation.equation} ({targets.equation.status})")
    console.print(f"Resting energy: {targets.resting_energy} kcal | TDEE: {targets.tdee} kcal")
    console.print(table)

    return NutritionContext(
        profile=profile, targets=targets, meal_targets=meal_targets
    )

def main() -> None:
    with logfire.span("User Profile Setup"):
        profile = get_user_input()
        context = print_targets(profile)
        
        
    with logfire.span("User Recipe Request"):
        user_request = input("\nWhat kind of recipe are you looking for today? ").strip()


    print("\nCooking up your personalized recipe...")
    try:
        recipe = generate_recipe(user_request, context)
        print(f"\n{recipe.title}")
        print(f"Calories: {recipe.total_calories} kcal")
        print(
            f"Macros: P {recipe.macros.protein}g | C {recipe.macros.carbs}g | F {recipe.macros.fats}g"
        )
        print(f"Cooking time: {recipe.cooking_time} minutes")

        print("\nIngredients:")
        for ingredient in recipe.ingredients:
            print(f"- {ingredient.amount} {ingredient.name}")

        print("\nInstructions:")
        for index, step in enumerate(recipe.instructions, start=1):
            print(f"{index}. {step}")
    except ValidationError as exc:
        print(f"Validation error: {exc}")
    except Exception as exc:
        print(f"Unexpected error: {exc}")


if __name__ == "__main__":
    try:
        main()
    finally:
        logfire.force_flush()
