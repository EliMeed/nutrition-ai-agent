# AI Nutritionist Agent

An intelligent AI-powered nutritionist agent that generates personalized recipes based on your physical profile, fitness goals, and dietary restrictions. Built with `pydantic-ai` and Google's Gemini model.

## Features

- 🧮 **Automatic Macro Calculation**: Calculates BMR (Basal Metabolic Rate) and TDEE (Total Daily Energy Expenditure) using the Mifflin-St Jeor formula
- 🎯 **Goal-Oriented Recipes**: Adjusts calorie targets based on fitness goals (weight loss, muscle gain, or maintenance)
- 🥗 **Personalized Meal Planning**: Generates recipes that match your calculated macro and calorie targets
- 🚫 **Dietary Restrictions**: Respects your dietary restrictions and preferences
- 📏 **Flexible Units**: Supports multiple unit systems (kg/lbs for weight, cm/in/ft for height)
- ⚡ **Smart Input Parsing**: Accepts natural language input for activity levels and goals
- 🔒 **Type-Safe**: Built with Pydantic for robust data validation

## Requirements

- Python 3.10 or higher
- Google API key for Gemini model access
- `uv` package manager (recommended) or `pip`

## Installation

### Using `uv` (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd ai-agent
```

2. Install dependencies using `uv`:
```bash
uv sync
```

3. Install development dependencies (for running tests):
```bash
uv sync --group dev
```

### Using `pip`

1. Clone the repository:
```bash
git clone <repository-url>
cd ai-agent
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
```

4. Install development dependencies:
```bash
pip install -e ".[dev]"
```

## Environment Setup

1. Create a `.env` file in the project root:
```bash
touch .env
```

2. Add your Google API key to the `.env` file:
```env
GOOGLE_API_KEY=your_api_key_here
```

**Note**: You can obtain a Google API key from the [Google AI Studio](https://makersuite.google.com/app/apikey).

## Usage

### Running the Application

1. Ensure your `.env` file is set up with your `GOOGLE_API_KEY`

2. Run the main application:
```bash
uv run python -m app.main
```

Or if using `pip`:
```bash
python -m app.main
```

### Example Session

```
--- 🥗 AI Nutritionist Profile Setup ---
Weight (e.g., 205 lbs): 180 lbs
Height (e.g., 6 ft, 180 cm): 6 ft
Age: 30
Gender (male/female): male

Levels: sedentary, lightly active, moderately active, very active
Activity level (or just first letter): m
Goals: weight loss, muscle gain, maintenance
Fitness goal: muscle gain

Dietary restrictions (comma-separated): peanuts, shellfish

What kind of recipe are you looking for today? A high-protein breakfast that's quick to make

Cooking up your personalized recipe... 👨‍🍳

✨ DONE! Here is your 'High-Protein Scrambled Eggs with Turkey'
🔥 Calories: 650 kcal
💪 Macros: P:45g | C:30g | F:20g
⏱️ Cooking Time: 15 minutes

🛒 Ingredients:
  - 6 large eggs
  - 4 oz turkey breast, diced
  - 1 cup spinach
  - 1 tbsp olive oil
  ...

📝 Instructions:
  1. Heat olive oil in a non-stick pan
  2. Add diced turkey and cook until golden
  ...
```

### Activity Levels

- **sedentary**: Little to no exercise (multiplier: 1.2)
- **lightly_active**: Light exercise 1-3 days/week (multiplier: 1.375)
- **moderately_active**: Moderate exercise 3-5 days/week (multiplier: 1.55)
- **very_active**: Heavy exercise 6-7 days/week (multiplier: 1.725)

### Fitness Goals

- **weight_loss**: Reduces daily calories by 500 kcal
- **muscle_gain**: Increases daily calories by 300 kcal
- **maintenance**: Uses calculated TDEE without adjustment

## Project Structure

```
ai-agent/
├── app/
│   ├── __init__.py
│   ├── agents.py          # AI agent configuration and tools
│   ├── main.py            # CLI application entry point
│   ├── models.py          # Pydantic models (PhysicalProfile, Recipe, etc.)
│   └── tools.py           # Additional utility functions
├── tests/
│   ├── test_agents.py     # Tests for agent functionality
│   └── test_models.py     # Tests for model validation
├── pyproject.toml         # Project configuration and dependencies
├── uv.lock                # Dependency lock file (if using uv)
├── .env                   # Environment variables (not in git)
└── README.md              # This file
```

## How It Works

1. **Profile Collection**: The application collects your physical profile (weight, height, age, gender, activity level, goals, and dietary restrictions)

2. **Target Calculation**: The `calculate_targets` tool computes:
   - BMR using the Mifflin-St Jeor formula
   - TDEE by applying activity level multipliers
   - Goal-adjusted calorie targets
   - Protein targets (2g per kg of body weight)
   - Fat targets (25% of total calories)



3. **Recipe Generation**: The AI agent uses these calculated targets to generate a personalized recipe that:
   - Matches your calorie and macro targets
   - Respects your dietary restrictions
   - Aligns with your fitness goals
   - Includes detailed ingredients and step-by-step instructions

### 📊 Nutritional Intelligence
Once the user provides their physical metrics, the system performs a multi-stage analysis:
- **Baseline Analysis**: Converts raw height/weight data into a standardized metric profile.
- **Intake Requirement Synthesis**: Calculates the specific TDEE (Total Daily Energy Expenditure) and provides a clear breakdown of daily requirements before recipe generation.
- **Caloric Partitioning**: Distributes the daily requirement across the user's preferred meal frequency.

## Testing

Run the test suite:

```bash
uv run pytest
```

Or with `pip`:
```bash
pytest
```

## Development

The project uses:
- **pydantic-ai**: For building type-safe AI agents
- **pydantic**: For data validation and modeling
- **pytest**: For testing
- **uv**: For fast dependency management (optional but recommended)

## 🚀 Roadmap & Future Enhancements

I am currently working on expanding the "Nutritionist" capabilities of the agent to move from single-recipe generation to full-day optimization:

- [ ] **Daily Intake Dashboard**: Enhance the CLI output to show a comprehensive breakdown of BMR, TDEE, and Macro-targets immediately after data entry.
- [ ] **Full-Day Meal Scheduling**: Implement logic to generate a 24-hour meal plan (Breakfast, Lunch, Dinner, and Snacks) that sums perfectly to the user's TDEE.
- [ ] **Intake Tracking Persistence**: Add a SQLite backend to allow the agent to "remember" previous meals and adjust the calorie budget for the remainder of the day.
- [ ] **Dynamic Macro Ratios**: Allow users to toggle between "High Protein," "Keto," or "Balanced" targets.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

[Add contribution guidelines if applicable]

## Support

For issues, questions, or contributions, please open an issue on the repository.

