"""Local HTTP adapter; authoritative server-side deterministic serving math."""
from decimal import Decimal
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path as FilePath
from pydantic import BaseModel

from .reuse import (
    MealRequest, RecipeCache, RecipeRequest, RecipeResult, ReuseError,
    canonical_ingredients, default_generator, get_or_generate,
)
from .repository import DatabaseUnavailable, IDS, make_repository

class Food(BaseModel):
    id: int
    name: str
    preparation: str
    notes: str

class MealNutrition(BaseModel):
    grams: int
    kcal: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None

class Nutrition(MealNutrition):
    id: int

def scale_macros(per_100g: dict[int, Decimal], grams: int) -> list[Decimal | None]:
    """Preserve MacroChef food_lookup.py's Decimal grams/100 scaling and null semantics."""
    weight = Decimal(grams)
    return [per_100g[n] * weight / Decimal("100") if n in per_100g else None for n in IDS]

def create_app(repository=None, serve_frontend=True, cache=None, generator=None) -> FastAPI:
    cache = RecipeCache() if cache is None else cache
    generator = default_generator if generator is None else generator
    repo = repository if repository is not None else make_repository()
    app = FastAPI(title="MacroChef", version="0.1.0")

    @app.exception_handler(DatabaseUnavailable)
    def database_unavailable(_request: Request, _exc: DatabaseUnavailable):
        return JSONResponse({"detail": "Food database temporarily unavailable. Try again."}, 503)

    @app.get("/api/info")
    def info():
        return {"storage": repo.mode, "data": "illustrative fixtures" if repo.uses_fixtures else "configured catalogue; verify source version"}

    @app.get("/api/foods", response_model=list[Food])
    def foods(q: Annotated[str, Query(max_length=100)] = ""):
        return repo.search(q)

    @app.get("/api/foods/{id}/nutrition", response_model=Nutrition)
    def nutrition(id: Annotated[int, Path(ge=1, le=2147483647)],
                  grams: Annotated[int, Query(ge=1, le=2000)],):
        values = repo.macros_per_100g(id)
        if values is None:
            raise HTTPException(404, "Food not found")
        return Nutrition(id=id, grams=grams,
                         **dict(zip(("kcal", "protein_g", "carbs_g", "fat_g"), scale_macros(values, grams))))

    def selected_ingredients(items):
        try:
            return canonical_ingredients(items)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/meals/nutrition", response_model=MealNutrition)
    def meal_nutrition(payload: MealRequest):
        items = selected_ingredients(payload.ingredients)
        totals = [Decimal("0")] * len(IDS)
        for food_id, grams in items:
            values = repo.macros_per_100g(food_id)
            if values is None:
                raise HTTPException(404, "Food not found")
            totals = [total + value if total is not None and value is not None else None
                      for total, value in zip(totals, scale_macros(values, grams))]
        return MealNutrition(grams=sum(grams for _, grams in items),
                             **dict(zip(("kcal", "protein_g", "carbs_g", "fat_g"), totals)))

    @app.post("/api/recipes", response_model=RecipeResult)
    def recipes(payload: RecipeRequest):
        labelled = []
        for food_id, grams in selected_ingredients(payload.ingredients):
            label = repo.food_label(food_id)
            if label is None:
                raise HTTPException(404, "Food not found")
            labelled.append((food_id, grams, label))
        catalogue = "fixture" if repo.uses_fixtures else "imported"
        try:
            return get_or_generate(payload, labelled, catalogue, cache, generator)
        except ReuseError as exc:
            raise HTTPException(exc.status, exc.detail) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    dist = FilePath(__file__).resolve().parent.parent / "frontend" / "dist"
    if serve_frontend and (dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app

app = create_app()
