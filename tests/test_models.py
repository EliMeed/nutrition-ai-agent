import pytest

from app.models import PhysicalProfile, Recipe, Macronutrients, Ingredient


def test_weight_conversion():
    profile = PhysicalProfile(
        weight_value=200,
        weight_unit="lbs",
        height_value=180,
        height_unit="cm",
        age=30,
        gender="male",
        activity_level="sedentary",
        goal="weight_loss",
        dietary_restrictions=[],
    )
    assert round(profile.weight_kg, 1) == 90.7


def test_height_conversion_ft_and_inches():
    profile = PhysicalProfile(
        weight_value=80,
        weight_unit="kg",
        height_value=5,
        height_unit="ft",
        height_inches_extra=10,
        age=30,
        gender="male",
        activity_level="sedentary",
        goal="weight_loss",
        dietary_restrictions=[],
    )
    assert round(profile.height_cm, 2) == 177.8


def test_body_fat_percentage_bounds():
    with pytest.raises(ValueError):
        PhysicalProfile(
            weight_value=80,
            weight_unit="kg",
            height_value=180,
            height_unit="cm",
            age=30,
            gender="male",
            activity_level="sedentary",
            goal="maintenance",
            dietary_restrictions=[],
            body_fat_percentage=75,
            body_fat_source="dxa",
        )


def test_recipe_total_calories_must_be_positive():
    with pytest.raises(ValueError):
        Recipe(
            title="Bad Recipe",
            total_calories=0,
            macros=Macronutrients(protein=10, carbs=10, fats=10),
            cooking_time=10,
            ingredients=[Ingredient(name="egg", amount="1")],
            instructions=["Cook it."],
        )
