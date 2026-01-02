import pytest
from app.models import PhysicalProfile

def test_weight_conversion():
    # Setup: Create a profile with lbs
    profile = PhysicalProfile(
        weight_value=200,
        weight_unit="lbs",
        height_value=180,
        height_unit="cm",
        age=30,
        gender="male",
        activity_level="sedentary",
        goal="weight_loss",
        dietary_restrictions=[]
    )
    # Assert: 200 lbs should be roughly 90.7 kg
    assert round(profile.weight_kg, 1) == 90.7

def test_height_conversion_ft():
    profile = PhysicalProfile(
        weight_value=80,
        weight_unit="kg",
        height_value=6,
        height_unit="ft",
        age=30,
        gender="male",
        activity_level="sedentary",
        goal="weight_loss",
        dietary_restrictions=[]
    )
    # Assert: 6 ft should be roughly 182.88 cm
    assert round(profile.height_cm, 2) == 182.88