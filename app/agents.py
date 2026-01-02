import os
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from .models import Recipe, PhysicalProfile


api_key = os.getenv('GOOGLE_API_KEY')

if not api_key:
    raise ValueError(
        "❌ GOOGLE_API_KEY not found in environment. "
        "Check your .env file and ensure you are using --env-file .env"
    )

provider = GoogleProvider(api_key=api_key)

model = GoogleModel(model_name='gemini-3-flash-preview', provider=provider)
# The agent returns a Recipe, but calculates the targets based on PhysicalProfile
recipe_agent = Agent(
    model,
    output_type=Recipe,
    deps_type=PhysicalProfile,
    system_prompt="You are a nutritionist AI. Start by using the 'calculate_targets' tool "
        "to determine the user's daily needs. Then, create a recipe that "
        "perfectly fits those calculated macros."
)

@recipe_agent.system_prompt
def add_user_context(ctx: RunContext[PhysicalProfile]) -> str:
    restrictions = ", ".join(ctx.deps.dietary_restrictions) if ctx.deps.dietary_restrictions else "none"
    return (
        f"The user's objective is {ctx.deps.goal}. "
        f"They eat {ctx.deps.meals_per_day} meals per day. "
        f"Strictly avoid: {restrictions}."
    )

@recipe_agent.tool_plain
def calculate_targets(profile: PhysicalProfile) -> dict:
    """Calculates the exact BMR, TDEE, and goal-specific calorie/macro targets."""
    # Mifflin-St Jeor Formula
    if profile.gender == "male":
        bmr = (10 * profile.weight_kg) + (6.25 * profile.height_cm) - (5 * profile.age) + 5
    else:
        bmr = (10 * profile.weight_kg) + (6.25 * profile.height_cm) - (5 * profile.age) - 161

    # Activity Multipliers
    multipliers = {
        "sedentary": 1.2,
        "lightly_active": 1.375,
        "moderately_active": 1.55,
        "very_active": 1.725
    }
    tdee = bmr * multipliers[profile.activity_level]
    
    # Goal Adjustment
    if profile.goal == "weight_loss":
        target = tdee - 500
    elif profile.goal == "muscle_gain":
        target = tdee + 300
    else:
        target = tdee

    return {
        "daily_target_calories": round(target),
        "protein_target_grams": round(profile.weight_kg * 2.0), # 2g of protein per kg of body weight
        "fat_target_grams": round((target * 0.25) / 9)
    }