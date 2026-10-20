// A Politics country page: metric tabs, measure tabs, the chart coloured by president, the year slider, the presidents
// (as a timeline or ranked by party or by president) and the numbers.
// One window of years, set by the slider or by pressing a president, applies to the chart's zoom, the lists and the table.
// The metric, the measure, the view and the window live in the URL so any view can be shared.
// Without JavaScript the tabs are plain links.
// gettext, ngettext and interpolate are Django's, from the translation catalog base.html loads.
import { escapeHtml, formatValue } from './lib/format.js';
import { bindSaveButton, imageName, saveChartImage } from './lib/chart-image.js';
import { createTermChart, logoHtml, termImageParts, trendHtml, trendSaid } from './lib/term-chart.js';
import {
  barScale, groupRows, logoCredits, omittedNote, saveTimelineImages, timelineRows, valueRange,
} from './lib/timeline.js';
import { toneOf } from './lib/term-chart.js';

const config = JSON.parse(document.getElementById('politics-config').textContent);
const { units, metrics } = config;
const LIST_DELAY = 250;  // ms the lists wait for the slider to settle before they ask for the new years

const card = document.querySelector('[data-chart-card]');
const canvas = document.querySelector('[data-term-chart]');
const empty = document.querySelector('[data-empty]');
const title = document.querySelector('[data-metric-title]');
const seriesLabel = document.querySelector('[data-series-label]');
const seriesNote = document.querySelector('[data-series-note]');
const summary = document.querySelector('[data-metric-summary]');
const metricLink = document.querySelector('[data-metric-link]');
const source = document.querySelector('[data-source]');
const seriesTabs = document.querySelector('[data-series-tabs]');
const list = document.querySelector('[data-presidencies]');
const listNote = document.querySelector('[data-presidencies-note]');
const ranking = document.querySelector('[data-ranking]');
const rankingList = document.querySelector('[data-ranking-list]');
const viewButtons = [...document.querySelectorAll('[data-view]')];
const VIEWS = ['timeline', 'party', 'president'];
const table = document.querySelector('[data-table]');
const slicer = {
  from: document.querySelector('[data-from]'),
  to: document.querySelector('[data-to]'),
  fromLabel: document.querySelector('[data-year-from]'),
  toLabel: document.querySelector('[data-year-to]'),
  track: document.querySelector('[data-slicer-track]'),
};
const categories = [...document.querySelectorAll('[data-group]')];
const panels = [...document.querySelectorAll('[data-group-panel]')];
const metricTabs = [...document.querySelectorAll('[data-metric]')];

const params = new URLSearchParams(window.location.search);
const urlWindow = [Number(params.get('from')), Number(params.get('to'))];
const state = {
  metric: config.metric,
  field: config.series,
  view: VIEWS.includes(params.get('view')) ? params.get('view') : 'timeline',
  data: null,  // the series, every year
  lists: null,  // the presidents' changes and rankings inside the window
  window: urlWindow[0] && urlWindow[1] ? urlWindow : null,  // [first year, last year], or null for every year
  active: null,  // the pressed president's index, whose years the window shows
  beforeActive: null,  // the window to go back to when the president is pressed again
};

const chart = createTermChart(canvas, { units, slider: false });

const cache = new Map();
function load(metric, field, window = null) {
  const key = [metric, field, ...(window || [])].join(':');
  if (!cache.has(key)) {
    const query = new URLSearchParams({ metric, series: field });
    if (window) {
      query.set('from', window[0]);
      query.set('to', window[1]);
    }
    cache.set(key, fetch(`${config.dataUrl}?${query}`).then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    }).catch((error) => {
      cache.delete(key);
      throw error;
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
    showEmpty(gettext('The data did not load. Reload the page to try again.'));
    card.classList.remove('is-loading');
    return;
  }
  card.classList.remove('is-loading');
  state.data = data;
  seriesLabel.textContent = `· ${data.label}`;
  seriesNote.textContent = data.note;
  seriesNote.hidden = !data.note;
  seriesLabel.hidden = metrics[state.metric].series.length < 2 || data.label === metrics[state.metric].title;
  drawSource(data.source);
  if (!data.points.length) {
    showEmpty(interpolate(gettext('No data for %s on this measure yet.'), [data.country]));
    return;
  }
  empty.hidden = true;
  card.classList.remove('is-empty');
  state.window = fitWindow(state.window);
  chart.render(data, currentRange());
  drawSlicer();
  drawTable(data);
  await drawLists();
}

// No data: the message alone. The slider, the lists and the table belong to a measure with data, so they hide too.
function showEmpty(message) {
  empty.textContent = message;
  empty.hidden = false;
  card.classList.add('is-empty');
  chart.clear();
  clearTimeout(listTimer);
  listRequest += 1;  // a list request still on its way belongs to the last measure
  state.lists = null;
  list.replaceChildren();
  rankingList.replaceChildren();
  listNote.hidden = true;
  table.replaceChildren();
}

// ---------- The window of years ----------
function fullRange() {
  return [state.data.points[0][0], state.data.points.at(-1)[0]];
}

function currentRange() {
  return state.window || fullRange();
}

// A window inside this series' years, or null when it covers them all (or no longer makes sense).
function fitWindow(window) {
  if (!window) return null;
  const [first, last] = fullRange();
  const from = Math.max(first, Math.min(window[0], window[1]));
  const to = Math.min(last, Math.max(window[0], window[1]));
  if (from >= to || (from === first && to === last)) return null;
  return [from, to];
}

// A presidency's years: from the year before its first year to its last, inside the data.
function rangeOf(presidency) {
  return [presidency.spans[0].from, presidency.spans.at(-1).to];
}

// Sets the window: the chart zooms at once; the address and the lists follow once the slider settles.
// Safari throws when a page rewrites its address too often, so a drag must not do it on every step.
let listTimer = 0;
function setWindow(window, { lists = 'later' } = {}) {
  state.window = fitWindow(window);
  chart.zoomTo(currentRange());
  drawSlicer();
  drawTable(state.data);
  clearTimeout(listTimer);
  const settle = () => {
    syncUrl();
    drawLists();
  };
  if (lists === 'now') settle();
  else listTimer = setTimeout(settle, LIST_DELAY);
}

function drawSlicer() {
  const [first, last] = fullRange();
  const [from, to] = currentRange();
  for (const input of [slicer.from, slicer.to]) {
    input.min = first;
    input.max = last;
  }
  slicer.from.value = from;
  slicer.to.value = to;
  slicer.fromLabel.textContent = from;
  slicer.toLabel.textContent = to;
  const share = (year) => `${((year - first) / Math.max(last - first, 1)) * 100}%`;
  slicer.track.style.setProperty('--from', share(from));
  slicer.track.style.setProperty('--to', share(to));
}

// The lists ask for the window's changes; a newer request wins over one still on its way.
let listRequest = 0;
async function drawLists() {
  const request = ++listRequest;
  let lists;
  try {
    lists = state.window ? await load(state.metric, state.field, state.window) : state.data;
  } catch (error) {
    return;
  }
  if (request !== listRequest || lists.field !== state.data.field) return;
  state.lists = lists;
  drawPresidencies(lists);
  drawRanking(lists);
}

// ---------- Text around the chart ----------
function drawHead() {
  const metric = metrics[state.metric];
  title.textContent = metric.title;
  summary.textContent = metric.summary;
  seriesLabel.hidden = metric.series.length < 2;
  metricLink.href = metric.url;
  canvas.setAttribute('aria-label', interpolate(gettext('%(title)s in %(name)s over time, coloured by the leader in office. The list below gives the change during each term.'),
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
  markOverflow(seriesTabs);
  for (const tab of metricTabs) {
    if (tab.dataset.metric === state.metric) tab.setAttribute('aria-current', 'page');
    else tab.removeAttribute('aria-current');
  }
  const panel = panels.find((p) => p.querySelector(`[data-metric="${state.metric}"]`));
  showGroup(panel?.dataset.groupPanel);
  document.title = `${config.pageTitle}: ${metric.title} · Data Mechanics`;
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

// ---------- The presidents with data, as a timeline from today back. Pressing one sets the window to its years ----------
function drawPresidencies(data) {
  const rows = timelineRows(data);
  const scale = barScale(rows.map((row) => row.presidency.summary.amount));
  list.replaceChildren(...rows.map(({ index, presidency: p, logos, color, years, partyNames }) => {
    const s = p.summary;
    const bar = scale.bar(s.amount);
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `term-row${p.current ? ' is-current' : ''}`;
    button.dataset.index = index;
    button.setAttribute('aria-pressed', 'false');
    button.style.setProperty('--party', color);
    button.title = p.role ? `${p.leader}, ${p.role}` : p.leader;
    button.setAttribute('aria-label', `${interpolate(gettext('%(years)s, %(name)s, %(parties)s: from %(start)s to %(end)s.'),
      { years, name: p.leader, parties: partyNames, start: s.startLabel, end: s.endLabel }, true)} ${trendSaid(s)}`);
    const status = p.current ? ` · ${escapeHtml(gettext('In office'))}` : '';
    button.innerHTML = `<span class="term-row__years">${years}</span><span class="term-row__rail"></span>`
      + `<span class="term-row__logos">${logos.map(logoHtml).join('')}</span>`
      + `<span class="term-row__who"><strong>${escapeHtml(p.shortName)}</strong>`
      + `<span><span class="term-row__when">${years} · </span>${escapeHtml(partyNames)}${status}</span></span>`
      + `<span class="term-row__values">${escapeHtml(valueRange(s))}</span>`
      + `<span class="term-row__bar" style="--axis: ${(scale.axis * 100).toFixed(2)}%" aria-hidden="true">`
      + `<i class="term-row__fill term-row__fill--${toneOf(s)}" style="left: ${(bar.from * 100).toFixed(2)}%; width: ${(bar.width * 100).toFixed(2)}%"></i></span>`
      + `${trendHtml(s)}`;
    const item = document.createElement('li');
    item.append(button);
    return item;
  }));
  const note = omittedNote(data);
  listNote.hidden = !note;
  listNote.textContent = note;
  markActive();
}

// ---------- The rankings: the changes added up by party or by president, best first ----------
function drawRanking(data) {
  if (state.view === 'timeline') return;
  const rows = groupRows(data, state.view);
  const scale = barScale(rows.map((row) => row.perYear.amount));
  rankingList.replaceChildren(...rows.map((row) => {
    const bar = scale.bar(row.perYear.amount);
    const item = document.createElement('li');
    item.className = 'group-row';
    item.title = row.title;
    item.innerHTML = `<span class="group-row__rank">${row.rank}</span>`
      + `<span class="term-row__logos">${row.logos.map(logoHtml).join('')}</span>`
      + `<span class="group-row__who"><span class="group-row__name"><strong>${escapeHtml(row.name)}</strong>`
      + `${row.aside ? ` <em>${escapeHtml(row.aside)}</em>` : ''}</span>${row.sub ? `<span>${escapeHtml(row.sub)}</span>` : ''}</span>`
      + `<span class="term-row__bar" style="--axis: ${(scale.axis * 100).toFixed(2)}%" aria-hidden="true">`
      + `<i class="term-row__fill term-row__fill--${toneOf(row.perYear)}" style="left: ${(bar.from * 100).toFixed(2)}%; width: ${(bar.width * 100).toFixed(2)}%"></i></span>`
      + `<span class="group-row__change"><span class="visually-hidden">${escapeHtml(gettext('Per year'))}: </span>${trendHtml(row.perYear)}</span>`
      + `<span class="group-row__change"><span class="visually-hidden">${escapeHtml(gettext('Total'))}: </span>${trendHtml(row.total)}</span>`;
    return item;
  }));
}

function showView(view) {
  state.view = view;
  for (const button of viewButtons) button.setAttribute('aria-pressed', String(button.dataset.view === view));
  list.hidden = view !== 'timeline';
  ranking.hidden = view === 'timeline';
  if (state.lists) drawRanking(state.lists);
  syncUrl();
}

function markActive() {
  for (const button of list.querySelectorAll('button[data-index]')) {
    button.setAttribute('aria-pressed', String(Number(button.dataset.index) === state.active));
  }
}

function drawTable(data) {
  const rule = units[data.unit];
  const [from, to] = currentRange();
  const owner = (year) => data.presidencies.flatMap((p) => p.spans.map((s) => ({ p, s })))
    .find(({ s }) => s.from < year && year <= s.to);
  const rows = data.points.filter(([year]) => year >= from && year <= to).reverse().map(([year, value]) => {
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
  if (state.view !== 'timeline') next.set('view', state.view);
  if (state.window) {
    next.set('from', state.window[0]);
    next.set('to', state.window[1]);
  }
  history.replaceState(null, '', `${window.location.pathname}?${next}`);
}

function select(metric, field) {
  state.metric = metric;
  state.field = field || metrics[metric].series[0].field;
  state.active = null;
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
  if (state.active === index) {
    state.active = null;
    setWindow(state.beforeActive, { lists: 'now' });
  } else {
    if (state.active === null) state.beforeActive = state.window;
    state.active = index;
    setWindow(rangeOf(state.data.presidencies[index]), { lists: 'now' });
  }
  markActive();
});

// The slider's two handles never cross: moving one past the other stops at the other.
for (const [input, other, side] of [[slicer.from, slicer.to, 0], [slicer.to, slicer.from, 1]]) {
  input.addEventListener('input', () => {
    if (!state.data) return;
    const value = Number(input.value);
    const bound = Number(other.value);
    const year = side === 0 ? Math.min(value, bound - 1) : Math.max(value, bound + 1);
    state.active = null;
    markActive();
    setWindow(side === 0 ? [year, bound] : [bound, year]);
  });
}

// A tab strip that does not fit fades at each edge where more tabs hide.
// The category tabs also get arrows: they hide their scrollbar, so a mouse has no other way to reach the last ones.
// A strip is measured again once the web font is in: the narrower fallback font can make every tab seem to fit.
const cats = document.querySelector('.pol-cats');
const catArrows = [...document.querySelectorAll('[data-cats-scroll]')];
function markOverflow(strip) {
  const before = strip.scrollLeft > 1;
  const after = strip.scrollLeft + strip.clientWidth < strip.scrollWidth - 1;
  strip.classList.toggle('is-scrolled', before);
  strip.classList.toggle('is-overflowing', after);
  if (strip === cats) [catArrows[0].hidden, catArrows[1].hidden] = [!before, !after];
}
for (const strip of [cats, seriesTabs]) {
  strip.addEventListener('scroll', () => markOverflow(strip), { passive: true });
  new ResizeObserver(() => markOverflow(strip)).observe(strip);
  document.fonts?.ready.then(() => markOverflow(strip));
}
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
for (const arrow of catArrows) {
  arrow.addEventListener('click', () => cats.scrollBy({
    left: Number(arrow.dataset.catsScroll) * cats.clientWidth * 0.7,
    behavior: reduceMotion.matches ? 'auto' : 'smooth',
  }));
}
// A page that opens on a category past the edge (a link to Society, say) scrolls it into view.
const openCat = cats.querySelector('[aria-current="true"]');
if (openCat && openCat.offsetLeft + openCat.offsetWidth > cats.clientWidth) {
  cats.scrollLeft = openCat.offsetLeft - (cats.clientWidth - openCat.offsetWidth) / 2;
}

// ---------- Save as image: the chart, and the timeline on as many images as it takes ----------
const clean = (element) => element?.textContent.replace(/\s+/g, ' ').trim();

// The images name the data's source; the presidents' data and the logos are credited on the page,
// except a logo whose licence asks for credit wherever it is shown (lib/timeline.js, logoCredits).
function imageText() {
  const metric = metrics[state.metric];
  const label = state.data.label === metric.title ? '' : ` · ${state.data.label}`;
  const range = currentRange();
  const inView = timelineRows(state.data).filter(({ presidency: p }) => p.spans.some((span) => span.to >= range[0] && span.from <= range[1]));
  return {
    title: metric.title,
    subtitle: `${config.subtitle}${label}`,
    sources: [clean(source), logoCredits(inView)],
  };
}

bindSaveButton(card.querySelector('[data-save-image]'), () => state.data?.points.length && saveChartImage({
  ...imageText(),
  filename: imageName(config.countryName, state.metric, state.field),
  ...termImageParts(state.data, currentRange(), units),
}));

bindSaveButton(card.querySelector('[data-save-timeline]'), () => {
  if (!state.lists?.points.length) return null;
  const { title, subtitle } = imageText();
  const view = viewButtons.find((button) => button.dataset.view === state.view);
  const years = state.window ? ` · ${state.window[0]}–${state.window[1]}` : '';
  return saveTimelineImages({
    title,
    subtitle: `${subtitle}${state.view === 'timeline' ? '' : ` · ${view.textContent.trim()}`}${years}`,
    source: clean(source),
    data: state.lists,
    view: state.view,
    nameParts: [config.countryName, state.metric, state.field, 'leaders'],
  });
});

for (const button of viewButtons) button.addEventListener('click', () => showView(button.dataset.view));

drawHead();
showView(state.view);
draw();
