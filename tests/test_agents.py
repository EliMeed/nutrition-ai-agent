from unittest.mock import Mock

from app import agents
from app.models import NutritionContext, PhysicalProfile, Recipe
from app.nutrition import calculate_meal_targets, calculate_targets


def test_generate_recipe_passes_context_and_model(monkeypatch):
    profile = PhysicalProfile(
        weight_value=80,
        weight_unit="kg",
        height_value=180,
        height_unit="cm",
        age=30,
        gender="male",
        activity_level="sedentary",
        goal="maintenance",
    )
    
    daily_targets = calculate_targets(profile)
    meal_targets = calculate_meal_targets(daily_targets, profile.meals_per_day)
    context = NutritionContext(
        profile=profile,
        targets=daily_targets,
        meal_targets=meal_targets,
    )
    
    expected_recipe = Recipe(
        title="Test recipe",
        total_calories=500,
        macros={"protein": 30, "carbs": 50, "fats": 18},
        cooking_time=15,
        ingredients=[],
        instructions=[],
    )

    fake_model = object()
    fake_run = Mock(return_value=Mock(output=expected_recipe))
    monkeypatch.setattr(agents, "_get_model_registry", lambda: {"test": fake_model})
    monkeypatch.setattr(agents, "_current_model_key", "test")
    monkeypatch.setattr(agents.recipe_agent, "run_sync", fake_run)

    result = agents.generate_recipe("Make a test meal", context)

    fake_run.assert_called_once_with(
        "Make a test meal", deps=context, model=fake_model
    )

    assert result == expected_recipe

    prompt = agents.add_user_context(Mock(deps=context))

    assert f"Per-meal target calories: {meal_targets.target_calories:.1f}" in prompt
    assert f"protein {meal_targets.protein:.1f}g" in prompt
    assert f"carbs {meal_targets.carbs:.1f}g" in prompt
    assert f"fats {meal_targets.fats:.1f}g" in prompt
