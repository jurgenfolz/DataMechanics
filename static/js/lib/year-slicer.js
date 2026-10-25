// The year slider: two handles on one track that pick a window of years (templates/partials/year_slicer.html).
// The Politics page and the metric pages use it; each decides what the window limits.

/**
 * Wires the slider inside `root`. `onChange([from, to])` runs while a handle moves.
 * Returns set(full, current): the years the track spans, and the window the handles show.
 */
export function createYearSlicer(root, { onChange }) {
  const from = root.querySelector('[data-from]');
  const to = root.querySelector('[data-to]');
  const fromLabel = root.querySelector('[data-year-from]');
  const toLabel = root.querySelector('[data-year-to]');
  const track = root.querySelector('[data-slicer-track]');

  // The two handles never cross: moving one past the other stops one year short of it.
  for (const [input, other, side] of [[from, to, 0], [to, from, 1]]) {
    input.addEventListener('input', () => {
      const bound = Number(other.value);
      const year = side === 0 ? Math.min(Number(input.value), bound - 1) : Math.max(Number(input.value), bound + 1);
      onChange(side === 0 ? [year, bound] : [bound, year]);
    });
  }

  function set([first, last], [start, end]) {
    for (const input of [from, to]) {
      input.min = first;
      input.max = last;
    }
    from.value = start;
    to.value = end;
    fromLabel.textContent = start;
    toLabel.textContent = end;
    const share = (year) => String((year - first) / Math.max(last - first, 1));
    track.style.setProperty('--from', share(start));
    track.style.setProperty('--to', share(end));
  }

  return { set };
}

/** A window inside [first, last], or null when it covers every year (or no longer makes sense). */
export function fitWindow(window, [first, last]) {
  if (!window) return null;
  const from = Math.max(first, Math.min(window[0], window[1]));
  const to = Math.min(last, Math.max(window[0], window[1]));
  if (from >= to || (from === first && to === last)) return null;
  return [from, to];
}
