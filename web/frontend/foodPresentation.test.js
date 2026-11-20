import test from 'node:test';
import assert from 'node:assert/strict';
import { nutritionSubtitle } from './src/foodPresentation.js';

test('food subtitle keeps useful culinary notes, not storage labels', () => {
  assert.equal(nutritionSubtitle({preparation:'Cooked', notes:'Long-grain, plain'}), 'Cooked · Long-grain, plain');
  assert.equal(nutritionSubtitle({preparation:'Cooked', notes:' PostgreSQL catalogue '}), 'Cooked');
  assert.equal(nutritionSubtitle({preparation:'Unspecified', notes:'Demo catalogue'}), '');
});
