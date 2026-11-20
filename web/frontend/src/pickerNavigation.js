export function moveOption(activeIndex, count, direction) {
  if (!Number.isInteger(count) || count < 1) return -1;
  if (activeIndex < 0 || activeIndex >= count) return direction > 0 ? 0 : count - 1;
  return Math.max(0, Math.min(count - 1, activeIndex + direction));
}

const words = value => (typeof value === 'string' ? value : '')
  .toLowerCase().normalize('NFKD').replace(/\p{M}/gu, '')
  .match(/[\p{L}\p{N}]+/gu) ?? [];

export function rankCandidates(candidates, query) {
  const tokens = words(query);
  if (tokens.length === 0) return candidates;
  const phrase = tokens.join(' ');
  const scored = candidates.map((food, index) => {
    const title = words(food.name);
    const titleText = title.join(' ');
    const labels = [...title, ...words(food.preparation), ...words(food.notes)];
    // Reorder the returned candidates only. Equal scores preserve server order.
    let score = 0;
    if (titleText === phrase) score = 5;
    else if (titleText.startsWith(phrase + ' ')) score = 4;
    else if (tokens.every(token => title.includes(token))) score = 3;
    else if (tokens.every(token => labels.includes(token))) score = 2;
    else if (tokens.every(token => labels.some(label => label.startsWith(token)))) score = 1;
    return {food, index, score};
  });
  return scored.sort((a, b) => b.score - a.score || a.index - b.index).map(entry => entry.food);
}
