import test from 'node:test';
import assert from 'node:assert/strict';
import { formatNutrient, generateRecipe, getApiInfo, getMealNutrition, getNutrition, listFoods, parseGrams } from './src/api.js';

const response = (data, status = 200) => new Response(JSON.stringify(data), { status });

test('search URL encodes queries and normalizes numeric ID', async () => {
  const signal = new AbortController().signal;
  const foods = await listFoods(' dry & cooked ', {
    signal,
    fetcher: async (url, options) => {
      assert.equal(new URL(url, 'http://local').searchParams.get('q'), 'dry & cooked');
      assert.equal(options.signal, signal);
      return response([{id:1,name:'Rice',preparation:'Dry',notes:'Long-grain'}]);
    },
  });
  assert.deepEqual(foods, [{id:'1',name:'Rice',preparation:'Dry',notes:'Long-grain'}]);
});

test('nutrition preserves both unavailable values and true zeros', async () => {
  const model = {id:1, grams:150, kcal:195, protein_g:0, carbs_g:42.3, fat_g:null};
  assert.deepEqual(await getNutrition('1', 150, {fetcher: async () => response(model)}), model);
  assert.equal(formatNutrient(null), 'Unavailable');
  assert.equal(formatNutrient(0), '0.0');
});

test('nutrition refuses incomplete or mismatched response data', async () => {
  const wrongId = {id:2, grams:150, kcal:195, protein_g:0, carbs_g:42.3, fat_g:null};
  await assert.rejects(getNutrition('1', 150, {fetcher: async () => response(wrongId)}), /invalid nutrition/i);
  const wrongServing = {...wrongId, id:1, grams:175};
  await assert.rejects(getNutrition('1', 150, {fetcher: async () => response(wrongServing)}), /invalid nutrition/i);
  const missingValue = {id:1, grams:150, kcal:195, protein_g:0, carbs_g:42.3};
  await assert.rejects(getNutrition('1', 150, {fetcher: async () => response(missingValue)}), /invalid nutrition/i);
});

test('API status is available for recoverable error UI', async () => {
  await assert.rejects(getNutrition('1', 150, {fetcher: async () => response({}, 404)}), {status:404});
  await assert.rejects(listFoods('', {fetcher: async () => response({}, 503)}), {status:503});
});

test('serving validation rejects non-integers and values outside bounds', () => {
  for (const bad of ['', '0', '-1', '12.5', '2e2', '2001', '10000']) assert.equal(parseGrams(bad), null);
  assert.equal(parseGrams('1'), 1);
  assert.equal(parseGrams('2000'), 2000);
});

test('only recognized API provenance can be advertised to the user', async () => {
  const info = {storage:'sqlite-fixtures', data:'Sample values'};
  assert.deepEqual(await getApiInfo({fetcher:async () => response(info)}), info);
  await assert.rejects(getApiInfo({fetcher:async () => response({storage:'unknown'})}), /invalid source/i);
});


test('meal nutrition sends every selected serving and keeps unavailable nutrients', async () => {
  const nutrition = {grams:225, kcal:142, protein_g:null, carbs_g:12, fat_g:0};
  const rows = [{food_id:'9', grams:175}, {food_id:10, grams:50}];
  assert.deepEqual(await getMealNutrition(rows, {fetcher: async (url, options) => {
    assert.equal(url, '/api/meals/nutrition');
    assert.equal(options.method, 'POST');
    assert.deepEqual(JSON.parse(options.body), {ingredients:[{food_id:9, grams:175}, {food_id:10, grams:50}]});
    return response(nutrition);
  }}), nutrition);
  await assert.rejects(getMealNutrition(rows, {fetcher:async () => response({...nutrition, grams:175})}), /invalid meal/i);
  await assert.rejects(getMealNutrition([]), /at least one/i);
});

test('recipe sends its profile, separate request and optional meal ingredients', async () => {
  const profile = {weight_value:70, weight_unit:'kg'};
  const recipe = {title:'Rice bowl', instructions:['Warm the rice.'], cooking_time:5, total_calories:207,
    macros:{protein:7,carbs:34,fats:1}, ingredients:[{name:'rice',amount:'100 g'}]};
  const generated = {recipe, created_at:'2026-11-20T00:00:00Z', reused:false};
  const rows = [{food_id:'9', grams:175}];
  assert.deepEqual(await generateRecipe(profile, ' rice bowl ', rows, {fetcher: async (url, options) => {
    assert.equal(url, '/api/recipes');
    assert.equal(options.method, 'POST');
    assert.deepEqual(JSON.parse(options.body), {profile, request:'rice bowl', ingredients:[{food_id:9, grams:175}]});
    return response(generated);
  }}), generated);
  await generateRecipe(profile, 'rice bowl', [], {fetcher: async (_url, options) => {
    assert.deepEqual(JSON.parse(options.body), {profile, request:'rice bowl'});
    return response({...generated, reused:true});
  }});
  await assert.rejects(generateRecipe(profile, 'bowl', rows, {fetcher:async () => response({}, 503)}), {status:503});
  await assert.rejects(generateRecipe(profile, 'bowl', rows, {fetcher:async () => response({...generated, reused:'yes'})}), /invalid recipe/i);
});
