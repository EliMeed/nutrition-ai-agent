# MacroChef

MacroChef is a nutrition and recipe generator. It collects a user's profile, calculates calorie and macro targets deterministically in Python, then uses Gemini to generate a recipe guided by those targets.

This public version is intentionally lean: a typed CLI app with explicit nutrition logic and a constrained AI step at the end.

## What it does

- Calculates resting energy, TDEE, and macro targets from user biometrics
- Uses `Mifflin-St Jeor` by default
- Uses `Cunningham` when the user provides a credible body-fat estimate
- Supports multiple units for weight and height, including `5 ft 10 in`
- Generates a structured recipe using the calculated targets as guidance
- Builds a meal from selected foods and calculates nutrition from the local food database
- Starts each CLI session fresh without saving user history

## Why the architecture matters

The app does not ask the model to do nutrition math.

Instead it uses a two-stage flow:
1. Python validates inputs and calculates targets locally
2. The model receives the finalized targets and generates a recipe

That keeps the system easier to reason about and reduces unnecessary model usage.

## Stack

- Python
- Pydantic
- pydantic-ai
- Gemini via Google's API
- pytest

## Run locally

### With `uv`

```bash
uv sync
uv sync --group dev
cp .env.example .env
uv run python -m app.main
```

### With `pip`

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest pytest-dotenv
python -m app.main
```

Add your API key to `.env`:

```env
GOOGLE_API_KEY=your_api_key_here
```

## Example flow

Choose `Build a meal` to select foods and calculate their nutrition, or `Generate a recipe` for the AI recipe flow.

## Project structure

```text
app/
  agents.py       Recipe-generation agent
  main.py         CLI flow
  meal_cli.py     Ingredient search and meal builder
  models.py       Typed data contracts
  nutrition.py    Deterministic nutrition logic
  pipeline/
    cnf.py        Read Canadian Nutrient File data
    load_cnf.py   Load food data into PostgreSQL
    food_lookup.py  Food search and nutrient calculations
sql/
  schema.sql      Database tables
tests/
  test_models.py
  test_nutrition.py
  test_meal_calculation.py
```

## Testing

```bash
pytest
```

## Notes

MacroChef calculates nutrition targets and generates recipes. The food data pipeline also loads Canadian Nutrient File data into a local PostgreSQL database. The recipe agent doesn’t query that database yet, and the app doesn’t currently save users’ meal histories.

## Current capabilities

- Calculate daily and per-meal nutrition targets from a physical profile.
- Generate a recipe using the existing AI agent.
- Import Canadian Nutrient File foods, nutrient definitions, and nutrient amounts into a local PostgreSQL database.

The meal builder queries the imported food database. The recipe agent does not yet use it.

## In progress

- Document and verify a reproducible local setup for the food import.
- Provide an API for querying the imported food data.
- Connect the food data to the recipe workflow.

## Food data import

The local pipeline reads Canadian Nutrient File CSVs and loads food and nutrient data into PostgreSQL. The CSVs are not included in this repository. The data used for development came from the [Canadian Nutrient File, 2015](https://www.canada.ca/en/health-canada/services/food-nutrition/healthy-eating/nutrient-data/canadian-nutrient-file-2015-download-files.html).

Place these files in `data/cnf/`:

- `FOOD NAME.csv`
- `NUTRIENT NAME.csv`
- `NUTRIENT AMOUNT.csv`

With PostgreSQL running and a new `macrochef` database available, run from the project root:

```bash
psql -d macrochef -f sql/schema.sql
python -m app.pipeline.load_cnf
```

The import reports rejected rows and updates existing food–nutrient pairs on rerun. One row in the dataset used during development referenced nutrient ID 328, which was absent from the nutrient definitions.

### Troubleshooting

If the meal builder cannot access the food database, check that PostgreSQL is running and that the `macrochef` database, schema, and CNF data have been set up using the steps above. Check your PostgreSQL connection permissions if the problem continues.
