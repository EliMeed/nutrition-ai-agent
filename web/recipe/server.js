import {createServer} from 'node:http';
import {pathToFileURL} from 'node:url';
import {RecipeRepository} from './repository.js';

const maxBody = 64 * 1024;
const pathPattern = /^\/v1\/recipes\/([a-f0-9]{64})$/;
class HttpError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = (value, limit) => typeof value === 'string' && value.trim().length > 0 && value.length <= limit;
const int = (value, min) => Number.isSafeInteger(value) && value >= min;
const list = (value, max, predicate) => Array.isArray(value) && value.length >= 1 && value.length <= max && value.every(predicate);

function validateRecipe(recipe) {
  return object(recipe) && Object.keys(recipe).length === 6 && text(recipe.title, 240) && int(recipe.total_calories, 1) && int(recipe.cooking_time, 0) &&
    object(recipe.macros) && Object.keys(recipe.macros).length === 3 && ['protein', 'carbs', 'fats'].every(field => int(recipe.macros[field], 0)) &&
    list(recipe.ingredients, 100, ingredient => object(ingredient) && Object.keys(ingredient).length === 2 && text(ingredient.name, 240) && text(ingredient.amount, 240)) &&
    list(recipe.instructions, 60, instruction => text(instruction, 1500));
}

function validateContext(context) {
  return object(context) && Object.keys(context).length === 4 &&
    context.schema_revision === 'recipe-reuse-v1' &&
    typeof context.request_sha256 === 'string' && /^[0-9a-f]{64}$/.test(context.request_sha256) &&
    Array.isArray(context.ingredients) && context.ingredients.length <= 20 &&
    context.ingredients.every(item => object(item) && Object.keys(item).length === 2 &&
      int(item.food_id, 1) && int(item.grams, 1) && item.grams <= 2000) &&
    Array.isArray(context.dietary_restrictions) && context.dietary_restrictions.length <= 20 &&
    context.dietary_restrictions.every(value => text(value, 120) && !/[\u0000-\u001f\u007f]/u.test(value));
}

async function input(req) {
  if (req.headers['content-type']?.split(';', 1)[0].trim().toLowerCase() !== 'application/json')
    throw new HttpError(415, 'Expected application/json.');
  if (Number(req.headers['content-length']) > maxBody) throw new HttpError(413, 'Request is too large.');
  let size = 0;
  const chunks = [];
  for await (const chunk of req.iterator({destroyOnReturn: false})) {
    size += chunk.length;
    if (size > maxBody) throw new HttpError(413, 'Request is too large.');
    chunks.push(chunk);
  }
  let payload;
  try { payload = JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch { throw new HttpError(400, 'Invalid JSON.'); }
  if (!validateRecipe(payload?.recipe) || !validateContext(payload?.context))
    throw new HttpError(422, 'Expected a complete recipe and a context object.');
  return payload;
}

function send(res, code, result) {
  res.writeHead(code, {'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store'});
  res.end(JSON.stringify(result));
}

export function makeServer({repository}) {
  return createServer({requestTimeout: 5000, headersTimeout: 5000, keepAliveTimeout: 2000}, async (req, res) => {
    try {
      if (req.url === '/health' && req.method === 'GET') {
        await repository.readiness();
        return send(res, 200, {status: 'ok'});
      }
      const match = pathPattern.exec(req.url);
      if (!match) throw new HttpError(404, 'Route not found.');
      const key = match[1];
      if (req.method === 'GET') {
        const row = await repository.get(key);
        if (!row) throw new HttpError(404, 'Recipe not found.');
        return send(res, 200, row);
      }
      if (req.method !== 'PUT') {
        res.setHeader('allow', 'GET, PUT');
        throw new HttpError(405, 'Method not allowed.');
      }
      const {recipe, context} = await input(req);
      const {created, row} = await repository.put(key, recipe, context);
      return send(res, created ? 201 : 200, row);
    } catch (err) {
      if (res.destroyed) return;
      if (err?.status === 413) res.setHeader('connection', 'close');
      return send(res, err instanceof HttpError ? err.status : 503, {
        error: err instanceof HttpError ? err.message : 'Recipe storage is unavailable.',
      });
    }
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const connectionString = process.env.RECIPE_DATABASE_URL;
  if (!connectionString) throw new Error('RECIPE_DATABASE_URL is required.');
  const {default: pg} = await import('pg');
  const pool = new pg.Pool({
    connectionString, max: 8, connectionTimeoutMillis: 1500, statement_timeout: 1500,
  });
  pool.on('error', () => console.error('An idle recipe database connection failed.'));
  const server = makeServer({repository: new RecipeRepository(pool)});
  server.listen(Number(process.env.PORT || '3000'), process.env.HOST || '0.0.0.0');
  for (const signal of ['SIGTERM', 'SIGINT'])
    process.once(signal, () => server.close(() => pool.end()));
}
