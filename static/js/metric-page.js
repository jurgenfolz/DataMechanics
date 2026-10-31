// A metric page: series tabs, the world map with its year filter, and the line chart with its country filter and year slider.
// The slider limits the line chart, its table and its image; the map keeps its own year.
// The page state (series, year, countries, years) lives in the URL so any view can be shared.
// gettext and interpolate are Django's, from the translation catalog base.html loads.
import { createPicker } from './lib/picker.js';
import { eventOptions, loadEvents, pickEvents, renderEventKeys } from './lib/events.js';
import { escapeHtml, formatValue } from './lib/format.js';
import { bindSaveButton, imageName, saveChartImage } from './lib/chart-image.js';
import { createLineChart, lineImageParts, PALETTE, shownSpan, WORLD_COLOR } from './lib/line-chart.js';
import { CONTINENTS, createRankTable } from './lib/rank-table.js';
import { createWorldMap, mapImageParts, renderLegend } from './lib/world-map.js';
import { createYearSlicer, fitWindow } from './lib/year-slicer.js';
import { createRaceReel, TOP } from './lib/race-reel.js';
import { presentReel } from './lib/reel-frame.js';

const { slug, dataUrl, units, defaultCountries, opensFrom, eventsUrl } = JSON.parse(document.getElementById('metric-config').textContent);
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
const eventKeys = document.querySelector('[data-event-keys]');
const seriesButtons = [...document.querySelectorAll('[data-series]')];
const seriesTabs = document.querySelector('.series-tabs');
const seriesNote = document.querySelector('[data-series-note]');
const rankCard = document.querySelector('[data-rank-card]');
const rankYearSelect = rankCard.querySelector('[data-rank-year]');
const rankContinentSelect = rankCard.querySelector('[data-rank-continent]');
const rankNote = rankCard.querySelector('[data-rank-note]');
const rank = {
  title: document.querySelector('[data-rank-title]'),
  series: document.querySelector('[data-rank-series]'),
  list: document.querySelector('[data-rank-list]'),
  world: document.querySelector('[data-rank-world]'),
};
const RANK_LENGTH = 10;

const params = new URLSearchParams(window.location.search);
const urlWindow = [Number(params.get('from')), Number(params.get('to'))];
const state = {
  field: params.get('series') || seriesButtons[0]?.dataset.series || '',
  year: Number(params.get('year')) || null,
  selected: null,  // [{iso3, color}], filled on the first load
  window: urlWindow[0] && urlWindow[1] ? urlWindow : null,  // the line chart's [first year, last year], or null for every year
  events: (params.get('events') || '').split(',').filter(Boolean),  // the world events' slugs on the chart
  rankYear: Number(params.get('rank')) || null,  // the year of the table of every country, or null for the latest
  continent: params.get('continent') || '',  // the table's continent filter, '' for all
  sort: { by: 'rank', desc: false },  // the table's order
};
let events = [];  // every world event (lib/events.js), once loaded

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
const rankTable = createRankTable(rankCard.querySelector('[data-rank-table]'), {
  units,
  onSort: (sort) => {
    state.sort = sort;
    drawRank();
  },
});
const picker = createPicker(document.querySelector('[data-picker]'), {
  max: MAX_COUNTRIES,
  onToggle: (iso3) => (state.selected.some((s) => s.iso3 === iso3) ? removeCountry(iso3) : addCountry(iso3)),
});
const eventPicker = createPicker(document.querySelector('[data-events-picker]'), {
  emptyLabel: gettext('World events'),
  noMatch: gettext('No event matches.'),
  onToggle: (slug) => toggleEvent(slug),
});

// ---------- World events: marked on the line chart, kept in the URL ----------
function toggleEvent(slug) {
  state.events = state.events.includes(slug) ? state.events.filter((s) => s !== slug) : [...state.events, slug];
  drawLine();
}

function chosenEvents() {
  return pickEvents(events, state.events);
}

loadEvents(eventsUrl).then((loaded) => {
  events = loaded;
  state.events = state.events.filter((slug) => events.some((event) => event.slug === slug));
  eventPicker.setOptions(eventOptions(events));
  if (data && state.events.length) drawLine();
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
  if (state.selected === null) {
    initialSelection(data);
    // A metric with centuries of data opens at a readable year (metrics/catalog.py, opens_from); the slider reaches the rest.
    if (!state.window && opensFrom) state.window = [opensFrom, data.years.at(-1)];
  }

  document.querySelectorAll('[data-series-label]').forEach((el) => { el.textContent = `· ${data.label}`; });
  seriesNote.textContent = data.note;
  seriesNote.hidden = !data.note;
  seriesButtons.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.series === data.field)));

  const options = [
    ...(data.world ? [{ id: data.world, name: data.countries[data.world].name, image: data.countries[data.world].flag, label: gettext('World'), world: true }] : []),
    ...Object.entries(data.countries)
      .filter(([iso3]) => iso3 !== WORLD)
      .map(([iso3, country]) => ({ id: iso3, name: country.name, image: country.flag }))
      .sort((a, b) => a.name.localeCompare(b.name)),
  ];
  picker.setOptions(options);

  fillYears();
  await drawMap();
  drawLine();
  drawRank();
  mapCard.classList.remove('is-loading');
  lineCard.classList.remove('is-loading');
}

function fillYears() {
  const covered = coveredYears();
  if (!covered.includes(state.year)) state.year = data.mapYear;
  yearSelect.innerHTML = [...covered].reverse()
    .map((year) => `<option value="${year}"${year === state.year ? ' selected' : ''}>${year}</option>`).join('');
}

// ---------- Every country ranked, in one year ----------
function coveredYears() {
  return data.years.filter((_, i) => Object.entries(data.values).some(([iso3, v]) => iso3 !== WORLD && v[i] !== null));
}

function drawRank() {
  const covered = coveredYears();
  if (!covered.includes(state.rankYear)) state.rankYear = data.mapYear;
  rankYearSelect.innerHTML = [...covered].reverse()
    .map((year) => `<option value="${year}"${year === state.rankYear ? ' selected' : ''}>${year}</option>`).join('');
  if (!CONTINENTS.some(([key]) => key === state.continent)) state.continent = '';
  rankContinentSelect.innerHTML = [['', gettext('All continents')], ...CONTINENTS.map(([key, label]) => [key, label()])]
    .map(([key, label]) => `<option value="${escapeHtml(key)}"${key === state.continent ? ' selected' : ''}>${escapeHtml(label)}</option>`).join('');
  const { shown, all } = rankTable.render(data, state.rankYear, { continent: state.continent, sort: state.sort });
  rankNote.textContent = state.continent
    ? interpolate(gettext("%(shown)s of the %(count)s countries with a value in %(year)s. The rank is each country's place among all of them."), { shown, count: all, year: state.rankYear }, true)
    : interpolate(ngettext('%(count)s country with a value in %(year)s, ranked by it.', '%(count)s countries with a value in %(year)s, ranked by it.', all), { count: all, year: state.rankYear }, true);
  syncUrl();
}

rankYearSelect.addEventListener('change', () => {
  state.rankYear = Number(rankYearSelect.value);
  drawRank();
});
rankContinentSelect.addEventListener('change', () => {
  state.continent = rankContinentSelect.value;
  drawRank();
});

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

// ---------- The line chart's years ----------
const slicerRoot = lineCard.querySelector('[data-year-slicer]');
const slicer = createYearSlicer(slicerRoot, {
  onChange(window) {
    state.window = fitWindow(window, lineYears());
    drawLine();
  },
});

// Every year the chosen countries have; the slider spans these.
function lineYears() {
  return shownSpan(data, state.selected).map((i) => data.years[i]);
}

function drawLine() {
  const years = lineYears();
  state.window = fitWindow(state.window, years);
  slicerRoot.hidden = years[1] - years[0] < 2;
  slicer.set(years, state.window || years);
  const chosen = chosenEvents();
  const shown = line.render(data, state.selected, state.window, chosen);
  picker.setSelected(state.selected.map((s) => s.iso3));
  eventPicker.setSelected(state.events);
  eventPicker.root.querySelector('[data-picker-button]').classList.toggle('is-set', chosen.length > 0);
  renderEventKeys(eventKeys, chosen, toggleEvent);
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
  const [from, to] = state.window || [-Infinity, Infinity];
  const rows = data.years.map((year, i) => ({ year, values: shown.map((iso3) => data.values[iso3][i]) }))
    .filter((row) => row.year >= from && row.year <= to && row.values.some((v) => v !== null))
    .reverse()
    .map((row) => `<tr><td>${row.year}</td>${row.values.map((v) => `<td>${escapeHtml(formatValue(v, rule))}</td>`).join('')}</tr>`);
  table.innerHTML = `${head}<tbody>${rows.join('')}</tbody>`;
}

function syncUrl() {
  const next = new URLSearchParams();
  if (seriesButtons.length && state.field !== seriesButtons[0].dataset.series) next.set('series', state.field);
  if (state.year && state.year !== data?.mapYear) next.set('year', state.year);
  if (state.selected) next.set('countries', state.selected.map((s) => s.iso3).join(','));
  if (state.window) {
    next.set('from', state.window[0]);
    next.set('to', state.window[1]);
  }
  if (state.events.length) next.set('events', state.events.join(','));
  if (state.rankYear && state.rankYear !== data?.mapYear) next.set('rank', state.rankYear);
  if (state.continent) next.set('continent', state.continent);
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

// ---------- Save as image ----------
const metricTitle = document.querySelector('.metric-head h1')?.textContent.trim();
const sourceOf = (card) => card.querySelector('.source-line')?.textContent.replace(/\s+/g, ' ').trim();

bindSaveButton(mapCard.querySelector('[data-save-image]'), (size) => data && saveChartImage({
  size,
  title: metricTitle,
  subtitle: `${data.label}, ${state.year}`,
  sources: [sourceOf(mapCard)],
  filename: imageName(slug, state.field, state.year),
  ...mapImageParts(data, state.year, units),
}));

bindSaveButton(lineCard.querySelector('[data-save-image]'), (size) => data && saveChartImage({
  size,
  title: metricTitle,
  subtitle: `${data.label} · ${shownSpan(data, state.selected, state.window).map((i) => data.years[i]).join('–')}`,
  sources: [sourceOf(lineCard)],
  filename: imageName(slug, state.field, 'over-time'),
  ...lineImageParts(data, state.selected, units, state.window, chosenEvents()),
}));

// ---------- The reel (lib/race-reel.js): a bar chart race for Instagram, or with &format=wide for YouTube and LinkedIn ----------
// ?reel=1 plays it over the page; ?reel=record draws nothing until tools/reel.py asks for each frame.
// &top=20 ranks the twenty highest countries of each year (any number works); without it, or with top=0, the race runs
// between the countries chosen on the page. The year slider's years bound it.
async function openReel(mode) {
  const format = params.get('format') === 'wide' ? 'wide' : 'reel';
  const asked = params.get('top');
  const top = asked === null || ['0', 'false', 'no'].includes(asked) ? 0 : (Number(asked) || TOP);
  const years = state.window || [data.years[0], data.years.at(-1)];
  const summary = document.querySelector('.metric-head__summary')?.textContent.trim() || '';
  const reel = await createRaceReel({
    format, data, units, years, top,
    selected: state.selected,
    title: metricTitle,
    unit: data.label === metricTitle ? '' : data.label,
    subtitle: `${top ? `${interpolate(gettext('Top %s each year'), [top])} · ` : ''}${years[0]}–${years[1]}`,
    explanation: summary,
    sources: [sourceOf(lineCard)],
  });
  const name = imageName(slug, state.field, top ? `top-${top}` : 'race', `${years[0]}-${years[1]}`, format === 'wide' && 'wide');
  presentReel(reel, name.replace(/\.png$/, '.mp4'), mode);
}

drawAll().then(() => {
  if (params.has('reel') && data) openReel(params.get('reel'));
});
