import React, { useEffect, useId, useMemo, useRef, useState } from 'react';
import { moveOption, rankCandidates } from './pickerNavigation.js';

const DISPLAY_LIMIT = 6;

export function IngredientPicker({ query, setQuery, selection, onSelect, foodState, onRetry }) {
  const candidates = useMemo(() => rankCandidates(foodState.data ?? [], query), [foodState.data, query]);
  const rows = candidates.slice(0, DISPLAY_LIMIT);
  const truncated = candidates.length > DISPLAY_LIMIT;
  const [open, setOpen] = useState(false);
  const [activeId, setActiveId] = useState(null);
  const listId = useId();
  const listRef = useRef(null);
  const inputRef = useRef(null);
  const expanded = open && rows.length > 0;
  const activeIndex = expanded ? rows.findIndex(row => row.id === activeId) : -1;
  const optionId = index => `${listId}-option-${index}`;

  useEffect(() => {
    const list = listRef.current;
    const current = activeIndex >= 0 && list?.children[activeIndex];
    if (!current) return;
    const top = current.offsetTop;
    const bottom = top + current.offsetHeight;
    if (top < list.scrollTop) list.scrollTop = top;
    else if (bottom > list.scrollTop + list.clientHeight) list.scrollTop = bottom - list.clientHeight;
  }, [activeIndex]);

  function dismiss() {
    setOpen(false);
    setActiveId(null);
  }

  function select(food) {
    onSelect(food);
    dismiss();
  }

  function onKeyDown(event) {
    if (event.nativeEvent.isComposing) return;
    switch (event.key) {
      case 'ArrowDown':
      case 'ArrowUp': {
        if (!rows.length) return;
        event.preventDefault();
        setOpen(true);
        const index = moveOption(activeIndex, rows.length, event.key === 'ArrowDown' ? 1 : -1);
        setActiveId(rows[index].id);
        break;
      }
      case 'Enter':
        if (!expanded) return;
        event.preventDefault();
        if (activeIndex >= 0) select(rows[activeIndex]);
        break;
      case 'Escape':
        if (!expanded) return;
        event.preventDefault();
        dismiss();
        break;
    }
  }

  return (
    <section className="panel picker" aria-labelledby="ingredient-title">
      <h2 id="ingredient-title">Search foods</h2>
      <div className="picker-anchor">
        <div className="search">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M16.5 16.5 21 21M18 10.5a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z"/>
          </svg>
          <input ref={inputRef} type="search" role="combobox" aria-autocomplete="list"
            aria-expanded={expanded} aria-controls={expanded ? listId : undefined}
            aria-activedescendant={activeIndex >= 0 ? optionId(activeIndex) : undefined}
            aria-label="Search ingredients" placeholder="Search by food name" autoComplete="off"
            value={query} onFocus={() => setOpen(true)} onClick={() => setOpen(true)}
            onBlur={dismiss} onKeyDown={onKeyDown} onChange={event => {
              setActiveId(null);
              setOpen(true);
              setQuery(event.target.value);
            }}/>
        </div>
        <div role="status" className="picker-status">
          {foodState.status === 'pending' ? 'Searching ingredients…'
            : foodState.status === 'success' ? (truncated ? 'Top 6. Narrow by cut or preparation.'
              : rows.length ? `${rows.length} matching foods shown.` : 'No matching foods.')
            : foodState.status === 'idle' ? 'Type a food name to begin.' : ''}
        </div>
        {expanded && <ul id={listId} ref={listRef} className="picker-popup" role="listbox"
          aria-label="Matching foods">
          {rows.map((food, index) => <li key={food.id} id={optionId(index)} role="option"
            aria-selected={activeIndex === index} data-chosen={selection?.id === food.id || undefined}
            onMouseDown={event => event.preventDefault()} onClick={() => select(food)}>
            <span className="picker-food-name">{food.name}</span>
            {food.preparation && food.preparation !== 'Unspecified' && <span className="picker-preparation">{food.preparation}</span>}
          </li>)}
        </ul>}
      </div>
      {foodState.status === 'error' && <div className="empty"><p role="alert">Foods are unavailable right now.</p>
        <button className="show-options" type="button" onClick={() => {
          inputRef.current?.focus();
          onRetry();
        }}>Retry ingredient search</button></div>}
    </section>
  );
}
