// Writes values the way metrics/formatting.py does. The rules come from Python (units()), passed in as JSON.
// Each rule carries the page language's words for its unit and scales, and its decimal and thousands marks.

function significant(value, digits) {
  // Like Python's f'{value:.3g}': round to `digits` significant digits, drop trailing zeros.
  return String(Number(value.toPrecision(digits)));
}

// English writes 1,234.5; this swaps in the language's own marks.
function marks(number, rule) {
  return number.replace(/[,.]/g, (mark) => (mark === ',' ? rule.group : rule.decimal));
}

function compact(value, rule, digits) {
  for (const [size, suffix] of rule.scales) {
    if (Math.abs(value) >= size) return `${marks(significant(value / size, digits), rule)} ${suffix}`;
  }
  return marks(significant(value, digits), rule);
}

export function formatValue(value, rule) {
  if (value === null || value === undefined) return '–';
  const number = rule.compact
    ? compact(value, rule, rule.digits)
    : marks(value.toLocaleString('en', { minimumFractionDigits: rule.decimals, maximumFractionDigits: rule.decimals }), rule);
  return `${rule.prefix || ''}${number}${rule.suffix || ''}`;
}

// Axis ticks: the same rule, but without trailing decimals on round numbers.
export function formatTick(value, rule) {
  if (rule.compact) return `${rule.prefix || ''}${compact(value, rule, 3)}`;
  const decimals = Number.isInteger(value) ? 0 : rule.decimals;
  return `${rule.prefix || ''}${marks(value.toLocaleString('en', { maximumFractionDigits: decimals }), rule)}${rule.suffix === '%' ? '%' : ''}`;
}

// The smallest gap between axis ticks whose labels still differ: one step of the rule's last decimal.
// Without it, a narrow range of an index (0.053 to 0.055) labels two ticks the same.
export function tickStep(rule) {
  return rule.compact || rule.decimals === undefined ? undefined : 10 ** -rule.decimals;
}

export function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}
