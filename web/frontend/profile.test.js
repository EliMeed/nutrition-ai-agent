import assert from 'node:assert/strict';
import test from 'node:test';
import { buildProfile } from './src/profile.js';

const fixture = {weight_value:180, weight_unit:'lbs', height_value:5, height_unit:'ft', height_inches_extra:10,
  age:30, gender:'male', activity_level:'very_active', goal:'maintenance', meals_per_day:3, dietary_restrictions:' , vegetarian, dairy-free '};
const form = overrides => new Map(Object.entries({...fixture, ...overrides}).map(([key,value]) => [key,String(value)]));

test('profile uses original units and enum values, and normalizes restriction fields', () => {
  assert.deepEqual(buildProfile(form()), {...fixture,dietary_restrictions:['vegetarian','dairy-free']});
  assert.equal(buildProfile(form({height_value:180, height_unit:'cm'})).height_inches_extra, 0);
});

test('profile rejects missing, unrecognized or out-of-range fields', () => {
  assert.throws(() => buildProfile(form({gender:''})), /complete the profile/i);
  assert.throws(() => buildProfile(form({weight_value:9,weight_unit:'kg'})), /10 and 500 kg/i);
  assert.throws(() => buildProfile(form({meals_per_day:7})), /meals per day/i);
});
