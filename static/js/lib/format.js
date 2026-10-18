// Writes values the way metrics/formatting.py does. The rules come from Python (UNITS), passed in as JSON.
const SCALES = [[1e12, 'tn'], [1e9, 'bn'], [1e6, 'm'], [1e3, 'k']];

function significant(value, digits) {
  // Like Python's f'{value:.3g}': round to `digits` significant digits, drop trailing zeros.
  return String(Number(value.toPrecision(digits)));
}

function compact(value, digits) {
  for (const [size, suffix] of SCALES) {
    if (Math.abs(value) >= size) return `${significant(value / size, digits)} ${suffix}`;
  }
  return significant(value, digits);
}

export function formatValue(value, rule) {
  if (value === null || value === undefined) return '–';
  const number = rule.compact
    ? compact(value, rule.digits)
    : value.toLocaleString('en', { minimumFractionDigits: rule.decimals, maximumFractionDigits: rule.decimals });
  return `${rule.prefix || ''}${number}${rule.suffix || ''}`;
}

// Axis ticks: the same rule, but without trailing decimals on round numbers.
export function formatTick(value, rule) {
  if (rule.compact) return `${rule.prefix || ''}${compact(value, 3)}`;
  const decimals = Number.isInteger(value) ? 0 : rule.decimals;
  return `${rule.prefix || ''}${value.toLocaleString('en', { maximumFractionDigits: decimals })}${rule.suffix === '%' ? '%' : ''}`;
}

export function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}
