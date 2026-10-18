// A Politics country page: metric tabs, measure tabs, the chart coloured by president, the presidents and the numbers.
// The metric and the measure live in the URL so any view can be shared. Without JavaScript the tabs are plain links.
// gettext, ngettext and interpolate are Django's, from the translation catalog base.html loads.
import { escapeHtml, formatValue } from './lib/format.js';
import { createTermChart, logoHtml, trendHtml, trendSaid } from './lib/term-chart.js';

const config = JSON.parse(document.getElementById('politics-config').textContent);
const { units, metrics } = config;
// The chart opens on about the last 40 years, fewer on narrow screens: earlier presidencies are a drag away.
const YEARS_SHOWN = { min: 12, max: 40, pixelsPerYear: 25 };

const card = document.querySelector('[data-chart-card]');
const canvas = document.querySelector('[data-term-chart]');
const empty = document.querySelector('[data-empty]');
const title = document.querySelector('[data-metric-title]');
const seriesLabel = document.querySelector('[data-series-label]');
const summary = document.querySelector('[data-metric-summary]');
const metricLink = document.querySelector('[data-metric-link]');
const source = document.querySelector('[data-source]');
const seriesTabs = document.querySelector('[data-series-tabs]');
const list = document.querySelector('[data-presidencies]');
const listNote = document.querySelector('[data-presidencies-note]');
const table = document.querySelector('[data-table]');
const categories = [...document.querySelectorAll('[data-group]')];
const panels = [...document.querySelectorAll('[data-group-panel]')];
const metricTabs = [...document.querySelectorAll('[data-metric]')];

const state = { metric: config.metric, field: config.series, range: null, active: null, data: null };

const chart = createTermChart(canvas, {
  units,
  onZoom(range) {
    state.range = range;
    state.active = null;
    markActive();
  },
});

const cache = new Map();
function load(metric, field) {
  const key = `${metric}:${field}`;
  if (!cache.has(key)) {
    const query = new URLSearchParams({ metric, series: field });
    cache.set(key, fetch(`${config.dataUrl}?${query}`).then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    }));
  }
  return cache.get(key);
}

async function draw() {
  card.classList.add('is-loading');
  let data;
  try {
    data = await load(state.metric, state.field);
  } catch (error) {
    cache.delete(`${state.metric}:${state.field}`);
    showEmpty(gettext('The data did not load. Reload the page to try again.'));
    card.classList.remove('is-loading');
    return;
  }
  card.classList.remove('is-loading');
  state.data = data;
  seriesLabel.textContent = `· ${data.label}`;
  seriesLabel.hidden = metrics[state.metric].series.length < 2 || data.label === metrics[state.metric].title;
  drawSource(data.source);
  if (!data.points.length) {
    showEmpty(interpolate(gettext('No data for %s on this measure yet.'), [data.country]));
  } else {
    empty.hidden = true;
    if (!state.range) state.range = defaultRange(data);
    chart.render(data, state.active === null ? state.range : rangeOf(data.presidencies[state.active]));
  }
  drawPresidencies(data);
  drawTable(data);
}

function showEmpty(message) {
  empty.textContent = message;
  empty.hidden = false;
  chart.chart.clear();
  list.replaceChildren();
  listNote.hidden = true;
  table.replaceChildren();
}

// Starts where a presidency starts, so its first label is on screen.
function defaultRange(data) {
  const first = data.points[0][0];
  const last = data.points.at(-1)[0];
  const years = Math.min(YEARS_SHOWN.max, Math.max(YEARS_SHOWN.min, Math.round(canvas.clientWidth / YEARS_SHOWN.pixelsPerYear)));
  const starts = data.presidencies.filter((p) => p.spans.length).map((p) => p.spans[0].from).filter((x) => x >= last - years);
  return [Math.max(first, starts.length ? Math.min(...starts) : last - years), last];
}

// A presidency's years with one year either side, inside the data.
function rangeOf(presidency) {
  const points = state.data.points;
  const from = presidency.spans[0].from - 1;
  const to = presidency.spans.at(-1).to + 1;
  return [Math.max(points[0][0], from), Math.min(points.at(-1)[0], to)];
}

// ---------- Text around the chart ----------
function drawHead() {
  const metric = metrics[state.metric];
  title.textContent = metric.title;
  summary.textContent = metric.summary;
  seriesLabel.hidden = metric.series.length < 2;
  metricLink.href = metric.url;
  canvas.setAttribute('aria-label', interpolate(gettext('%(title)s in %(name)s over time, coloured by the president in office. The list below gives the change during each presidency.'),
    { title: metric.title, name: config.countryName }, true));
  seriesTabs.hidden = metric.series.length < 2;
  seriesTabs.replaceChildren(...metric.series.map((s) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.series = s.field;
    button.textContent = s.label;
    button.setAttribute('aria-pressed', String(s.field === state.field));
    return button;
  }));
  for (const tab of metricTabs) {
    if (tab.dataset.metric === state.metric) tab.setAttribute('aria-current', 'page');
    else tab.removeAttribute('aria-current');
  }
  const panel = panels.find((p) => p.querySelector(`[data-metric="${state.metric}"]`));
  showGroup(panel?.dataset.groupPanel);
  document.title = `${interpolate(gettext('%(name)s by president: %(title)s'), { name: config.countryName, title: metric.title }, true)} · Data Mechanics`;
}

function showGroup(name) {
  for (const p of panels) p.hidden = p.dataset.groupPanel !== name;
  for (const tab of categories) {
    if (tab.dataset.group === name) tab.setAttribute('aria-current', 'true');
    else tab.removeAttribute('aria-current');
  }
}

function drawSource(load) {
  if (!load) {
    source.textContent = gettext('Source: not loaded yet.');
    return;
  }
  const updated = load.updated && !load.name.includes(load.updated)
    ? ` (${escapeHtml(interpolate(gettext('updated %(date)s'), { date: load.updated }, true))})` : '';
  const fetched = escapeHtml(interpolate(gettext('fetched %(date)s'), { date: load.fetched }, true));
  source.innerHTML = `${escapeHtml(gettext('Source:'))} <a href="${escapeHtml(load.url)}">${escapeHtml(load.name)}</a>${updated} · ${fetched}`;
}

// ---------- The presidents with data, as a timeline from today back. Pressing one zooms the chart to it ----------
function drawPresidencies(data) {
  const shown = data.presidencies.map((p, index) => ({ p, index })).filter(({ p }) => p.summary).reverse();
  list.replaceChildren(...shown.map(({ p, index }) => {
    // The parties a presidency held, in order. Months without a party show as grey on the line, not as a logo here.
    const parties = [...new Map(p.spans.map((s) => [s.party.name, s.party])).values()].filter((party) => party.abbreviation);
    const logos = parties.length ? parties : [p.party];
    const years = `${p.start.slice(0, 4)}–${p.current ? gettext('now') : p.end.slice(0, 4)}`;
    const partyNames = logos.map((party) => party.abbreviation || party.name).join(', ');
    const s = p.summary;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `term-row${p.current ? ' is-current' : ''}`;
    button.dataset.index = index;
    button.setAttribute('aria-pressed', 'false');
    button.style.setProperty('--party', logos.at(-1).color);
    button.title = `${p.leader}, ${p.role}`;
    button.setAttribute('aria-label', `${interpolate(gettext('%(years)s, %(name)s, %(parties)s: from %(start)s to %(end)s.'),
      { years, name: p.leader, parties: partyNames, start: s.startLabel, end: s.endLabel }, true)} ${trendSaid(s)}`);
    const status = p.current ? ` · ${escapeHtml(gettext('In office'))}` : '';
    button.innerHTML = `<span class="term-row__years">${years}</span><span class="term-row__rail"></span>`
      + `<span class="term-row__logos">${logos.map(logoHtml).join('')}</span>`
      + `<span class="term-row__who"><strong>${escapeHtml(p.shortName)}</strong>`
      + `<span><span class="term-row__when">${years} · </span>${escapeHtml(partyNames)}${status}</span></span>`
      + `<span class="term-row__values">${escapeHtml(s.startLabel)} → ${escapeHtml(s.endLabel)}</span>${trendHtml(s)}`;
    const item = document.createElement('li');
    item.append(button);
    return item;
  }));
  const left = data.presidencies.length - shown.length;
  listNote.hidden = !left;
  listNote.textContent = interpolate(ngettext('%s president without enough data for this measure is not listed.',
    '%s presidents without enough data for this measure are not listed.', left), [left]);
  markActive();
}

function markActive() {
  for (const button of list.querySelectorAll('button[data-index]')) {
    button.setAttribute('aria-pressed', String(Number(button.dataset.index) === state.active));
  }
}

function drawTable(data) {
  const rule = units[data.unit];
  const owner = (year) => data.presidencies.flatMap((p) => p.spans.map((s) => ({ p, s })))
    .find(({ s }) => s.from < year && year <= s.to);
  const rows = [...data.points].reverse().map(([year, value]) => {
    const who = owner(year);
    return `<tr><td>${year}</td><td>${escapeHtml(formatValue(value, rule))}</td>`
      + `<td>${escapeHtml(who?.p.shortName || '–')}</td><td>${escapeHtml(who?.s.party.abbreviation || who?.s.party.name || '–')}</td></tr>`;
  });
  const heads = [gettext('Year'), data.label, gettext('In office on 1 July'), gettext('Party')];
  table.innerHTML = `<thead><tr>${heads.map((head) => `<th scope="col">${escapeHtml(head)}</th>`).join('')}</tr></thead>`
    + `<tbody>${rows.join('')}</tbody>`;
}

function syncUrl() {
  const next = new URLSearchParams({ metric: state.metric });
  if (state.field !== metrics[state.metric].series[0].field) next.set('series', state.field);
  history.replaceState(null, '', `${window.location.pathname}?${next}`);
}

function select(metric, field) {
  state.metric = metric;
  state.field = field || metrics[metric].series[0].field;
  drawHead();
  syncUrl();
  draw();
}

// ---------- Controls ----------
for (const tab of categories) {
  tab.addEventListener('click', (event) => {
    event.preventDefault();
    const panel = panels.find((p) => p.dataset.groupPanel === tab.dataset.group);
    if (!panel.querySelector(`[data-metric="${state.metric}"]`)) select(panel.querySelector('[data-metric]').dataset.metric);
  });
}

for (const tab of metricTabs) {
  tab.addEventListener('click', (event) => {
    event.preventDefault();
    if (tab.dataset.metric !== state.metric) select(tab.dataset.metric);
  });
}

seriesTabs.addEventListener('click', (event) => {
  const button = event.target.closest('[data-series]');
  if (button && button.dataset.series !== state.field) select(state.metric, button.dataset.series);
});

list.addEventListener('click', (event) => {
  const button = event.target.closest('button[data-index]');
  if (!button || !state.data) return;
  const index = Number(button.dataset.index);
  state.active = state.active === index ? null : index;
  chart.zoomTo(state.active === null ? state.range : rangeOf(state.data.presidencies[index]));
  markActive();
});

// A tab strip that does not fit fades at its right edge while more tabs hide past it.
for (const strip of [document.querySelector('.pol-cats'), seriesTabs]) {
  const markOverflow = () => strip.classList.toggle('is-overflowing', strip.scrollLeft + strip.clientWidth < strip.scrollWidth - 1);
  strip.addEventListener('scroll', markOverflow, { passive: true });
  new ResizeObserver(markOverflow).observe(strip);
}

drawHead();
draw();
