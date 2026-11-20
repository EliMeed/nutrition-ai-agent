import assert from 'node:assert/strict';
import {once} from 'node:events';
import {test} from 'node:test';
import {readFile} from 'node:fs/promises';
import {makeServer} from './server.js';
import {RecipeRepository} from './repository.js';

const key = 'a'.repeat(64);
const recipe = {title:'Lemon rice',total_calories:250,cooking_time:15,
  macros:{protein:5,carbs:42,fats:7},ingredients:[{name:'White rice',amount:'150 g'}],
  instructions:['Cook the rice.','Add lemon and serve.']};
const context = {schema_revision:'recipe-reuse-v1',request_sha256:'c'.repeat(64),
  ingredients:[{food_id:1,grams:150}],dietary_restrictions:['vegetarian']};

async function start(t, repository) {
  const server = makeServer({repository});
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => new Promise(resolve => server.close(resolve)));
  const base = `http://127.0.0.1:${server.address().port}`;
  return (path, method, body) => fetch(base + path, {
    method, headers: {'content-type':'application/json'}, body: JSON.stringify(body),
  });
}

test('HTTP contract executes repository SQL, first write wins and read never leaks context', async t => {
  const rows = new Map();
  const pool = {query: async (sql, params) => {
    if (sql.includes('LIMIT 0')) return {rows:[]};
    if (sql.startsWith('INSERT')) {
      assert.match(sql, /ON CONFLICT \(key\) DO NOTHING/);
      assert.match(sql, /VALUES \(\$1, \$2::jsonb, \$3::jsonb\)/);
      const [value, json, metadata] = params;
      assert.deepEqual(JSON.parse(metadata), context);
      if (rows.has(value)) return {rows:[]};
      const row = {recipe: JSON.parse(json),created_at:'2026-11-20T00:00:00.000Z'};
      rows.set(value, row);
      return {rows:[row]};
    }
    assert.match(sql, /SELECT recipe, created_at FROM public\.recipe_cache WHERE key = \$1/);
    return {rows: rows.has(params[0]) ? [rows.get(params[0])] : []};
  }};
  const request = await start(t, new RecipeRepository(pool));
  const path = '/v1/recipes/' + key;
  assert.equal((await request('/health')).status, 200);
  assert.equal((await request(path)).status, 404);
  assert.equal((await request(path, 'PUT', {recipe,context:{...context,profile:'private'}})).status, 422);
  assert.equal((await request(path, 'PUT', {recipe,context:{...context,request_sha256:'not a hash'}})).status, 422);
  assert.equal((await request(path, 'PUT', {recipe:{...recipe,total_calories:0},context})).status, 422);
  const responses = await Promise.all([request(path,'PUT',{recipe,context}),
    request(path,'PUT',{recipe:{...recipe,title:'Second write'},context})]);
  assert.deepEqual(responses.map(response => response.status).sort(), [200,201]);
  const bodies = await Promise.all(responses.map(response => response.json()));
  assert.deepEqual(bodies[0], bodies[1]);
  assert.deepEqual(Object.keys(bodies[0]).sort(), ['created_at','recipe']);
  assert.deepEqual(await (await request(path)).json(), bodies[0]);
  assert.equal((await request('/v1/recipes/' + key.toUpperCase())).status, 404);
});

test('profile-target recipes can use no selected foods', async t => {
  const request = await start(t, {
    put: async (_key, value, metadata) => {
      assert.deepEqual(metadata.ingredients, []);
      return {created:true,row:{recipe:value,created_at:'2026-11-20T00:00:00.000Z'}};
    },
  });
  const response = await request('/v1/recipes/' + key,'PUT',{recipe,context:{...context,ingredients:[]}});
  assert.equal(response.status, 201);
});

test('failed readiness and queries return sanitized 503', async t => {
  const request = await start(t, new RecipeRepository({query: async () => {throw new Error('private detail');}}));
  for (const path of ['/health', '/v1/recipes/' + key]) {
    const response = await request(path);
    assert.equal(response.status, 503);
    assert.deepEqual(await response.json(), {error:'Recipe storage is unavailable.'});
  }
});

test('real PostgreSQL persists one winning write and returns it after reconnect', {
  skip: !process.env.RECIPE_TEST_DATABASE_URL,
}, async () => {
  const {default: pg} = await import('pg');
  const {randomBytes} = await import('node:crypto');
  const connectionString = process.env.RECIPE_TEST_DATABASE_URL;
  const firstPool = new pg.Pool({connectionString});
  const unique = randomBytes(32).toString('hex');
  const uniqueContext = {...context,request_sha256:unique};
  let winner;
  try {
    await firstPool.query(await readFile(new URL('./schema.sql',import.meta.url),'utf8'));
    const repo = new RecipeRepository(firstPool);
    await repo.readiness();
    assert.equal(await repo.get(unique), null);
    const writes = await Promise.all([repo.put(unique,recipe,uniqueContext),
      repo.put(unique,{...recipe,title:'Concurrent contender'},uniqueContext)]);
    assert.equal(writes.filter(write => write.created).length, 1);
    assert.deepEqual(writes[0].row, writes[1].row);
    winner = writes[0].row;
  } finally {
    await firstPool.end();
  }
  const secondPool = new pg.Pool({connectionString});
  try {
    assert.deepEqual(await new RecipeRepository(secondPool).get(unique), winner);
  } finally {
    await secondPool.query('DELETE FROM public.recipe_cache WHERE key = $1',[unique]);
    await secondPool.end();
  }
});
