// A metric page: series tabs, the world map with its year filter, and the line chart with its country filter.
// The page state (series, year, countries) lives in the URL so any view can be shared.
// gettext and interpolate are Django's, from the translation catalog base.html loads.
import { createCountryPicker } from './lib/country-picker.js';
import { escapeHtml, formatValue } from './lib/format.js';
import { createLineChart, PALETTE, WORLD_COLOR } from './lib/line-chart.js';
import { createWorldMap, renderLegend } from './lib/world-map.js';

const { dataUrl, units, defaultCountries } = JSON.parse(document.getElementById('metric-config').textContent);
const WORLD = 'WLD';
const MAX_COUNTRIES = PALETTE.length;
// A metric can name its own (metrics/catalog.py), e.g. when one country's extremes would flatten every other line.
const DEFAULT_COUNTRIES = defaultCountries.length ? defaultCountries : ['USA', 'CHN', 'IND', 'DEU', 'BRA'];

const mapCard = document.querySelector('[data-map-card]');
const lineCard = document.querySelector('[data-line-card]');
const yearSelect = document.querySelector('[data-year]');
const legend = document.querySelector('[data-legend]');
const keys = document.querySelector('[data-keys]');
const table = document.querySelector('[data-table]');
const seriesButtons = [...document.querySelectorAll('[data-series]')];
const seriesTabs = document.querySelector('.series-tabs');
const rank = {
  title: document.querySelector('[data-rank-title]'),
  series: document.querySelector('[data-rank-series]'),
  list: document.querySelector('[data-rank-list]'),
  world: document.querySelector('[data-rank-world]'),
};
const RANK_LENGTH = 10;

const params = new URLSearchParams(window.location.search);
const state = {
  field: params.get('series') || seriesButtons[0]?.dataset.series || '',
  year: Number(params.get('year')) || null,
  selected: null,  // [{iso3, color}], filled on the first load
};

const cache = new Map();
function load(field) {
  if (!cache.has(field)) {
    const query = field ? `?series=${encodeURIComponent(field)}` : '';
    cache.set(field, fetch(`${dataUrl}${query}`).then((response) => response.json()));
  }
  return cache.get(field);
}

const map = createWorldMap(document.querySelector('[data-map]'), {
  units,
  roam: window.matchMedia('(pointer: fine)').matches,
  onSelect: (iso3) => addCountry(iso3),
});
const line = createLineChart(document.querySelector('[data-line]'), { units });
const picker = createCountryPicker(document.querySelector('[data-picker]'), {
  max: MAX_COUNTRIES,
  onToggle: (iso3) => (state.selected.some((s) => s.iso3 === iso3) ? removeCountry(iso3) : addCountry(iso3)),
});

// ---------- Selection: a country keeps its colour while it stays on the chart ----------
function countryCount() {
  return state.selected.filter((s) => s.iso3 !== WORLD).length;
}

function freeColor() {
  const used = new Set(state.selected.map((s) => s.color));
  return PALETTE.find((color) => !used.has(color));
}

function addCountry(iso3) {
  if (state.selected.some((s) => s.iso3 === iso3)) return;
  if (iso3 !== WORLD && countryCount() >= MAX_COUNTRIES) return;
  state.selected.push({ iso3, color: iso3 === WORLD ? WORLD_COLOR : freeColor() });
  drawLine();
}

function removeCountry(iso3) {
  state.selected = state.selected.filter((s) => s.iso3 !== iso3);
  drawLine();
}

function initialSelection(data) {
  const fromUrl = (params.get('countries') || '').split(',').filter((iso3) => data.countries[iso3]);
  const codes = fromUrl.length ? fromUrl : [data.world, ...DEFAULT_COUNTRIES].filter((iso3) => iso3 && data.countries[iso3]);
  state.selected = [];
  for (const iso3 of codes.slice(0, MAX_COUNTRIES + 1)) {
    state.selected.push({ iso3, color: iso3 === WORLD ? WORLD_COLOR : freeColor() });
  }
}

// ---------- Drawing ----------
let data = null;

async function drawAll() {
  mapCard.classList.add('is-loading');
  lineCard.classList.add('is-loading');
  data = await load(state.field);
  if (state.selected === null) initialSelection(data);

  document.querySelectorAll('[data-series-label]').forEach((el) => { el.textContent = `· ${data.label}`; });
  seriesButtons.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.series === data.field)));

  const options = [
    ...(data.world ? [{ iso3: data.world, ...data.countries[data.world], world: true }] : []),
    ...Object.entries(data.countries)
      .filter(([iso3]) => iso3 !== WORLD)
      .map(([iso3, country]) => ({ iso3, ...country, world: false }))
      .sort((a, b) => a.name.localeCompare(b.name)),
  ];
  picker.setOptions(options);

  fillYears();
  await drawMap();
  drawLine();
  mapCard.classList.remove('is-loading');
  lineCard.classList.remove('is-loading');
}

function fillYears() {
  const covered = data.years.filter((_, i) => Object.entries(data.values).some(([iso3, v]) => iso3 !== WORLD && v[i] !== null));
  if (!covered.includes(state.year)) state.year = data.mapYear;
  yearSelect.innerHTML = [...covered].reverse()
    .map((year) => `<option value="${year}"${year === state.year ? ' selected' : ''}>${year}</option>`).join('');
}

async function drawMap() {
  const { scale } = await map.render(data, state.year);
  renderLegend(legend, data, scale, units);
  drawRanking();
  syncUrl();
}

// The rail follows the map: highest values for the series and year on screen.
function drawRanking() {
  if (!rank.list) return;
  const rule = units[data.unit];
  // A long unit ("per 1,000") would crowd out country names; the note above the list names it.
  // Same rule as metrics/formatting.py (compact).
  const rowRule = rule.long ? { ...rule, suffix: '' } : rule;
  const i = data.years.indexOf(state.year);
  const rows = Object.entries(data.values)
    .filter(([iso3, values]) => iso3 !== WORLD && values[i] !== null)
    .sort((a, b) => b[1][i] - a[1][i])
    .slice(0, RANK_LENGTH);
  rank.title.textContent = interpolate(gettext('Highest values, %s'), [state.year]);
  rank.series.textContent = data.label;
  rank.list.innerHTML = rows.map(([iso3, values], n) => {
    const country = data.countries[iso3];
    return `<li><span class="rank-list__n">${n + 1}</span>`
      + `<img class="flag" src="${escapeHtml(country.flag)}" alt="" width="28" height="21" loading="lazy">`
      + `<button type="button" data-add-country="${iso3}">${escapeHtml(country.name)}</button>`
      + `<span class="rank-list__value">${escapeHtml(formatValue(values[i], rowRule))}</span></li>`;
  }).join('');
  const world = data.world ? data.values[data.world][i] : null;
  rank.world.hidden = world === null || world === undefined;
  if (!rank.world.hidden) rank.world.querySelector('strong').textContent = formatValue(world, rule);
}

function drawLine() {
  const shown = line.render(data, state.selected);
  picker.setSelected(state.selected.map((s) => s.iso3));
  drawKeys(shown);
  drawTable(shown);
  syncUrl();
}

function drawKeys(shown) {
  keys.replaceChildren(...state.selected.map(({ iso3, color }) => {
    const country = data.countries[iso3];
    const key = document.createElement('span');
    key.className = 'series-key';
    key.setAttribute('role', 'listitem');
    const lineKey = document.createElement('i');
    lineKey.className = `series-key__line${iso3 === WORLD ? ' series-key__line--dashed' : ''}`;
    lineKey.style.background = color;
    const flag = document.createElement('img');
    flag.className = 'flag';
    flag.src = country?.flag || '';
    flag.alt = '';
    const name = document.createElement('span');
    name.textContent = shown.includes(iso3) ? country.name : interpolate(gettext('%s (no data)'), [country?.name || iso3]);
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.setAttribute('aria-label', interpolate(gettext('Remove %s'), [country?.name || iso3]));
    remove.innerHTML = '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M1 1l8 8M9 1l-8 8" stroke="currentColor" stroke-width="1.6"/></svg>';
    remove.addEventListener('click', () => removeCountry(iso3));
    key.append(lineKey, flag, name, remove);
    return key;
  }));
}

function drawTable(shown) {
  const rule = units[data.unit];
  const head = `<thead><tr><th scope="col">${escapeHtml(gettext('Year'))}</th>${shown.map((iso3) => `<th scope="col">${escapeHtml(data.countries[iso3].name)}</th>`).join('')}</tr></thead>`;
  const rows = data.years.map((year, i) => ({ year, values: shown.map((iso3) => data.values[iso3][i]) }))
    .filter((row) => row.values.some((v) => v !== null))
    .reverse()
    .map((row) => `<tr><td>${row.year}</td>${row.values.map((v) => `<td>${escapeHtml(formatValue(v, rule))}</td>`).join('')}</tr>`);
  table.innerHTML = `${head}<tbody>${rows.join('')}</tbody>`;
}

function syncUrl() {
  const next = new URLSearchParams();
  if (seriesButtons.length && state.field !== seriesButtons[0].dataset.series) next.set('series', state.field);
  if (state.year && state.year !== data?.mapYear) next.set('year', state.year);
  if (state.selected) next.set('countries', state.selected.map((s) => s.iso3).join(','));
  const query = next.toString();
  history.replaceState(null, '', `${window.location.pathname}${query ? `?${query}` : ''}`);
}

// ---------- Controls ----------
yearSelect.addEventListener('change', () => {
  state.year = Number(yearSelect.value);
  drawMap();
});

seriesButtons.forEach((button) => button.addEventListener('click', () => {
  if (button.dataset.series === state.field) return;
  state.field = button.dataset.series;
  state.year = null;
  drawAll();
}));

rank.list?.addEventListener('click', (event) => {
  const button = event.target.closest('[data-add-country]');
  if (!button) return;
  addCountry(button.dataset.addCountry);
  lineCard.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center' });
});

// The tab strip fades at its right edge only while more tabs hide past it.
if (seriesTabs) {
  const markOverflow = () => seriesTabs.classList.toggle('is-overflowing',
    seriesTabs.scrollLeft + seriesTabs.clientWidth < seriesTabs.scrollWidth - 1);
  seriesTabs.addEventListener('scroll', markOverflow, { passive: true });
  new ResizeObserver(markOverflow).observe(seriesTabs);
}

drawAll();
