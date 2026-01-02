from pydantic import BaseModel, Field, field_validator
from typing import List, Literal

class PhysicalProfile(BaseModel):
    weight_value: float
    weight_unit: Literal["kg", "lbs"]
    height_value: float
    height_unit: Literal["cm", "in", "ft"]
    age: int
    gender: Literal["male", "female"]
    activity_level: Literal["sedentary", "lightly_active", "moderately_active", "very_active"]
    goal: Literal["weight_loss", "muscle_gain", "maintenance"]
    dietary_restrictions: List[str]
    meals_per_day: int = Field(default=3, ge=1, le=6)
    

    @property
    def weight_kg(self) -> float:
        if self.weight_unit == "lbs":
            return self.weight_value * 0.453592
        return self.weight_value
    
    
    @property
    def height_cm(self) -> float:
        if self.height_unit == "in":
            return self.height_value * 2.54
        if self.height_unit == "ft":
            return self.height_value * 30.48
        return self.height_value

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

    @field_validator('total_calories')
    @classmethod
    def must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('Calories must be greater than zero!')
        return v

    

