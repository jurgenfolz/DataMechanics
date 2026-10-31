// The Compare page: one country and up to two metrics on one line chart, the first on the left axis, the second on the right.
// The state (country, metrics, years) lives in the URL so any view can be shared.
// gettext and interpolate are Django's, from the translation catalog base.html loads.
import { createPicker } from './lib/picker.js';
import { eventOptions, loadEvents, pickEvents, renderEventKeys } from './lib/events.js';
import { escapeHtml, formatValue } from './lib/format.js';
import { bindSaveButton, imageName, saveChartImage } from './lib/chart-image.js';
import { COLORS, compareImageParts, createCompareChart } from './lib/compare-chart.js';
import { createYearSlicer, fitWindow } from './lib/year-slicer.js';

const { units, defaults, metrics, eventsUrl } = JSON.parse(document.getElementById('compare-config').textContent);
const WORLD = 'WLD';
const NONE = 'none';  // the right select's value for "no second metric"

const card = document.querySelector('[data-compare-card]');
const selects = [document.querySelector('[data-left]'), document.querySelector('[data-right]')];
const keyMarks = [...document.querySelectorAll('[data-axis-key]')];
const countryLabel = document.querySelector('[data-country-label]');
const sources = document.querySelector('[data-sources]');
const missing = document.querySelector('[data-missing]');
const scaleNote = document.querySelector('[data-scale-note]');
const table = document.querySelector('[data-table]');
const about = document.querySelector('[data-about]');
const downloads = document.querySelector('[data-downloads]');
const downloadIcon = document.querySelector('[data-download-icon]');
const eventKeys = document.querySelector('[data-event-keys]');

const params = new URLSearchParams(window.location.search);
const offered = (key) => [...selects[0].options].some((option) => option.value === key);
const urlWindow = [Number(params.get('from')), Number(params.get('to'))];
const state = {
  country: params.get('country') || defaults.country,
  // [left, right]: a measure's key ("gdp-per-capita:ppp"), or NONE on the right.
  keys: [
    offered(params.get('left')) ? params.get('left') : defaults.left,
    params.get('right') === NONE || offered(params.get('right')) ? params.get('right') : defaults.right,
  ],
  window: urlWindow[0] && urlWindow[1] ? urlWindow : null,  // [first year, last year], or null for every year
  events: (params.get('events') || '').split(',').filter(Boolean),  // the world events' slugs on the chart
};
if (state.keys[1] === state.keys[0]) state.keys[1] = NONE;
let events = [];  // every world event (lib/events.js), once loaded

const cache = new Map();
function load(key) {
  if (!cache.has(key)) {
    const [slug, field] = key.split(':');
    const query = field ? `?series=${encodeURIComponent(field)}` : '';
    cache.set(key, fetch(`${metrics[slug].dataUrl}${query}`).then((response) => response.json()));
  }
  return cache.get(key);
}

const chart = createCompareChart(document.querySelector('[data-chart]'));
const picker = createPicker(document.querySelector('[data-picker]'), {
  single: true,
  emptyLabel: gettext('Choose a country'),
  onToggle(iso3) {
    if (iso3 === state.country) return;
    state.country = iso3;
    drawChart();
  },
});
const eventPicker = createPicker(document.querySelector('[data-events-picker]'), {
  emptyLabel: gettext('World events'),
  noMatch: gettext('No event matches.'),
  onToggle: (slug) => toggleEvent(slug),
});

// ---------- World events: marked on the chart, kept in the URL ----------
function toggleEvent(slug) {
  state.events = state.events.includes(slug) ? state.events.filter((s) => s !== slug) : [...state.events, slug];
  if (drawn) drawChart();
}

function chosenEvents() {
  return pickEvents(events, state.events);
}

loadEvents(eventsUrl).then((loaded) => {
  events = loaded;
  state.events = state.events.filter((slug) => events.some((event) => event.slug === slug));
  eventPicker.setOptions(eventOptions(events));
  if (drawn && state.events.length) drawChart();
});

// ---------- Loading ----------
let shown = [];  // the chosen measures: [{ side, key, slug, data }]
let countries = {};  // every country either measure has: { iso3: { name, flag } }
let latest = 0;  // the newest draw: an older one that finishes loading later is dropped

async function drawAll() {
  const run = ++latest;
  card.classList.add('is-loading');
  const chosen = state.keys.map((key, side) => ({ side, key })).filter(({ key }) => key !== NONE);
  const loaded = await Promise.all(chosen.map(({ key }) => load(key)));
  if (run !== latest) return;
  shown = chosen.map(({ side, key }, n) => ({ side, key, slug: key.split(':')[0], data: loaded[n] }));

  selects.forEach((select, side) => {
    select.value = state.keys[side];
    // A measure cannot be on both axes.
    for (const option of select.options) option.disabled = option.value !== NONE && option.value === state.keys[1 - side];
  });
  keyMarks.forEach((mark, side) => {
    mark.style.background = COLORS[side];
    mark.classList.toggle('is-off', state.keys[side] === NONE);
  });

  fillPicker();
  drawMetrics();
  drawChart();
  card.classList.remove('is-loading');
}

// The countries either measure has, the World first where a source has it.
function fillPicker() {
  countries = Object.assign({}, ...shown.map(({ data }) => data.countries));
  if (countries[WORLD]) countries[WORLD] = { ...countries[WORLD], name: gettext('World') };
  if (!countries[state.country]) state.country = countries[defaults.country] ? defaults.country : Object.keys(countries)[0];
  picker.setOptions([
    ...(countries[WORLD] ? [{ id: WORLD, name: countries[WORLD].name, image: countries[WORLD].flag, world: true }] : []),
    ...Object.entries(countries)
      .filter(([iso3]) => iso3 !== WORLD)
      .map(([iso3, country]) => ({ id: iso3, name: country.name, image: country.flag }))
      .sort((a, b) => a.name.localeCompare(b.name)),
  ]);
}

// One line per metric, even when both measures are of one metric (GDP per capita in US$ and at PPP).
function chosenMetrics() {
  return [...new Set(shown.map(({ slug }) => slug))].map((slug) => metrics[slug]);
}

// The sources over the chart, the downloads under it and the metrics' pages in the rail.
function drawMetrics() {
  sources.replaceChildren(...chosenMetrics().map((metric) => {
    const line = document.createElement('p');
    line.className = 'source-line';
    const name = document.createElement('span');
    name.className = 'source-line__metric';
    name.textContent = metric.title;
    const source = document.createElement('span');
    source.innerHTML = metric.source;  // the metric pages' own source line, rendered by Django
    line.append(name, ' · ', source);
    return line;
  }));

  downloads.replaceChildren(...chosenMetrics().map((metric) => {
    const link = document.createElement('a');
    link.className = 'button';
    link.href = metric.csvUrl;
    link.download = '';
    link.append(downloadIcon.content.cloneNode(true), ` ${interpolate(gettext('%s (CSV)'), [metric.title])}`);
    return link;
  }), Object.assign(document.createElement('p'), {
    textContent: gettext('Every country and year of each metric, with the source on each row.'),
  }));
}

// ---------- The chart ----------
const slicerRoot = card.querySelector('[data-year-slicer]');
const slicer = createYearSlicer(slicerRoot, {
  onChange(window) {
    state.window = fitWindow(window, allYears());
    drawChart();
  },
});

function valueIn(data, year) {
  return data.values[state.country]?.[year - data.years[0]] ?? null;
}

// The first and last year either measure has for the country; the slider spans these.
function allYears() {
  const years = shown.flatMap(({ data }) => (data.values[state.country] || [])
    .flatMap((value, i) => (value === null ? [] : [data.years[i]])));
  return years.length ? [Math.min(...years), Math.max(...years)] : null;
}

let drawn = null;  // what the chart shows: { years, lines }, for the table and the saved image

function drawChart() {
  const country = countries[state.country];
  countryLabel.textContent = country ? `· ${country.name}` : '';
  picker.setSelected([state.country]);
  drawAbout();

  const span = allYears();
  missing.hidden = shown.every(({ data }) => data.values[state.country]);
  missing.textContent = shown.filter(({ data }) => !data.values[state.country])
    .map(({ data }) => interpolate(gettext('%(measure)s has no data for %(country)s.'), { measure: data.label, country: country?.name || '' }, true))
    .join(' ');
  slicerRoot.hidden = !span || span[1] - span[0] < 2;
  if (!span) {
    drawn = null;
    chart.chart.clear();
    scaleNote.hidden = true;
    table.innerHTML = '';
    syncUrl();
    return;
  }

  state.window = fitWindow(state.window, span);
  slicer.set(span, state.window || span);
  const [from, to] = state.window || span;
  const years = Array.from({ length: to - from + 1 }, (_, i) => from + i);
  const lines = shown
    .map(({ side, data }) => ({
      side,
      label: data.label,
      axis: data.measuredIn || data.label,
      rule: units[data.unit],
      values: years.map((year) => valueIn(data, year)),
    }))
    .filter((line) => line.values.some((value) => value !== null));
  drawn = { years, lines };
  const chosen = chosenEvents();
  chart.render(years, lines, chosen);
  eventPicker.setSelected(state.events);
  eventPicker.root.querySelector('[data-picker-button]').classList.toggle('is-set', chosen.length > 0);
  renderEventKeys(eventKeys, chosen, toggleEvent);
  scaleNote.hidden = lines.length < 2;
  drawTable();
  syncUrl();
}

function drawTable() {
  const { years, lines } = drawn;
  const head = `<thead><tr><th scope="col">${escapeHtml(gettext('Year'))}</th>`
    + `${lines.map((line) => `<th scope="col">${escapeHtml(line.label)}</th>`).join('')}</tr></thead>`;
  const rows = years.map((year, i) => ({ year, values: lines.map((line) => line.values[i]) }))
    .filter((row) => row.values.some((value) => value !== null))
    .reverse()
    .map((row) => `<tr><td>${row.year}</td>${row.values.map((value, n) => `<td>${escapeHtml(formatValue(value, lines[n].rule))}</td>`).join('')}</tr>`);
  table.innerHTML = `${head}<tbody>${rows.join('')}</tbody>`;
}

function syncUrl() {
  const next = new URLSearchParams({ country: state.country, left: state.keys[0], right: state.keys[1] });
  if (state.window) {
    next.set('from', state.window[0]);
    next.set('to', state.window[1]);
  }
  if (state.events.length) next.set('events', state.events.join(','));
  history.replaceState(null, '', `${window.location.pathname}?${next}`);
}

// The rail: each metric's page, opened on this country.
function drawAbout() {
  about.replaceChildren(...chosenMetrics().map((metric) => {
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.className = 'rail-item';
    link.href = `${metric.url}?countries=${encodeURIComponent(state.country)}`;
    const title = document.createElement('span');
    title.className = 'rail-item__title';
    title.textContent = metric.title;
    const summary = document.createElement('span');
    summary.className = 'rail-item__sub';
    summary.textContent = metric.summary;
    link.append(title, summary);
    item.append(link);
    return item;
  }));
}

// ---------- Controls ----------
selects.forEach((select, side) => select.addEventListener('change', () => {
  state.keys[side] = select.value;
  drawAll();
}));

// ---------- Save as image ----------
bindSaveButton(card.querySelector('[data-save-image]'), (size) => {
  if (!drawn?.lines.length) return null;
  const country = countries[state.country];
  const titles = [...new Set(drawn.lines.map((line) => metrics[shown.find((s) => s.side === line.side).slug].title))];
  return saveChartImage({
    size,
    title: titles.length > 1 ? interpolate(gettext('%(first)s and %(second)s'), { first: titles[0], second: titles[1] }, true) : titles[0],
    subtitle: `${country.name}, ${drawn.years[0]}–${drawn.years.at(-1)}`,
    // Flags come in two shapes, in folders of the same names (media/flags/4x3 and 1x1); the World's has one shape.
    flag: country.flag.replace('/flags/4x3/', '/flags/1x1/'),
    sources: [...sources.children].map((line) => line.textContent.replace(/\s+/g, ' ').trim()),
    filename: imageName(state.country, ...shown.map(({ key }) => key)),
    ...compareImageParts(drawn.years, drawn.lines, chosenEvents()),
  });
});

drawAll();
