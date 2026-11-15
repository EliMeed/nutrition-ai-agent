from decimal import Decimal
from unittest.mock import patch

from app.pipeline.food_lookup import calculate_meal_macros


def test_meal_totals_and_missing_values():
    foods = [
        {"amounts": {"calories": Decimal("100"), "protein": Decimal("10"), "carbs": Decimal("5"), "fat": Decimal("2")}},
        {"amounts": {"calories": Decimal("50"), "protein": None, "carbs": Decimal("3"), "fat": Decimal("1")}},
    ]
    with patch("app.pipeline.food_lookup.calculate_food_macros", side_effect=foods):
        result = calculate_meal_macros([(1, "100"), (2, "50")])

    assert result == {
        "calories": Decimal("150"),
        "protein": None,
        "carbs": Decimal("8"),
        "fat": Decimal("3"),
    }
