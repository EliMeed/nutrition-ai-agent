from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PhysicalProfile(BaseModel):
    weight_value: float = Field(gt=0)
    weight_unit: Literal["kg", "lbs"]
    height_value: float = Field(gt=0)
    height_unit: Literal["cm", "in", "ft"]
    height_inches_extra: float = Field(default=0, ge=0, lt=12)
    age: int = Field(ge=10, le=120)
    gender: Literal["male", "female"]
    activity_level: Literal[
        "sedentary",
        "lightly_active",
        "moderately_active",
        "very_active",
    ]
    goal: Literal["weight_loss", "muscle_gain", "maintenance"]
    dietary_restrictions: list[str] = Field(default_factory=list)
    meals_per_day: int = Field(default=3, ge=1, le=6)
    body_fat_percentage: float | None = Field(default=None, gt=0, lt=70)
    body_fat_source: Literal["dxa", "calipers", "smart_scale", "visual_estimate", "other"] | None = None

    @property
    def weight_kg(self) -> float:
        if self.weight_unit == "lbs":
            return self.weight_value * 0.45359237
        return self.weight_value

    @property
    def height_cm(self) -> float:
        if self.height_unit == "in":
            return self.height_value * 2.54
        if self.height_unit == "ft":
            total_inches = (self.height_value * 12) + self.height_inches_extra
            return total_inches * 2.54
        return self.height_value


class EquationChoice(BaseModel):
    equation: Literal["mifflin_st_jeor", "cunningham"]
    status: Literal["default_estimate", "body_fat_based_estimate"]
    confidence: Literal["low", "medium", "high"]


class NutritionTargets(BaseModel):
    equation: EquationChoice
    resting_energy: int
    tdee: int
    target_calories: int
    protein: int
    carbs: int
    fats: int


class MealTargets(BaseModel):
    target_calories: float
    protein: float
    carbs: float
    fats: float


class NutritionContext(BaseModel):
    profile: PhysicalProfile
    targets: NutritionTargets
    meal_targets: MealTargets


class Ingredient(BaseModel):
    name: str
    amount: str


class Macronutrients(BaseModel):
    protein: int
    carbs: int
    fats: int


class Recipe(BaseModel):
    title: str
    total_calories: int
    macros: Macronutrients
    cooking_time: int
    ingredients: list[Ingredient]
    instructions: list[str]

    @field_validator("total_calories")
    @classmethod
    def must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Calories must be greater than zero")
        return value
