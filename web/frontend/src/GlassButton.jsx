import React, { useEffect, useRef } from 'react';

export function GlassButton({ pending = false, children, ...props }) {
  const frame = useRef(null);
  useEffect(() => () => cancelAnimationFrame(frame.current), []);

  function moveLight(event) {
    if (event.type === 'pointermove' && !['mouse','pen'].includes(event.pointerType)) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || pending) return;
    const node = event.currentTarget;
    const { left, top, width, height } = node.getBoundingClientRect();
    const clamp = value => Math.min(100, Math.max(0, value));
    const x = clamp((event.clientX - left) / width * 100);
    const y = clamp((event.clientY - top) / height * 100);
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => {
      node.style.setProperty('--light-x', `${x}%`);
      node.style.setProperty('--light-y', `${y}%`);
      node.style.setProperty('--bend', `${(x - 50) * .15}px`);
    });
  }

  function resetLight(event) {
    cancelAnimationFrame(frame.current);
    const style = event.currentTarget.style;
    for (const key of ['--light-x','--light-y','--bend']) style.removeProperty(key);
  }

  return (
    <button {...props} className="glass-button"
      aria-disabled={pending || undefined} data-pending={pending || undefined}
      onPointerMove={moveLight} onPointerDown={moveLight}
      onPointerLeave={resetLight} onPointerCancel={resetLight} onBlur={resetLight}>
      <span className="glass-seam" aria-hidden="true" />
      <span className="glass-light" aria-hidden="true" />
      <span className="glass-label">{children}</span>
    </button>
  );
}
