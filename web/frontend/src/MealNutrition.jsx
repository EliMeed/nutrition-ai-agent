import React from 'react';
import { formatNutrient, macroFields } from './api.js';

export function NutritionNumbers({ data }) {
  return <div className="numbers">
    <div className="energy" data-unavailable={data.kcal == null || undefined}>
      {formatNutrient(data.kcal, 0)} {data.kcal != null && <span>kcal</span>}
    </div>
    <dl>{['Protein','Carbs','Fat'].map((name, i) => {
      const value = data[macroFields[i]];
      return <div key={name}>
        <dt>{name}</dt>
        <dd data-unavailable={value == null || undefined}>
          {formatNutrient(value)}{value != null && <small> g</small>}
        </dd>
      </div>;
    })}</dl>
  </div>;
}

export function MealNutrition({ rows, state, onRemove, onRetry }) {
  return <section aria-labelledby="meal-totals-heading" className="meal-totals">
    <h2 id="meal-totals-heading">Meal nutrition</h2>
    {rows.length === 0 ? <p className="recipe-intro">Add foods to see their combined nutrition.</p> : <>
      <ul className="meal-ingredient-list">
        {rows.map(({ key, food, grams }) => <li key={key}>
          <span>{food.name}{food.preparation && food.preparation !== 'Unspecified' && <small> · {food.preparation}</small>}</span>
          <span className="meal-ingredient-weight">{grams} g</span>
          <button className="quiet-action" type="button" onClick={() => onRemove(key)}
            aria-label={`Remove ${grams} grams of ${food.name} from meal`}>Remove</button>
        </li>)}
      </ul>
      {state.status === 'pending' && <p className="recipe-intro" role="status">Calculating meal nutrition…</p>}
      {state.status === 'error' && <div>
        <p className="error" role="alert">Meal nutrition couldn’t be calculated. Your foods were kept.</p>
        <button className="quiet-action" type="button" onClick={onRetry}>Retry meal nutrition</button>
      </div>}
      {state.data && <>
        <p role="status" className="recipe-intro">Combined nutrition for {state.data.grams} g</p>
        <NutritionNumbers data={state.data}/>
      </>}
    </>}
  </section>;
}
