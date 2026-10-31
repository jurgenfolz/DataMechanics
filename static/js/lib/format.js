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

/** A whole number with the language's thousands mark: 12,400,000 in English, 12.400.000 in German. */
export function formatWhole(value, units) {
  return Math.round(value).toLocaleString('en').replace(/,/g, units.people.group);
}

/**
 * The size of a change, without its sign (an arrow gives the direction), as metrics/formatting.py's format_amount writes it.
 * A `relative` change is in percent of the start value; any other is in the unit, with a long unit's words left out.
 */
export function formatAmount(amount, rule, unit, relative) {
  const size = Math.abs(amount);
  if (relative) return `${marks(size < 10 ? size.toFixed(1) : Math.round(size).toLocaleString('en'), rule)}%`;
  if (unit === 'percent') return `${marks(size.toLocaleString('en', { minimumFractionDigits: 1, maximumFractionDigits: 1 }), rule)}%`;
  return formatValue(size, shortRule(rule));
}

/** The rule without a long unit's words, as format_value(compact=True) writes values where room is tight. */
export function shortRule(rule) {
  return rule.long ? { ...rule, suffix: '' } : rule;
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

/**
 * What fits on a party's badge, the stand-in for a missing logo: an abbreviation of up to 4 characters as it is,
 * a longer one's initials (Non-affiliated gives NA) and a long single word's first 3 letters (Crossbench gives Cro).
 */
export function badgeText(abbreviation) {
  if (abbreviation.length <= 4) return abbreviation;
  const words = abbreviation.split(/[\s-]+/).filter(Boolean);
  if (words.length > 1) return words.map((word) => word[0]).join('').toUpperCase().slice(0, 4);
  return abbreviation.slice(0, 3);
}

export function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}
