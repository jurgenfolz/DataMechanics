// World choropleth on a Mercator projection.
// Used by the metric page and the home page spotlight. Needs the global `echarts`, and Django's gettext and interpolate.
import { escapeHtml, formatValue } from './format.js';

// Metrics with a better direction: red (worse) -> neutral grey -> blue (better). Midpoint: the median country.
export const DIVERGING = ['#e66767', '#ab5b5b', '#724d4e', '#3a3d41', '#455a75', '#4e79ac', '#5598e7'];
// Metrics without a better direction: one blue ramp, dark (low) to light (high).
export const SEQUENTIAL = ['#0d366b', '#104281', '#1c5cab', '#2a78d6', '#5598e7', '#86b6ef', '#cde2fb'];
const NO_DATA = '#2a2c2f';
const BORDER = '#121416';
const HOVER = '#ffd700';
const WORLD = 'WLD';

// ---------- Mercator ----------
// The classic web map: country shapes stay true, areas grow towards the poles.
const RAD = Math.PI / 180;
const MAX_LATITUDE = 85;
// Width / height of the projected map, Antarctica left out (latitudes -56 to 84).
export const MAP_ASPECT = 1.54;

function project([lon, lat]) {
  const phi = Math.max(-MAX_LATITUDE, Math.min(MAX_LATITUDE, lat)) * RAD;
  return [lon * RAD * 100, -Math.log(Math.tan(Math.PI / 4 + phi / 2)) * 100];
}

function unproject([x, y]) {
  return [x / 100 / RAD, (2 * Math.atan(Math.exp(-y / 100)) - Math.PI / 2) / RAD];
}

let shapes;
// Country names from the shapes file, for the tooltip of a country without data.
const names = new Map();
export function loadShapes() {
  // base.html sets the URL, in the page's language, with a version that changes whenever the countries are reloaded.
  shapes ??= fetch(document.body.dataset.shapesUrl)
    .then((response) => response.json())
    .then((geojson) => {
      for (const feature of geojson.features) names.set(feature.properties.iso3, feature.properties.name);
      echarts.registerMap('world', geojson);
    });
  return shapes;
}

// ---------- Colour scale ----------
function quantile(sorted, q) {
  const i = (sorted.length - 1) * q;
  const lo = Math.floor(i);
  return sorted[lo] + (sorted[Math.ceil(i)] - sorted[lo]) * (i - lo);
}

function mix(a, b, t) {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  return `#${pa.map((v, i) => Math.round(v + (pb[i] - v) * t).toString(16).padStart(2, '0')).join('')}`;
}

function colorAt(colors, t) {
  const position = Math.min(Math.max(t, 0), 1) * (colors.length - 1);
  const i = Math.min(Math.floor(position), colors.length - 2);
  return mix(colors[i], colors[i + 1], position - i);
}

/** How a series' values for one year map to colours. Outliers beyond the 5th/95th percentile take the end colours. */
export function colorScale(series, values) {
  const transform = series.logScale ? (v) => Math.log10(Math.max(v, 1e-9)) : (v) => v;
  const sorted = values.map(transform).sort((a, b) => a - b);
  const lo = quantile(sorted, 0.05), hi = quantile(sorted, 0.95), mid = quantile(sorted, 0.5);
  const inverse = series.logScale ? (v) => 10 ** v : (v) => v;
  const diverging = Boolean(series.better);
  const colors = diverging ? DIVERGING : SEQUENTIAL;

  function unit(value) {
    const v = transform(value);
    if (!diverging) return hi === lo ? 0.5 : (v - lo) / (hi - lo);
    const t = v < mid ? 0.5 * (v - lo) / (mid - lo || 1) : 0.5 + 0.5 * (v - mid) / (hi - mid || 1);
    // Colours run from worse to better, so a "lower is better" series flips.
    return series.better === 'lower' ? 1 - t : t;
  }

  return {
    colors,  // worse -> better (diverging) or low -> high (sequential)
    color: (value) => colorAt(colors, unit(value)),
    ends: { low: inverse(lo), mid: inverse(mid), high: inverse(hi) },
    diverging,
  };
}

// ---------- The map ----------
export function createWorldMap(element, { units, onSelect, roam = false }) {
  const chart = echarts.init(element, null, { renderer: 'canvas' });
  let current = null;

  // The map's width in pixels, as large as the box allows without stretching it.
  const fit = () => Math.min(element.clientWidth, element.clientHeight * MAP_ASPECT) * 0.98;
  new ResizeObserver(() => {
    chart.resize();
    if (current) chart.setOption({ series: [{ layoutSize: fit() }] });
  }).observe(element);

  if (onSelect) {
    chart.on('click', (event) => {
      if (event.data?.raw !== undefined) onSelect(event.name);
    });
  }

  async function render(data, year) {
    await loadShapes();
    const rule = units[data.unit];
    const yearIndex = data.years.indexOf(year);
    const rows = Object.entries(data.values)
      .filter(([iso3, values]) => iso3 !== WORLD && values[yearIndex] !== null && values[yearIndex] !== undefined)
      .map(([iso3, values]) => ({ iso3, value: values[yearIndex] }));
    const scale = colorScale(data, rows.map((row) => row.value));
    const ranked = [...rows].sort((a, b) => b.value - a.value);
    const rank = new Map(ranked.map((row, i) => [row.iso3, i + 1]));

    current = { data, year, scale };
    chart.setOption({
      tooltip: {
        trigger: 'item',
        backgroundColor: '#17191b',
        borderColor: '#3a3d41',
        padding: [10, 12],
        extraCssText: 'border-radius:10px;box-shadow:0 12px 30px rgb(0 0 0 / .5);',
        formatter(params) {
          const country = data.countries[params.name];
          const name = escapeHtml(country?.name || names.get(params.name) || params.name);
          const flag = country?.flag ? `<img src="${escapeHtml(country.flag)}" alt="">` : '';
          if (params.data?.raw === undefined) {
            const muted = escapeHtml(interpolate(gettext('No data for %s'), [year]));
            return `<div class="tip"><div class="tip__head">${flag}${name}</div><div class="tip__muted">${muted}</div></div>`;
          }
          return `<div class="tip"><div class="tip__head">${flag}${name}</div>`
            + `<div class="tip__value">${escapeHtml(formatValue(params.data.raw, rule))}</div>`
            + `<div class="tip__muted">${escapeHtml(interpolate(gettext('%(year)s · rank %(rank)s of %(count)s'), { year, rank: rank.get(params.name), count: rows.length }, true))}</div></div>`;
        },
      },
      series: [{
        type: 'map',
        map: 'world',
        nameProperty: 'iso3',
        projection: { project, unproject },
        roam,
        scaleLimit: { min: 1, max: 8 },
        layoutCenter: ['50%', '50%'],
        layoutSize: fit(),
        selectedMode: false,
        itemStyle: { areaColor: NO_DATA, borderColor: BORDER, borderWidth: 0.6 },
        emphasis: { label: { show: false }, itemStyle: { areaColor: NO_DATA, borderColor: HOVER, borderWidth: 1.4 } },
        label: { show: false },
        data: rows.map((row) => {
          const fill = scale.color(row.value);
          return {
            name: row.iso3,
            raw: row.value,
            itemStyle: { areaColor: fill },
            emphasis: { itemStyle: { areaColor: fill, borderColor: HOVER, borderWidth: 1.4, shadowColor: 'rgba(255, 215, 0, 0.55)', shadowBlur: 14 } },
          };
        }),
      }],
    }, { replaceMerge: ['series'] });
    return { scale, count: rows.length };
  }

  return { render, chart, get current() { return current; } };
}

/** The legend under a map: a colour bar with its end values, and the "No data" swatch. */
export function renderLegend(container, data, scale, units) {
  const rule = units[data.unit];
  const stops = scale.colors.map((c, i) => `${c} ${(i / (scale.colors.length - 1)) * 100}%`).join(', ');
  const [left, right] = scale.diverging ? [gettext('Worse'), gettext('Better')] : [gettext('Lower'), gettext('Higher')];
  const lowEnd = scale.diverging && data.better === 'lower' ? scale.ends.high : scale.ends.low;
  const highEnd = scale.diverging && data.better === 'lower' ? scale.ends.low : scale.ends.high;

  container.replaceChildren();
  const block = document.createElement('div');
  block.className = 'legend__scale';
  const leftLabel = document.createElement('span');
  const bar = document.createElement('span');
  const rightLabel = document.createElement('span');
  const ends = document.createElement('span');
  leftLabel.textContent = left;
  rightLabel.textContent = right;
  bar.className = 'legend__bar';
  bar.style.background = `linear-gradient(90deg, ${stops})`;
  ends.className = 'legend__ends';
  const values = scale.diverging ? [lowEnd, scale.ends.mid, highEnd] : [lowEnd, highEnd];
  for (const value of values) {
    const tick = document.createElement('span');
    tick.textContent = formatValue(value, rule);
    ends.append(tick);
  }
  if (scale.diverging) ends.children[1].title = gettext('Median country');
  block.append(leftLabel, bar, rightLabel, ends);

  const noData = document.createElement('span');
  noData.className = 'legend__nodata';
  noData.append(document.createElement('i'), gettext('No data'));
  container.append(block, noData);
}
