export class RecipeRepository {
  constructor(pool) { this.pool = pool; }

  async readiness() {
    await this.pool.query('SELECT key FROM public.recipe_cache LIMIT 0');
  }

  async get(key) {
    const {rows} = await this.pool.query(
      'SELECT recipe, created_at FROM public.recipe_cache WHERE key = $1', [key],
    );
    return rows[0] ?? null;
  }

  async put(key, recipe, context) {
    const {rows} = await this.pool.query(
      `INSERT INTO public.recipe_cache (key, recipe, context)
       VALUES ($1, $2::jsonb, $3::jsonb)
       ON CONFLICT (key) DO NOTHING
       RETURNING recipe, created_at`, [key, JSON.stringify(recipe), JSON.stringify(context)],
    );
    if (rows.length) return {created: true, row: rows[0]};
    // At READ COMMITTED, this separate statement sees the committed winner.
    // No delete endpoint exists, so a winning row cannot vanish in normal usage.
    const row = await this.get(key);
    if (!row) throw new Error('Recipe cache winner missing');
    return {created: false, row};
  }
}
