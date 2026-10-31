// What the World War II page's charts share: the sides' colours, dates as day numbers, who fought on which side
// on a given day, and the way numbers and ranges are written.
// gettext and interpolate are Django's, from the translation catalog base.html loads.
import { escapeHtml, formatValue } from './format.js';

// Validated with the dataviz palette script against the chart well (#1d1f21): both pairs pass every check.
export const SIDE_COLORS = { allies: '#3987e5', axis: '#d95926' };
export const DEATH_COLORS = { soldiers: '#3987e5', civilians: '#c98500' };
export const INK = '#f2f3f4';
export const INK_2 = '#b6b9bd';
export const INK_3 = '#8b8f94';
export const WELL = '#1d1f21';
export const GROUND = '#121416';
export const FONT = 'Archivo, "Helvetica Neue", Arial, sans-serif';
export const MONO = '"JetBrains Mono", ui-monospace, Menlo, Consolas, monospace';

const DAY = 86400000;

/** A date ("1941-06-22") as a whole number of days, so dates compare and subtract as numbers. */
export function toDay(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  return Math.round(Date.UTC(y, m - 1, d) / DAY);
}

export function fromDay(day) {
  return new Date(day * DAY);
}

const language = document.documentElement.lang || 'en';
const dateFormats = {
  long: new Intl.DateTimeFormat(language, { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }),
  month: new Intl.DateTimeFormat(language, { month: 'short', year: 'numeric', timeZone: 'UTC' }),
};

/** A day as the page writes it: "22 Jun 1941" (long) or "Jun 1941" (month), in the page's language. */
export function formatDay(day, style = 'long') {
  return dateFormats[style].format(fromDay(day));
}

/** A range of people as the site writes values: "4.44 m–5.32 m", one value when both ends agree, "–" when empty. */
export function formatRange([low, high], units, rule = units.people) {
  if (low === null || low === undefined) return '–';
  if (high === null || high === undefined || high === low) return formatValue(low, rule);
  return `${formatValue(low, rule)}–${formatValue(high, rule)}`;
}

/**
 * The side a state fought on that day: 'allies', 'axis' or null (not at war).
 * With no day (the whole war), the side it fought on longest: Italy and Romania count with the Axis.
 * A state with no sides of its own takes its ruler's: a colony fought with its empire, a puppet with its master.
 */
export function sideOn(states, code, day = null) {
  for (let state = states[code], depth = 0; state && depth < 4; state = states[state.ruler], depth += 1) {
    if (state.sides.length) {
      if (day === null) return state.longest;
      const side = state.sides.find(([, start, end]) => start <= day && day <= end);
      return side ? side[0] : null;
    }
  }
  return null;
}

/** Prepares the states for sideOn: dates become day numbers once, and each state learns its longest side. */
export function prepareStates(states, last) {
  for (const state of Object.values(states)) {
    state.sides = state.sides.map(([side, start, end]) => [side, toDay(start), end ? toDay(end) : Infinity]);
    const days = { allies: 0, axis: 0 };
    for (const [side, start, end] of state.sides) days[side] += Math.min(end, last) - start;
    state.longest = state.sides.length ? (days.axis > days.allies ? 'axis' : 'allies') : null;
  }
  return states;
}

/** A flag and a name for a tooltip's head. */
export function stateHead(state) {
  if (!state) return '';
  return `<img src="${escapeHtml(state.flag)}" alt="">${escapeHtml(state.name)}`;
}

/** Loads an image once; resolves to null when it fails, so a missing flag never stops a chart. */
const images = new Map();
export function image(src) {
  if (!images.has(src)) {
    images.set(src, new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = src;
    }));
  }
  return images.get(src);
}

/** Places an HTML tooltip near the pointer, inside its layer's parent, and keeps it on screen. */
export function placeTip(tip, html, x, y) {
  tip.innerHTML = html;
  tip.hidden = false;
  const box = tip.parentElement.getBoundingClientRect();
  const { width, height } = tip.getBoundingClientRect();
  const left = x + 16 + width > box.width ? x - 16 - width : x + 16;
  const top = Math.min(Math.max(y - height / 2, 8), box.height - height - 8);
  tip.style.transform = `translate(${Math.max(8, left)}px, ${Math.max(8, top)}px)`;
}

export const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
