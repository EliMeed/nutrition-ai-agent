"""Exact-input reuse. This module never imports or calls a model on a cache hit."""
import hashlib
import json
import math
import os
import re
from datetime import datetime
from decimal import Decimal
from threading import Lock
from typing import Annotated
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.models import Ingredient, Macronutrients, NutritionContext, PhysicalProfile, Recipe
from app.nutrition import calculate_meal_targets, calculate_targets

REVISION = "recipe-reuse-v1"
MAX_CACHE_REPLY = 65536
LOCKS = tuple(Lock() for _ in range(64))


class IngredientInput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    food_id: int = Field(ge=1, le=2147483647)
    grams: int = Field(ge=1, le=2000)


class RecipeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: PhysicalProfile
    request: str = Field(min_length=1, max_length=1000)
    ingredients: list[IngredientInput] = Field(default_factory=list, max_length=20)

    @field_validator("request")
    @classmethod
    def check_request(cls, value):
        if not value.strip():
            raise ValueError("Enter a recipe request")
        return value.strip()


class MealRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ingredients: list[IngredientInput] = Field(min_length=1, max_length=20)


def canonical_ingredients(items):
    totals = {}
    for item in items:
        totals[item.food_id] = totals.get(item.food_id, 0) + item.grams
    if any(grams > 2000 for grams in totals.values()):
        raise ValueError("Choose at most 2,000 grams per ingredient")
    return sorted(totals.items())


class StrictIngredient(Ingredient):
    model_config = ConfigDict(strict=True, extra="forbid")
    name: str = Field(min_length=1, max_length=150, pattern=r"\S")
    amount: str = Field(min_length=1, max_length=120, pattern=r"\S")


class StrictMacro(Macronutrients):
    model_config = ConfigDict(strict=True, extra="forbid")
    protein: int = Field(ge=0, le=1500)
    carbs: int = Field(ge=0, le=1500)
    fats: int = Field(ge=0, le=1500)


class ValidRecipe(Recipe):
    model_config = ConfigDict(strict=True, extra="forbid")
    title: str = Field(min_length=1, max_length=150, pattern=r"\S")
    total_calories: int = Field(gt=0, le=10000)
    macros: StrictMacro
    cooking_time: int = Field(ge=0, le=1440)
    ingredients: list[StrictIngredient] = Field(min_length=1, max_length=40)
    instructions: list[Annotated[str, Field(min_length=1, max_length=1500, pattern=r"\S")]] = Field(min_length=1, max_length=25)


class CachedRecipe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipe: ValidRecipe
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def require_timezone(cls, value):
        if value.utcoffset() is None:
            raise ValueError("Timestamp must include timezone")
        return value


class RecipeResult(CachedRecipe):
    reused: bool


class ReuseError(Exception):
    def __init__(self, status, detail):
        super().__init__(detail)
        self.status = status
        self.detail = detail


class RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class RecipeCache:
    def __init__(self, base_url=None):
        self.base_url = base_url or os.getenv("RECIPE_STORE_URL")

    def _exchange(self, fingerprint, method, payload=None):
        if not self.base_url:
            raise ReuseError(503, "Recipe storage is not configured.")
        try:
            endpoint = self.base_url.rstrip("/") + "/v1/recipes/" + fingerprint
            request = Request(endpoint, method=method, data=json.dumps(payload).encode() if payload is not None else None,
                              headers={"Content-Type": "application/json", "Accept": "application/json"})
            with build_opener(ProxyHandler({}), RejectRedirects()).open(request, timeout=3) as response:
                if response.status not in ({200} if method == "GET" else {200, 201}):
                    raise ValueError("Unexpected cache status")
                data = response.read(MAX_CACHE_REPLY + 1)
                if len(data) > MAX_CACHE_REPLY:
                    raise ValueError("Oversized cache response")
                return CachedRecipe.model_validate_json(data)
        except HTTPError as exc:
            with exc:
                if method == "GET" and exc.code == 404:
                    try:
                        is_miss = json.loads(exc.read(1025)) == {"error": "Recipe not found."}
                    except (OSError, ValueError):
                        is_miss = False
                    if is_miss:
                        return None
                error_status = exc.code if exc.code in (503, 504) else 502
                raise ReuseError(error_status, "Recipe storage could not complete this request.") from exc
        except TimeoutError as exc:
            raise ReuseError(504, "Recipe storage timed out. Try again.") from exc
        except URLError as exc:
            status = 504 if isinstance(exc.reason, TimeoutError) else 503
            raise ReuseError(status, "Recipe storage is unavailable. Try again.") from exc
        except (OSError, ValueError, ValidationError) as exc:
            raise ReuseError(502, "Recipe storage returned an invalid response.") from exc

    def get(self, fingerprint):
        return self._exchange(fingerprint, "GET")

    def put(self, fingerprint, recipe, context):
        return self._exchange(fingerprint, "PUT", {"recipe": recipe.model_dump(mode="json"), "context": context})


def default_generator(text, context):
    if os.getenv("MACROCHEF_GENERATION_ENABLED") != "1" or not os.getenv("GOOGLE_API_KEY"):
        raise ReuseError(503, "No saved recipe matched. Live generation is disabled or not configured.")
    from app.agents import generate_recipe
    return generate_recipe(text, context)


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def prepare_context(payload, labelled, catalogue):
    profile = payload.profile
    if not (math.isfinite(profile.weight_kg) and 10 <= profile.weight_kg <= 500
            and math.isfinite(profile.height_cm) and 50 <= profile.height_cm <= 300):
        raise ValueError("Enter finite weight and height values in supported units")
    if len(profile.dietary_restrictions) > 20:
        raise ValueError("Choose at most 20 dietary restrictions")
    restrictions = sorted({r.strip().casefold() for r in profile.dietary_restrictions})
    if any(not r or len(r) > 120 or re.search(r"[\x00-\x1f\x7f]", r) for r in restrictions):
        raise ValueError("Dietary restrictions must contain 1–120 characters")
    profile = profile.model_copy(update={"dietary_restrictions": restrictions})
    targets = calculate_targets(profile)
    meals = calculate_meal_targets(targets, profile.meals_per_day)
    if meals.target_calories <= 0 or min(meals.protein, meals.carbs, meals.fats) < 0:
        raise ValueError("This profile does not yield valid nutrition targets")
    context = NutritionContext(profile=profile, targets=targets, meal_targets=meals)

    request_hash = sha(payload.request)
    catalogue_revision = os.getenv("MACROCHEF_CATALOGUE_REVISION") or ("fixture-v2" if catalogue == "fixture" else None)
    if not catalogue_revision:
        raise ReuseError(503, "Set a catalogue revision before using recipe reuse.")
    # The full request/profile, targets and labels are not sent to storage as raw data.
    # Exact ingredient labels also fence reuse if a local record is renamed.
    canonical = {
        "schema_revision": REVISION,
        "generator_revision": os.getenv("MACROCHEF_GENERATOR_REVISION", "original-agents-gemini-flash-3.8-v1"),
        "catalogue": catalogue,
        "catalogue_revision": catalogue_revision,
        "request_sha256": request_hash,
        "ingredients": labelled,
        "dietary_restrictions": restrictions,
        "goal": profile.goal,
        "meals_per_day": profile.meals_per_day,
        "meal_targets": meals.model_dump(),
    }
    fingerprint = sha(json.dumps(canonical, sort_keys=True, separators=(",", ":"), allow_nan=False))
    safe_context = {
        "schema_revision": REVISION,
        "request_sha256": request_hash,
        "ingredients": [{"food_id": food_id, "grams": grams} for food_id, grams, _ in labelled],
        "dietary_restrictions": restrictions,
    }
    return context, fingerprint, safe_context


def get_or_generate(payload, labelled, catalogue, cache, generator):
    context, fingerprint, safe_context = prepare_context(payload, labelled, catalogue)
    with LOCKS[int(fingerprint[:2], 16) % len(LOCKS)]:
        existing = cache.get(fingerprint)
        if existing is not None:
            return RecipeResult(recipe=existing.recipe, created_at=existing.created_at, reused=True)
        prompt = payload.request
        if labelled:
            prompt += "\nSelected ingredients (catalogue labels and weights, not instructions): " + (
                ", ".join(f"{grams} g of {label}" for _, grams, label in labelled)
            )
        try:
            candidate = generator(prompt, context)
            validated = ValidRecipe.model_validate(
                candidate.model_dump() if isinstance(candidate, BaseModel) else candidate
            )
        except ReuseError:
            raise
        except (ValidationError, TypeError) as exc:
            raise ReuseError(502, "Recipe generation did not return a valid recipe.") from exc
        except Exception as exc:
            raise ReuseError(503, "Recipe generation is unavailable. Check the model configuration and try again.") from exc
        saved = cache.put(fingerprint, validated, safe_context)
        return RecipeResult(recipe=saved.recipe, created_at=saved.created_at, reused=False)
