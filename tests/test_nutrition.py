from app.models import PhysicalProfile
from app.nutrition import calculate_targets, select_equation


def test_select_equation_defaults_to_mifflin():
    profile = PhysicalProfile(
        weight_value=80,
        weight_unit="kg",
        height_value=180,
        height_unit="cm",
        age=30,
        gender="male",
        activity_level="sedentary",
        goal="maintenance",
        dietary_restrictions=[],
    )

    equation = select_equation(profile)

    assert equation.equation == "mifflin_st_jeor"
    assert equation.status == "default_estimate"


def test_select_equation_uses_cunningham_for_credible_body_fat():
    profile = PhysicalProfile(
        weight_value=80,
        weight_unit="kg",
        height_value=180,
        height_unit="cm",
        age=30,
        gender="male",
        activity_level="moderately_active",
        goal="maintenance",
        dietary_restrictions=[],
        body_fat_percentage=15,
        body_fat_source="dxa",
    )

    equation = select_equation(profile)

    assert equation.equation == "cunningham"
    assert equation.confidence == "high"


def test_calculate_targets_returns_macro_summary():
    profile = PhysicalProfile(
        weight_value=100,
        weight_unit="kg",
        height_value=180,
        height_unit="cm",
        age=30,
        gender="male",
        activity_level="sedentary",
        goal="maintenance",
        dietary_restrictions=[],
    )

    results = calculate_targets(profile)

    assert results.target_calories > 2000
    assert results.protein == 200
    assert results.carbs >= 0

def test_calculate_meal_targets_divides_daily_targets():
    from app.models import EquationChoice, NutritionTargets
    from app.nutrition import calculate_meal_targets

    daily = NutritionTargets(
        equation=EquationChoice(
            equation="mifflin_st_jeor",
            status="default_estimate",
            confidence="low",
        ),
        resting_energy=1800,
        tdee=2400,
        target_calories=2400,
        protein=150,
        carbs=300,
        fats=90,
    )

    meal = calculate_meal_targets(daily, meals_per_day=3)

    assert meal.target_calories == 800
    assert meal.protein == 50
    assert meal.carbs == 100
    assert meal.fats == 30
