const options = {
  weight_unit: ['kg', 'lbs'],
  height_unit: ['cm', 'in', 'ft'],
  gender: ['male', 'female'],
  activity_level: ['sedentary', 'lightly_active', 'moderately_active', 'very_active'],
  goal: ['weight_loss', 'muscle_gain', 'maintenance'],
};
export const REQUEST_LIMIT = 500;

export function buildProfile(fields) {
  const profile = Object.fromEntries(Object.entries(options).map(([name, allowed]) => {
    const value = fields.get(name);
    if (!allowed.includes(value)) throw new Error('Please complete the profile fields.');
    return [name, value];
  }));
  const numeric = (name, min, max, integer = false) => {
    const string = String(fields.get(name) ?? '').trim();
    const number = Number(string);
    if (!string || !Number.isFinite(number) || number < min || number > max || (integer && !Number.isInteger(number))) {
      throw new Error('Please check your measurements, age and meals per day.');
    }
    return number;
  };
  profile.weight_value = numeric('weight_value', .1, Infinity);
  profile.height_value = numeric('height_value', .1, Infinity, profile.height_unit === 'ft');
  profile.height_inches_extra = profile.height_unit === 'ft' && fields.get('height_inches_extra')
    ? numeric('height_inches_extra', 0, 11, true) : 0;
  const kilograms = profile.weight_value * (profile.weight_unit === 'lbs' ? 0.45359237 : 1);
  const centimetres = profile.height_unit === 'ft' ? (profile.height_value * 12 + profile.height_inches_extra) * 2.54
    : profile.height_value * (profile.height_unit === 'in' ? 2.54 : 1);
  if (kilograms < 10 || kilograms > 500 || centimetres < 50 || centimetres > 300) {
    throw new Error('Please enter weight between 10 and 500 kg and height between 50 and 300 cm, or the equivalent.');
  }
  profile.age = numeric('age', 10, 120, true);
  profile.meals_per_day = numeric('meals_per_day', 1, 6, true);
  profile.dietary_restrictions = String(fields.get('dietary_restrictions') ?? '').split(',').map(value => value.trim()).filter(Boolean);
  if (profile.dietary_restrictions.length > 20 || profile.dietary_restrictions.some(value => value.length > 120)) {
    throw new Error('Enter up to 20 short dietary restrictions.');
  }
  return profile;
}
