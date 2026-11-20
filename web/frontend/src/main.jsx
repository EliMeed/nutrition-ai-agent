import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { RecipePanel } from './RecipePanel.jsx';
import { IngredientPicker } from './IngredientPicker.jsx';
import { MealNutrition, NutritionNumbers } from './MealNutrition.jsx';
import { nutritionSubtitle } from './foodPresentation.js';
import { getMealNutrition, getNutrition, listFoods, MAX_MEAL_INGREDIENTS, parseGrams } from './api.js';
import './style.css';
import logo from './assets/macrochef-logo.svg';

function NutritionReadout({ food, state }) {
  const data = state.data;
  const subtitle = nutritionSubtitle(food);
  return (
    <div className="nutrition">
      <h2 id="nutrition-title">{food?.name ?? 'Nutrition'}
        {subtitle && <span>{subtitle}</span>}
      </h2>
      {data ? <NutritionNumbers data={data}/>  : <p className="nutrition-message" role={state.status === 'error' ? 'alert' : 'status'}>
        {state.status === 'pending' ? 'Calculating nutrition…'
          : state.status === 'error' ? (state.error?.status === 404 ? 'This food has no available nutrition record.' : 'Nutrition couldn’t be loaded. Your serving size is unchanged.')
          : food ? 'Enter a valid serving size to calculate nutrition.' : 'Choose an ingredient to see nutrition.'}</p>}
      {data && <div role="status" className="sr-only">Nutrition updated for {data.grams} grams.</div>}
    </div>
  );
}

function PortionInput({ grams, setGrams, valid }) {
  const parsed = parseGrams(grams);
  const step = delta => setGrams(String(Math.min(2000, Math.max(1, parsed + delta))));
  return (
    <div className="portion">
      <label htmlFor="grams">Serving size</label>
      <div className="stepper">
        <button type="button" aria-label="Subtract 25 grams" disabled={!valid || parsed <= 1} onClick={() => step(-25)}>−</button>
        <div className="grams">
          <input id="grams" inputMode="numeric" maxLength={4} value={grams} onChange={e => setGrams(e.target.value)}
            aria-invalid={!valid || undefined} aria-describedby={!valid ? 'grams-error' : 'grams-unit'}/>
          <span id="grams-unit" aria-label="grams">g</span>
        </div>
        <button type="button" aria-label="Add 25 grams" disabled={!valid || parsed >= 2000} onClick={() => step(25)}>+</button>
      </div>
      {!valid && <p id="grams-error" className="error">Enter a whole number from 1 to 2,000 grams.</p>}
    </div>
  );
}

const PENDING = { status: 'pending' };
const IDLE = { status: 'idle' };

// A request key ties visible data to the current user inputs. Cleanup aborts
// network work on superseded queries without clearing the serving or selection.
function useRequest(key, load, delay = 0) {
  const [snapshot, setSnapshot] = useState(null);
  useEffect(() => {
    if (!key) return undefined;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const data = await load(controller.signal);
        if (!controller.signal.aborted) setSnapshot({ key, status: 'success', data });
      } catch (error) {
        if (!controller.signal.aborted) setSnapshot({ key, status: 'error', error });
      }
    }, delay);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [key, delay]); // load closes over precisely the inputs encoded in the key.
  if (!key) return IDLE;
  return snapshot?.key === key ? snapshot : PENDING;
}

function App() {
  const [query, setQuery] = useState('');
  const [view, setView] = useState('nutrition');
  const [selected, setSelected] = useState(null);
  const [ingredients, setIngredients] = useState([]);
  const [mealAttempt, setMealAttempt] = useState(0);
  const [mealUpdate, setMealUpdate] = useState('');
  const nextPortionKey = useRef(0);
  const [grams, setGrams] = useState('150');
  const [searchAttempt, setSearchAttempt] = useState(0);
  const [nutritionAttempt, setNutritionAttempt] = useState(0);
  const normalized = query.trim();
  const foodState = useRequest(
    normalized ? JSON.stringify([normalized, searchAttempt]) : null,
    signal => listFoods(normalized, { signal }),
    160,
  );
  const food = selected;
  const numericGrams = parseGrams(grams);
  const nutritionKey = food && numericGrams !== null
    ? JSON.stringify([food.id, numericGrams, nutritionAttempt]) : null;
  const nutritionState = useRequest(nutritionKey,
    signal => getNutrition(food.id, numericGrams, { signal }), 120);
  const busy = nutritionState.status === 'pending';
  const portions = ingredients.map(({ food, grams: amount }) => ({ food_id: food.id, grams: amount }));
  const mealKey = portions.length ? JSON.stringify([portions, mealAttempt]) : null;
  const mealState = useRequest(mealKey, signal => getMealNutrition(portions, {signal}));
  const existingWeight = ingredients.filter(row => row.food.id === food?.id).reduce((sum, row) => sum + row.grams, 0);
  const overIngredientLimit = numericGrams !== null && existingWeight + numericGrams > 2000;
  const canAdd = food && numericGrams !== null && !overIngredientLimit && ingredients.length < MAX_MEAL_INGREDIENTS;

  function addPortion() {
    if (!canAdd) return;
    const next = { key: ++nextPortionKey.current, food, grams: numericGrams };
    setIngredients(items => items.length >= MAX_MEAL_INGREDIENTS ? items : [...items, next]);
    setMealUpdate(`Added ${numericGrams} grams of ${food.name} to the meal.`);
  }
  function removePortion(key) {
    setIngredients(items => items.filter(item => item.key !== key));
    setMealUpdate('Ingredient removed from the meal.');
  }


  return (
    <main className="studio">
      <header className="masthead">
        <div className="brand"><img className="brand-logo" src={logo} alt="MacroChef" width="161" height="31" /></div>
      </header>
      <div className="intro">
        <h1>Build a serving.</h1>
        <p>Look up an ingredient and calculate its nutrition by weight.</p>
      </div>
      <div className="workbench">
        <IngredientPicker query={query} setQuery={setQuery}
          selection={food} onSelect={setSelected} foodState={foodState} onRetry={() => setSearchAttempt(value => value + 1)} />
        <div className="view-area">
          <div className="view-switch" role="group" aria-label="Studio view">
            <button type="button" aria-pressed={view === 'nutrition'} aria-controls="nutrition-view"
              onClick={() => setView('nutrition')}>Nutrition</button>
            <button type="button" aria-pressed={view === 'meal'} aria-controls="meal-view"
              onClick={() => setView('meal')}>Make a meal</button>
          </div>
          <section id="nutrition-view" className="panel readout nutrition-view" aria-labelledby="nutrition-title"
            hidden={view !== 'nutrition'}>
            <NutritionReadout food={food} state={nutritionState} />
            {food && <PortionInput {...{ grams, setGrams }} valid={numericGrams !== null} />}
            {nutritionKey && <div className="nutrition-actions">
              <button className="quiet-action" type="button" aria-disabled={busy || undefined}
                onClick={() => { if (!busy) setNutritionAttempt(value => value + 1); }}>
                {busy ? 'Calculating…' : nutritionState.status === 'error' ? 'Retry nutrition' : 'Refresh nutrition'}
              </button>
            </div>}
            {food && <div className="meal-add">
              <button className="simple-button" type="button" disabled={!canAdd} onClick={addPortion}>Add serving to meal</button>
              {ingredients.length >= MAX_MEAL_INGREDIENTS && <small>Remove a serving to add another.</small>}
              {overIngredientLimit && <small>The meal can include up to 2,000 g of the same food.</small>}
              <p className="sr-only" role="status">{mealUpdate}</p>
            </div>}
            <MealNutrition rows={ingredients} state={mealState} onRemove={removePortion}
              onRetry={() => setMealAttempt(value => value + 1)}/>
          </section>
          <div id="meal-view" className="panel meal-view" hidden={view !== 'meal'}>
            <RecipePanel ingredients={ingredients}/>
          </div>
        </div>
      </div>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
