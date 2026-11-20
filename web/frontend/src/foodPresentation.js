// Keep storage provenance out of the culinary subtitle without changing API records.
const storageLabels = /^(?:postgres(?:ql)?|demo|sqlite|sample|fixture)(?:\s+(?:catalog(?:ue)?|database|data|fixtures?))?$/i;

export function nutritionSubtitle(food) {
  if (!food) return '';
  const preparation = typeof food.preparation === 'string' ? food.preparation.trim() : '';
  const notes = typeof food.notes === 'string' ? food.notes.trim() : '';
  return [
    preparation && !/^unspecified$/i.test(preparation) ? preparation : '',
    notes && !storageLabels.test(notes) ? notes : '',
  ].filter(Boolean).join(' · ');
}
