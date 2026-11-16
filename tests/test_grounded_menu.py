from unittest.mock import patch

from app.main import main


def test_grounded_meal_passes_restrictions_and_shows_reminder(capsys):
    meal = {"ingredients": [("Chicken breast", "100")], "totals": {}}
    with patch("builtins.input", side_effect=["3", "no pork", "4"]), \
         patch("app.main.build_meal", return_value=meal), \
         patch("app.main.generate_meal_instructions", return_value="Cook the chicken.") as generate:
        main()

    assert generate.call_args.args[0]["restrictions"] == "no pork"
    output = capsys.readouterr().out
    assert "Cook the chicken." in output
    assert "Check product labels" in output
    assert "suggested extras are not included" in output
