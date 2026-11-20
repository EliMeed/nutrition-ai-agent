# MacroChef: recipe reuse

## Flow

The browser only calls FastAPI. The **Nutrition** view builds a meal from individually weighed foods and sums their recorded macros in Python. The **Recipe** view uses the same personal target calculation and structured recipe agent as the terminal app. The previous Node template generator is not part of this flow.

FastAPI validates the input and calculates targets, then checks the private Node recipe store for an exact match. A hit reuses the saved recipe and timestamp without contacting a model. A confirmed miss runs the existing agent, validates its structured output, and saves it before returning. An unreachable or malformed store is not a cache miss. Node only performs reads and writes; it never gets a model key. Previously saved recipes are not a substitute for updated dietary constraints. Dietary preferences guide generation; the app does not certify allergen safety.

Separate data stores keep the read-only nutrient catalogue apart from writable saved recipes. The browser displays ingredient nutrition and recipe estimates separately. The deterministic energy and target calculations do not depend on an AI response.

## Run locally

Requires Node 22+, Python 3.11+, and PostgreSQL. Use a dedicated recipe database. **Do not apply the following schema to the existing imported food database.**

```bash
# From this draft's root, with your new recipe database already provisioned:
psql "$RECIPE_DATABASE_URL" -v ON_ERROR_STOP=1 -f recipe/schema.sql
(cd recipe && npm ci)
(cd frontend && npm ci && npm run build)
bash run-local.sh
```

Set `RECIPE_DATABASE_URL` in the shell before running; native startup uses loopback only. The native default serves http://127.0.0.1:8002/. If testing the imported catalogue instead of the separate fixture, also set a read-only `MACROCHEF_DATABASE_URL` and `MACROCHEF_CATALOGUE_REVISION` in the shell. A catalogue revision scopes saved results to the exact source; change it when the data changes.

For an isolated Compose setup, build the frontend first, then run `docker compose up --build`. The default address is http://127.0.0.1:8000/. Neither PostgreSQL nor Node is exposed to the host by Compose. The fixed passwords in this Compose file are for this local demo only. Docker is optional; it is not needed for the Arch instructions above. `docker compose down` leaves named volumes intact.

Only opt in to a live agent call by setting `MACROCHEF_GENERATION_ENABLED=1` and the original project’s `GOOGLE_API_KEY` locally. On a miss, the agent receives calculated nutrition targets, food labels and serving amounts, dietary restrictions, and the recipe request. Never enter private details in free-text fields, and never commit keys. The store does not retain a raw physical profile or raw free-text prompt.

## Interface

- `GET /api/foods?q=...` returns a list, possibly empty.
- `GET /api/foods/{id}/nutrition?grams=...` returns nutrition for one serving.
- `POST /api/meals/nutrition` returns summed nutrition for several weighed selections. Missing source amounts remain unavailable instead of silently becoming zero.
- `POST /api/recipes` is the only web endpoint that may generate. Its response contains the recipe, creation timestamp and a reuse flag.
- Internally, Node exposes `GET /health`, and `GET` / `PUT /v1/recipes/{key}`. Only an explicit `404` from the lookup permits generation. An atomic insert preserves the first saved result for a key.

Concurrent requests handled by separate API workers can both miss before either saves. The database still deduplicates the saved record, but a multi-worker deployment would need shared request coordination to guarantee a single billable model call for simultaneous misses. This local draft is not deployed.

### Seed a mock saved recipe without a model call

In a second terminal, point the seed command at the running private recipe store:

```bash
PYTHONPATH=.. RECIPE_STORE_URL=http://127.0.0.1:3028 .venv/bin/python -m backend.seed_saved_recipe
PYTHONPATH=.. .venv/bin/python -m backend.seed_saved_recipe --print-request |
  curl -sS -H 'Content-Type: application/json' -d @- http://127.0.0.1:8002/api/recipes
```

For Compose run `docker compose exec app python -m backend.seed_saved_recipe` instead. The sample is manual seed data and contains illustrative recipe estimates. The exact request above should return `"reused": true` even without a model key.

## Tests and review

From this directory, with dev dependencies installed:

```bash
(cd frontend && npm ci && npm test && npm run build)
(cd recipe && npm ci && npm test)
PYTHONPATH=.. .venv/bin/python -m unittest discover -s backend -t .
git diff --check
```

Use `RECIPE_TEST_DATABASE_URL` only with a disposable PostgreSQL database for the optional real SQL test. Tests cover multi-ingredient totals, profile validation, distinct recipe cache keys, fail-closed storage outage, Node persistence, and the browser API payload. An integration run against real PostgreSQL and a stub model verified: seed hit makes zero model calls; a miss calls the stub once; a repeated request and a Node restart reuse the same timestamp; a storage outage returns 503 without generating and does not break nutrition. No live model or Docker run was used for this verification. Before merging, verify the target checkout’s provider configuration and run its CI.
