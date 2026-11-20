CREATE TABLE IF NOT EXISTS public.recipe_cache (
    key text PRIMARY KEY CHECK (key ~ '^[0-9a-f]{64}$'),
    recipe jsonb NOT NULL CHECK (jsonb_typeof(recipe) = 'object'),
    context jsonb NOT NULL CHECK (jsonb_typeof(context) = 'object'),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
