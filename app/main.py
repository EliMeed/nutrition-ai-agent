import sys
import re
from app.agents import recipe_agent
from app.models import PhysicalProfile
from pydantic import ValidationError

def parse_input(prompt: str, valid_units: list) -> tuple[float, str]:
    """Parses a string like '180 lbs' into (180.0, 'lbs')."""
    while True:
        raw = input(prompt).strip().lower()
        match = re.match(r"([0-9.]+)\s*([a-zA-Z]+)", raw)
        if match:
            try:
                value = float(match.group(1))
                unit = match.group(2)
                if unit in valid_units:
                    return value, unit
                print(f"❌ Supported units: {', '.join(valid_units)}")
            except ValueError:
                print("❌ Invalid number format.")
        else:
            print(f"❌ Format error. for weight try '180 lbs' or '80 kg'. If its height try '70 in', '180 cm', or '5 ft 10 in'.")

def get_user_input() -> PhysicalProfile:
    print("\n--- 🥗 AI Nutritionist Profile Setup ---")
    try:
        # 1. Capture Stats
        weight_val, weight_unit = parse_input("Weight (e.g., 205 lbs): ", ["kg", "lbs"])
        
        # Pro-tip: For '6 ft 0 in', just type '6 ft' for now, 
        # or we can update the parser later to handle complex strings.
        height_val, height_unit = parse_input("Height (e.g., 6 ft, 180 cm): ", ["cm", "in", "ft"])
        
        
        while True:
            age_input = input("Age: ").strip()
            if age_input.isdigit():
                age = int(age_input)
                if 10 <= age <= 120:
                    break
                else:
                    print("❌ Please enter a realistic age (10-120).")
            else:
                print("❌ Invalid input. Please enter a number for your age.")
       
        
        while True:
            gender = input("Gender (male/female): ").strip().lower()
            if gender in ["male", "female"]:
                break
            print("❌ Please enter exactly 'male' or 'female'.")
        
        # 2. Map user's input to Activity Level
        print("\nLevels: sedentary, lightly active, moderately active, very active")
        act_input = input("Activity level (or just first letter): ").strip().lower()
        activity_map = {
            "s": "sedentary", "l": "lightly_active", 
            "m": "moderately_active", "v": "very_active"
        }
        
        # Use the map if they type one letter, otherwise use what they typed
        activity = activity_map.get(act_input[0], act_input) if act_input else "sedentary"

        # 3. Map user's input to Fitness Goal  
        goal_input = input("Fitness goal: ").strip().lower()
        if "fat" in goal_input or "lose" in goal_input or "weight" in goal_input:
            goal = "weight_loss"
        elif "muscle" in goal_input or "gain" in goal_input:
            goal = "muscle_gain"
        else:
            goal = "maintenance"

        restrictions = input("\nDietary restrictions (comma-separated): ")
        restrictions_list = [r.strip() for r in restrictions.split(",") if r.strip()]

        return PhysicalProfile(
            weight_value=weight_val,
            weight_unit=weight_unit,
            height_value=height_val,
            height_unit=height_unit,
            age=age,
            gender=gender,
            activity_level=activity,
            goal=goal,
            dietary_restrictions=restrictions_list
        )
    except Exception as e:
        print(f"❌ Error setting up profile: {e}")
        sys.exit(1)

def main():
    # 1. Collect user profile information
    user = get_user_input()

    # 2. Get the specific request
    user_request = input("\nWhat kind of recipe are you looking for today? ")

    # 3. Run the agent with the user's profile
    print("\nCooking up your personalized recipe... 👨‍🍳")
    try:
        result = recipe_agent.run_sync(user_request, deps=user)
        recipe = result.output
        
        print(f"\n✨ DONE! Here is your '{recipe.title}'")
        print(f"🔥 Calories: {recipe.total_calories} kcal")
        # Display macros
        print(f"💪 Macros: P:{recipe.macros.protein}g | C:{recipe.macros.carbs}g | F:{recipe.macros.fats}g")
        print(f"⏱️ Cooking Time: {recipe.cooking_time} minutes")
        
        print("\n🛒 Ingredients:")
        for ing in recipe.ingredients:
            print(f"  - {ing.amount} {ing.name}")
        
        print("\n📝 Instructions:")
        for i, step in enumerate(recipe.instructions, 1):
            print(f"  {i}. {step}")

    except ValidationError as e:
        print(f"❌ AI Validation Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

if __name__ == "__main__":
    main()