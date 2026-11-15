from .models import EquationChoice, MealTargets, NutritionTargets, PhysicalProfile


_ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "lightly_active": 1.375,
    "moderately_active": 1.55,
    "very_active": 1.725,
}


def _body_fat_confidence(source: str | None) -> str:
    if source == "dxa":
        return "high"
    if source == "calipers":
        return "medium"
    return "low"


def select_equation(profile: PhysicalProfile) -> EquationChoice:
    if profile.body_fat_percentage is not None:
        confidence = _body_fat_confidence(profile.body_fat_source)
        if confidence in {"high", "medium"}:
            return EquationChoice(
                equation="cunningham",
                status="body_fat_based_estimate",
                confidence=confidence,
            )

    return EquationChoice(
        equation="mifflin_st_jeor",
        status="default_estimate",
        confidence="low",
    )


def calculate_resting_energy(profile: PhysicalProfile, equation: EquationChoice) -> int:
    if equation.equation == "cunningham":
        fat_free_mass = profile.weight_kg * (1 - (profile.body_fat_percentage or 0) / 100)
        return round(500 + (22 * fat_free_mass))

    if profile.gender == "male":
        value = (10 * profile.weight_kg) + (6.25 * profile.height_cm) - (5 * profile.age) + 5
    else:
        value = (10 * profile.weight_kg) + (6.25 * profile.height_cm) - (5 * profile.age) - 161
    return round(value)


def calculate_targets(profile: PhysicalProfile) -> NutritionTargets:
    equation = select_equation(profile)
    resting_energy = calculate_resting_energy(profile, equation)
    tdee = round(resting_energy * _ACTIVITY_MULTIPLIERS[profile.activity_level])

    if profile.goal == "weight_loss":
        target_calories = tdee - 500
    elif profile.goal == "muscle_gain":
        target_calories = tdee + 300
    else:
        target_calories = tdee

    protein = round(profile.weight_kg * 2.0)
    fats = round((target_calories * 0.25) / 9)
    carbs = max(0, round((target_calories - (protein * 4) - (fats * 9)) / 4))

    return NutritionTargets(
        equation=equation,
        resting_energy=resting_energy,
        tdee=tdee,
        target_calories=target_calories,
        protein=protein,
        carbs=carbs,
        fats=fats,
    )

def calculate_meal_targets(
    targets: NutritionTargets, meals_per_day: int
) -> MealTargets:
    return MealTargets(
        target_calories=targets.target_calories / meals_per_day,
        protein=targets.protein / meals_per_day,
        carbs=targets.carbs / meals_per_day,
        fats=targets.fats / meals_per_day,
    )
