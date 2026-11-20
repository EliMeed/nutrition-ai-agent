import React, { useEffect, useRef, useState } from 'react';
import { generateRecipe } from './api.js';
import { GlassButton } from './GlassButton.jsx';
import { buildProfile, REQUEST_LIMIT } from './profile.js';

const activities = [
  ['sedentary', 'Sedentary'], ['lightly_active', 'Lightly active'],
  ['moderately_active', 'Moderately active'], ['very_active', 'Very active'],
];
const goals = [
  ['maintenance', 'Maintain weight'], ['muscle_gain', 'Build muscle'], ['weight_loss', 'Lose weight'],
];

function RecipeFields({ heightUnit, setHeightUnit }) {
  return <>
    <fieldset className="profile-fields">
      <legend>Nutrition profile</legend>
      <div className="profile-grid">
        <div className="profile-field">
          <label htmlFor="profile-weight">Weight</label>
          <div className="profile-units">
            <input id="profile-weight" name="weight_value" type="number" min=".1" step="any" required/>
            <select name="weight_unit" aria-label="Weight unit">
              <option value="kg">kg</option><option value="lbs">lb</option>
            </select>
          </div>
        </div>
        <div className="profile-field">
          <label htmlFor="profile-height">Height</label>
          <div className="profile-units">
            <input id="profile-height" name="height_value" type="number" min={heightUnit === 'ft' ? 1 : '.1'}
              step={heightUnit === 'ft' ? 1 : 'any'} required/>
            <select name="height_unit" aria-label="Height unit" value={heightUnit} onChange={e => setHeightUnit(e.target.value)}>
              <option value="cm">cm</option><option value="in">in</option><option value="ft">ft</option>
            </select>
          </div>
        </div>
        {heightUnit === 'ft' && <label className="profile-field">
          Additional inches <input name="height_inches_extra" type="number" min="0" max="11" step="1" placeholder="0"/>
        </label>}
        <label className="profile-field">Age <input name="age" type="number" min="10" max="120" step="1" required/></label>
        <label className="profile-field">Sex for calculation
          <select name="gender" defaultValue="" required>
            <option value="" disabled>Select</option><option value="female">Female</option><option value="male">Male</option>
          </select>
        </label>
        <label className="profile-field">Activity
          <select name="activity_level" defaultValue="" required>
            <option value="" disabled>Select</option>{activities.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
          </select>
        </label>
        <label className="profile-field">Goal
          <select name="goal" defaultValue="" required>
            <option value="" disabled>Select</option>{goals.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
          </select>
        </label>
        <label className="profile-field">Meals per day
          <input name="meals_per_day" type="number" min="1" max="6" step="1" defaultValue="3" required/>
        </label>
        <label className="profile-field profile-full">Dietary restrictions <small>Optional, separate with commas.</small>
          <input name="dietary_restrictions" type="text" placeholder="e.g. vegetarian, dairy-free" maxLength={240}/>
        </label>
      </div>
    </fieldset>
    <label className="profile-field request-field">What would you like to make?
      <textarea name="recipe_request" rows={3} maxLength={REQUEST_LIMIT}
        placeholder="e.g. A quick rice bowl with something crunchy" required/>
    </label>
  </>;
}

function RecipeResult({ data, changed }) {
  const { recipe, reused } = data;
  return <article className="recipe-result" aria-labelledby="recipe-result-title">
    <div className="section-index">{reused ? 'SAVED RECIPE' : 'GENERATED RECIPE'}</div>
    <h4 id="recipe-result-title">{recipe.title}</h4>
    {changed && <p className="recipe-stale">This recipe reflects your previous request. Generate again to use your changes.</p>}
    <p className="recipe-serving"><strong>{recipe.cooking_time} min</strong> · Estimated recipe nutrition</p>
    <dl className="recipe-macros">
      <div><dt>Energy</dt><dd>{recipe.total_calories} <small>kcal</small></dd></div>
      <div><dt>Protein</dt><dd>{recipe.macros.protein} <small>g</small></dd></div>
      <div><dt>Carbs</dt><dd>{recipe.macros.carbs} <small>g</small></dd></div>
      <div><dt>Fat</dt><dd>{recipe.macros.fats} <small>g</small></dd></div>
    </dl>
    <p id="recipe-ingredients-title" className="recipe-instructions-heading">Ingredients</p>
    <ul className="recipe-items" aria-labelledby="recipe-ingredients-title">
      {recipe.ingredients.map(({ name, amount }, index) => <li key={index}>{amount} · {name}</li>)}
    </ul>
    <p id="recipe-instructions" className="recipe-instructions-heading">Instructions</p>
    <ol aria-labelledby="recipe-instructions">
      {recipe.instructions.map((step, index) => <li key={index}>{step}</li>)}
    </ol>
  </article>;
}

export function RecipePanel({ ingredients }) {
  const [state, setState] = useState({ status: 'idle' });
  const [heightUnit, setHeightUnit] = useState('cm');
  const [changed, setChanged] = useState(false);
  const request = useRef(null);
  const busy = state.status === 'pending';
  const failed = state.status === 'error' || state.status === 'unavailable';
  const mealKey = JSON.stringify(ingredients.map(({ food, grams }) => [food.id, grams]));
  useEffect(() => () => request.current?.abort(), []);

  async function requestRecipe(event) {
    event.preventDefault();
    if (request.current) return;
    const fields = new FormData(event.currentTarget);
    let profile, goal;
    try {
      profile = buildProfile(fields);
      goal = String(fields.get('recipe_request') ?? '').trim();
      if (!goal) throw new Error('Describe what you would like to make.');
    } catch (error) {
      setState({ status: 'error', message: error.message });
      return;
    }
    const controller = new AbortController();
    request.current = controller;
    const rows = ingredients.map(({ food, grams }) => ({ food_id: food.id, grams }));
    setChanged(false);
    setState({ status: 'pending' });
    try {
      const data = await generateRecipe(profile, goal, rows, { signal: controller.signal });
      if (!controller.signal.aborted) setState({ status: 'success', data, mealKey });
    } catch (error) {
      if (!controller.signal.aborted) setState({ status: [502, 503, 504].includes(error?.status)
        ? 'unavailable' : 'error', message: error?.status === 422 ? 'Check your profile and request, then try again.' : undefined });
    } finally {
      if (request.current === controller) request.current = null;
    }
  }

  return (
    <section className="recipe profile-recipe" aria-labelledby="recipe-title">
      <h2 id="recipe-title">Make it a meal.</h2>
      <p className="recipe-intro">Use your profile and a request to get a recipe idea. Recipe nutrition is an estimate.</p>
      <form className="recipe-form" autoComplete="off" onChange={() => setChanged(true)} onSubmit={requestRecipe}>
        <RecipeFields {...{heightUnit, setHeightUnit}}/>
        {ingredients.length > 0 && <p className="meal-selection">
          {ingredients.length} {ingredients.length === 1 ? 'serving' : 'servings'} from your meal will be included in the request.
        </p>}
        <div className="recipe-action action-zone">
          <div className="action-backdrop" aria-hidden="true"/>
          <GlassButton type="submit" pending={busy}>
            {busy ? 'Generating…' : failed ? 'Retry recipe' : 'Generate recipe'}
          </GlassButton>
        </div>
      </form>
      <section className="recipe-output" aria-labelledby="recipe-output-title">
        <h3 id="recipe-output-title">Recipe idea</h3>
        <p className={state.status === 'success' ? 'sr-only' : 'recipe-output-status'} role="status" aria-atomic="true">
          {state.status === 'idle' ? 'Your recipe will appear here.'
            : busy ? 'Generating a recipe idea…'
            : state.status === 'success' ? 'Recipe idea ready.' : ''}
        </p>
        {failed && <p className="recipe-error error" role="alert">
          {state.message ?? (state.status === 'unavailable' ? 'Recipe generation is temporarily unavailable. Try again in a moment.'
            : 'Couldn’t generate that recipe. Try again. Your profile and request were kept.')}
        </p>}
        {state.status === 'success' && <RecipeResult data={state.data} changed={changed || state.mealKey !== mealKey}/>}
      </section>
    </section>
  );
}
