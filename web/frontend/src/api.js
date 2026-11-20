const nullableNumber = value => value === null || (typeof value === 'number' && Number.isFinite(value));
export const macroFields = ['protein_g', 'carbs_g', 'fat_g'];

async function getJson(url, { signal, fetcher = globalThis.fetch } = {}) {
  const response = await fetcher(url, { signal, headers: { Accept: 'application/json' } });
  if (!response.ok) {
    const error = new Error(`Request failed (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

export async function listFoods(query, options) {
  const data = await getJson(`/api/foods?${new URLSearchParams({ q: query.trim() })}`, options);
  const rows = Array.isArray(data) ? data : data?.foods;
  if (!Array.isArray(rows)) throw new Error('Invalid food response.');
  return rows.map(row => {
    if (!row || !['number','string'].includes(typeof row.id) || typeof row.name !== 'string') {
      throw new Error('Invalid food record.');
    }
    return {
      id: String(row.id),
      name: row.name,
      preparation: row.preparation ?? '',
      notes: row.notes ?? '',
    };
  });
}

export async function getNutrition(id, grams, options) {
  const data = await getJson(`/api/foods/${encodeURIComponent(id)}/nutrition?${new URLSearchParams({ grams })}`, options);
  if (!data || String(data.id ?? data.food_id) !== String(id) || Number(data.grams) !== Number(grams)
      || !['kcal', ...macroFields].every(key => nullableNumber(data[key]))) {
    throw new Error('Invalid nutrition response.');
  }
  return data;
}

export function parseGrams(value) {
  if (!/^\d{1,4}$/.test(value)) return null;
  const grams = Number(value);
  return grams >= 1 && grams <= 2000 ? grams : null;
}

export function formatNutrient(value, decimals = 1) {
  return value == null ? 'Unavailable' : Number(value).toFixed(decimals);
}

export async function getApiInfo(options) {
  const data = await getJson('/api/info', options);
  if (!data || !['sqlite-fixtures', 'postgresql'].includes(data.storage)) {
    throw new Error('Invalid source metadata.');
  }
  return data;
}


export const MAX_MEAL_INGREDIENTS = 12;

export function ingredientPayload(rows) {
  if (!Array.isArray(rows) || rows.length > MAX_MEAL_INGREDIENTS) throw new Error('Invalid ingredient list.');
  return rows.map(row => {
    const food_id = Number(row.food_id ?? row.id);
    const grams = parseGrams(String(row.grams));
    if (!Number.isSafeInteger(food_id) || food_id < 1 || grams === null) {
      throw new Error('Choose a food and an amount between 1 and 2,000 grams.');
    }
    return { food_id, grams };
  });
}

async function sendJson(url, body, { signal, fetcher = globalThis.fetch } = {}) {
  const response = await fetcher(url, {
    method: 'POST', signal,
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = new Error(`Request failed (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

export async function getMealNutrition(rows, options) {
  const ingredients = ingredientPayload(rows);
  if (!ingredients.length) throw new Error('Add at least one ingredient.');
  const data = await sendJson('/api/meals/nutrition', { ingredients }, options);
  if (!data || data.grams !== ingredients.reduce((sum, item) => sum + item.grams, 0)
      || !['kcal', ...macroFields].every(key => nullableNumber(data[key]))) {
    throw new Error('Invalid meal nutrition response.');
  }
  return data;
}

const nonemptyText = value => typeof value === 'string' && Boolean(value.trim());
const validCount = value => Number.isInteger(value) && value >= 0;
export async function generateRecipe(profile, request, rows = [], options) {
  if (!profile || !nonemptyText(request)) throw new Error('Enter a profile and a recipe request.');
  const ingredients = ingredientPayload(rows);
  const data = await sendJson('/api/recipes', { profile, request: request.trim(), ...(ingredients.length && { ingredients }) }, options);
  const recipe = data?.recipe;
  if (!recipe || !nonemptyText(recipe.title)
      || !validCount(recipe.total_calories) || recipe.total_calories === 0 || !validCount(recipe.cooking_time)
      || !['protein', 'carbs', 'fats'].every(key => validCount(recipe.macros?.[key]))
      || !Array.isArray(recipe.ingredients) || !recipe.ingredients.every(row => nonemptyText(row?.name) && nonemptyText(row?.amount))
      || !Array.isArray(recipe.instructions) || !recipe.instructions.every(nonemptyText)
      || !nonemptyText(data.created_at) || !Number.isFinite(Date.parse(data.created_at)) || typeof data.reused !== 'boolean') {
    throw new Error('Invalid recipe response.');
  }
  return data;
}
