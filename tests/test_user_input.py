
from unittest.mock import patch

import pytest

from app.main import get_user_input


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("", []),
        (" peanuts, dairy , , shellfish ", ["peanuts", "dairy", "shellfish"]),
    ],
)
def test_dietary_restrictions_input(answer, expected):
    answers = iter([
        "180 lbs", "180 cm", "30", "sedentary", "maintain",
        "3", answer, "", "male",
    ])
    with patch("builtins.input", side_effect=answers):
        profile = get_user_input()

    assert profile.dietary_restrictions == expected
