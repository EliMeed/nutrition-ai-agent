from app.agents import calculate_targets
from app.models import PhysicalProfile

def test_calculate_targets_logic():
    profile = PhysicalProfile(
        weight_value=100, # 100kg
        weight_unit="kg",
        height_value=180, # 180cm
        height_unit="cm",
        age=30,
        gender="male",
        activity_level="sedentary",
        goal="maintenance",
        dietary_restrictions=[]
    )
    
    results = calculate_targets(profile)
    
    # BMR for 100kg, 180cm, 30yo Male = 2000 + 1125 - 150 + 5 = 2980
    # Sedentary TDEE = 2980 * 1.2 = 3576
    assert results["daily_target_calories"] > 2000
    assert "protein_target_grams" in results