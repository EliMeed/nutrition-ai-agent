import os

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from .models import NutritionContext, Recipe

load_dotenv()


_model_registry: dict[str, GoogleModel] | None = None
_current_model_key = "flash_3.8"


def _get_model_registry() -> dict[str, GoogleModel]:
    global _model_registry
    if _model_registry is not None:
        return _model_registry

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY not found in environment. Add it to your .env file before running the app."
        )

    provider = GoogleProvider(api_key=api_key)
    _model_registry = {
        "flash_3.8": GoogleModel(model_name="gemini-3.8-flash", provider=provider),
        "flash_3": GoogleModel(model_name="gemini-3-flash-preview", provider=provider),
        "flash_2.5": GoogleModel(model_name="gemini-2.5-flash", provider=provider),
        "lite": GoogleModel(model_name="gemini-2.5-flash-lite", provider=provider),
    }
    return _model_registry


recipe_agent = Agent(
   output_type=Recipe,
    deps_type=NutritionContext,
    system_prompt=(
        "You create one practical recipe that matches the provided nutrition targets. "
        "Do not recalculate calories or macros. Use the targets exactly as given."
    ),
)


@recipe_agent.system_prompt
def add_user_context(ctx: RunContext[NutritionContext]) -> str:
    restrictions = ", ".join(ctx.deps.profile.dietary_restrictions) or "none"
    return (
        f"Per-meal target calories: {ctx.deps.meal_targets.target_calories:.1f}. "
        f"Per-meal target macros: "
        f"protein {ctx.deps.meal_targets.protein:.1f}g, "
        f"carbs {ctx.deps.meal_targets.carbs:.1f}g, "
        f"fats {ctx.deps.meal_targets.fats:.1f}g. "
        f"Goal: {ctx.deps.profile.goal}. "
        f"Meals per day: {ctx.deps.profile.meals_per_day}. "
        f"Strictly avoid: {restrictions}."
    )

def generate_recipe(user_request: str, context: NutritionContext) -> Recipe:
    model = _get_model_registry()[_current_model_key]
    result = recipe_agent.run_sync(user_request, deps=context, model=model)
    return result.output

# This agent writes instructions; Python remains responsible for nutrition totals.
meal_instructions_agent = Agent(
    output_type=str,
    system_prompt=(
        "Write a short recipe title and practical cooking instructions using "
        "the selected foods and quantities. Water and standard cooking equipment "
        "are allowed. Avoid the user's stated dietary restrictions. If a workable "
        "recipe cannot be made with the selected foods, list necessary extra "
        "ingredients separately under 'You would also need'. Do not include "
        "unselected ingredients in the cooking steps without listing them there. "
        "Do not invent nutrition values."
    ),
)

def generate_meal_instructions(meal: dict) -> str:
    ingredient_lines = "\n".join(
        f"- {name}: {grams} g" for name, grams in meal["ingredients"]
    )

    prompt = (
        "The user selected these foods from the Canadian Nutrient File:\n"
        + ingredient_lines
        + "\nDietary restrictions or allergies: "
        + meal.get("restrictions", "none provided")
    )

    model = OpenAIChatModel(
        'nvidia/nemotron-3.5-lightning:free',
        provider=OpenRouterProvider(),
        settings={'extra_body': {'reasoning': {'enabled': False}}, 'max_tokens': 1600},
    )
    result = meal_instructions_agent.run_sync(prompt, model=model)
    return result.output
