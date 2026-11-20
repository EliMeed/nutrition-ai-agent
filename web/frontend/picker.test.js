import test from 'node:test';
import assert from 'node:assert/strict';
import { moveOption, rankCandidates } from './src/pickerNavigation.js';

test('the first directional key enters a result list at the expected edge', () => {
  assert.equal(moveOption(-1, 60, 1), 0);
  assert.equal(moveOption(-1, 60, -1), 59);
  assert.equal(moveOption(-1, 0, 1), -1);
});

test('move through many results without allowing an invalid index', () => {
  let active = -1;
  for (let presses = 0; presses < 75; presses++) active = moveOption(active, 60, 1);
  assert.equal(active, 59);
  for (let presses = 0; presses < 75; presses++) active = moveOption(active, 60, -1);
  assert.equal(active, 0);
});

test('ranking is restricted to returned candidates and preserves server order for ties', () => {
  const foods = [
    { id:1, name:'Cream of chicken soup' },
    { id:2, name:'Chicken thigh' },
    { id:3, name:'Chicken breast' },
    { id:4, name:'Chicken' },
    { id:5, name:'Chickenless protein' },
  ];
  assert.deepEqual(rankCandidates(foods, 'CHICKEN').map(food => food.id), [4, 2, 3, 1, 5]);
  assert.deepEqual(foods.map(food => food.id), [1,2,3,4,5]);
});
