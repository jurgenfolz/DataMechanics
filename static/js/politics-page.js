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
import { createCompassView } from './lib/compass-view.js';
import { createCongressView } from './lib/congress-view.js';
import { createReel, FPS } from './lib/reel.js';
import { createYearSlicer, fitWindow as fitInside } from './lib/year-slicer.js';

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
const compareSelect = document.querySelector('[data-compare]');
const compareBox = document.querySelector('[data-compare-select]');
const compareNote = document.querySelector('[data-compare-note]');
const categories = [...document.querySelectorAll('[data-group]')];
const panels = [...document.querySelectorAll('[data-group-panel]')];
const metricTabs = [...document.querySelectorAll('[data-metric]')];

const params = new URLSearchParams(window.location.search);
const urlWindow = [Number(params.get('from')), Number(params.get('to'))];
const state = {
  tab: config.tab,  // 'metric', or the party compass's or Congress's tab
  house: config.house,  // the house of Congress shown on its tab
  metric: config.metric,
  field: config.series,
  view: VIEWS.includes(params.get('view')) ? params.get('view') : 'timeline',
  data: null,  // the series, every year
  lists: null,  // the presidents' changes and rankings inside the window
  window: urlWindow[0] && urlWindow[1] ? urlWindow : null,  // [first year, last year], or null for every year
  compare: config.compare,  // the comparison group (politics/comparison.py): world, brics, g7 or g20, or none
  active: null,  // the pressed president's index, whose years the window shows
  beforeActive: null,  // the window to go back to when the president is pressed again
};

const chart = createTermChart(canvas, { units, slider: false });

const cache = new Map();
function load(metric, field, window = null) {
  const key = [metric, field, state.compare, ...(window || [])].join(':');
  if (!cache.has(key)) {
    const query = new URLSearchParams({ metric, series: field, compare: state.compare, v: config.dataVersion });
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
  drawCompareChoices(data);
  await drawLists();
}

// The groups without values for this series say so, and can't be picked; a total (GDP) compares with none, so the
// dropdown hides. A chosen group without values stays chosen for the next series, and this one shows no comparison.
function drawCompareChoices(data) {
  compareBox.hidden = !data.comparable.length;
  for (const option of compareSelect.options) {
    if (option.value === 'none') continue;
    option.dataset.label ??= option.textContent;
    const comparable = data.comparable.includes(option.value);
    option.disabled = !comparable;
    option.textContent = comparable ? option.dataset.label : interpolate(gettext('%s (no data)'), [option.dataset.label]);
  }
  compareNote.hidden = !data.comparison;
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
  return fitInside(window, fullRange());
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

// Moving a handle sets the window and lets go of a pressed president.
const slicer = createYearSlicer(document.querySelector('[data-year-slicer]'), {
  onChange(window) {
    if (!state.data) return;
    state.active = null;
    markActive();
    setWindow(window);
  },
});

function drawSlicer() {
  slicer.set(fullRange(), currentRange());
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
  if (state.tab === 'metric') showGroup(panel?.dataset.groupPanel);
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
// The comparison group's change over the same years, small and grey under the term's own.
function compareHtml(summary, group) {
  if (!summary.compare) return '';
  return `<span class="term-row__compare"><span>${escapeHtml(group.short)}</span>${trendHtml({ ...summary.compare, good: null })}</span>`;
}

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
      + `<span class="term-row__change">${trendHtml(s)}${compareHtml(s, data.comparison)}</span>`;
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
  if (state.tab !== 'metric') next.set('tab', state.tab);
  if (state.tab === 'congress' && state.house !== config.congress.houses[0].key) next.set('house', state.house);
  // The compass keeps its survey in the address itself (lib/compass-view.js), and Congress its term and view
  // (lib/congress-view.js).
  const kept = new URLSearchParams(window.location.search);
  for (const key of ['survey', 'term', 'by']) if (kept.get(key)) next.set(key, kept.get(key));
  if (state.field !== metrics[state.metric].series[0].field) next.set('series', state.field);
  if (state.view !== 'timeline') next.set('view', state.view);
  if (state.compare !== 'world') next.set('compare', state.compare);
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

// ---------- The tabs before the metrics: the party compass and the seats in Congress ----------
// Each has its own section, which takes the metric chart's place while its tab is open.
const sections = Object.fromEntries([...document.querySelectorAll('[data-section]')].map((element) => [element.dataset.section, element]));
const views = {
  compass: config.compass && createCompassView(sections.compass, config.compass,
    { country: config.countryName, flag: config.flag, title: config.compassTitle }),
  congress: config.congress && createCongressView(sections.congress, config.congress,
    { country: config.countryName, flag: config.flag, title: config.congressTitle }),
};
const houseTabs = [...document.querySelectorAll('[data-house]')];

function openTab(tab) {
  state.tab = tab;
  for (const [key, element] of Object.entries(sections)) element.hidden = key !== tab;
  if (tab === 'metric') {
    showGroup(panels.find((p) => p.querySelector(`[data-metric="${state.metric}"]`))?.dataset.groupPanel);
  } else {
    showGroup(tab);
    if (tab === 'congress') showHouse(state.house);
    else views.compass.show();
  }
  syncUrl();
}

function showHouse(key) {
  state.house = key;
  for (const button of houseTabs) {
    if (button.dataset.house === key) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  }
  views.congress.show(key);
}

for (const button of houseTabs) {
  button.addEventListener('click', (event) => {
    event.preventDefault();
    showHouse(button.dataset.house);
    syncUrl();
  });
}

// ---------- Controls ----------
for (const tab of categories) {
  tab.addEventListener('click', (event) => {
    event.preventDefault();
    if (tab.dataset.tab) {
      openTab(tab.dataset.tab);
      return;
    }
    const panel = panels.find((p) => p.dataset.groupPanel === tab.dataset.group);
    if (state.tab !== 'metric') openTab('metric');
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
  // The measure's label, unless the title already says it ("Human rights index (V-Dem)" holds "Human rights index").
  const label = String(metric.title).includes(state.data.label) ? '' : ` · ${state.data.label}`;
  const range = currentRange();
  const inView = timelineRows(state.data).filter(({ presidency: p }) => p.spans.some((span) => span.to >= range[0] && span.from <= range[1]));
  // "Brazil, president by president, compared with G7 countries".
  const compared = state.data.comparison ? `, ${state.data.comparison.compared}` : '';
  return {
    title: metric.title,
    subtitle: `${config.subtitle}${compared}${label}`,
    sources: [clean(source), logoCredits(inView)],
    flag: config.flag,
  };
}

bindSaveButton(card.querySelector('[data-save-image]'), () => state.data?.points.length && saveChartImage({
  ...imageText(),
  filename: imageName(config.countryName, state.metric, state.field),
  ...termImageParts(state.data, currentRange(), units),
}));

bindSaveButton(card.querySelector('[data-save-timeline]'), () => {
  if (!state.lists?.points.length) return null;
  const { title, subtitle, flag } = imageText();
  const view = viewButtons.find((button) => button.dataset.view === state.view);
  const years = state.window ? ` · ${state.window[0]}–${state.window[1]}` : '';
  return saveTimelineImages({
    title,
    subtitle: `${subtitle}${state.view === 'timeline' ? '' : ` · ${view.textContent.trim()}`}${years}`,
    source: clean(source),
    flag,
    data: state.lists,
    view: state.view,
    nameParts: [config.countryName, state.metric, state.field, 'leaders'],
  });
});

for (const button of viewButtons) button.addEventListener('click', () => showView(button.dataset.view));

// One comparison group at a time, or none: a new choice loads the series and the lists again.
compareSelect.addEventListener('change', () => {
  state.compare = compareSelect.value;
  compareBox.toggleAttribute('data-none', state.compare === 'none');
  syncUrl();
  draw();
});

// ---------- The reel (lib/reel.js): a video for Instagram, or with &format=wide for YouTube and LinkedIn ----------
// ?reel=1 plays it over the page, as large as the window allows; a click pauses it.
// ?reel=record draws nothing until tools/reel.py asks for each frame through window.reel.
// On the compass's tab, the video is the compass's (lib/compass-reel.js); on Congress's, the open house's (lib/congress-reel.js).
async function openReel(mode) {
  const format = params.get('format') === 'wide' ? 'wide' : 'reel';
  if (state.tab === 'compass' || state.tab === 'congress') {
    const reel = await views[state.tab].createReel(format);
    present(reel, reel.filename, mode);
    return;
  }
  const { title, subtitle } = imageText();
  const range = currentRange();
  const leaders = viewButtons.find((button) => button.dataset.view === 'president');
  const reel = await createReel({
    format,
    data: state.lists,
    range,
    units,
    title,
    flag: config.flag,
    subtitle: `${subtitle} · ${range[0]}–${range[1]}`,
    // The metric's summary, and what sets this measure apart when the metric has several (PPP, say).
    explanation: [metrics[state.metric].summary, state.lists.note].filter(Boolean).join(' '),
    rankingTitle: leaders.textContent.trim(),
    source: clean(source),
  });
  present(reel, imageName(config.countryName, state.metric, state.field, `${range[0]}-${range[1]}`, format === 'wide' && 'wide')
    .replace(/\.png$/, '.mp4'), mode);
}

// Shows a video over the page and hands its frames to tools/reel.py through window.reel; `mode` 'record' only does the second.
function present(reel, filename, mode) {
  const stage = document.createElement('div');
  stage.className = 'reel-stage';
  stage.append(reel.canvas);
  document.body.append(stage);
  reel.draw(0);
  window.reel = {
    ready: true,
    fps: FPS,
    frames: reel.frames,
    filename,
    width: reel.canvas.width,
    height: reel.canvas.height,
    frame(n) {
      reel.draw(n);
      return reel.canvas.toDataURL('image/png');
    },
  };
  if (mode === 'record') return;
  let elapsed = 0;
  let last = null;
  let paused = false;
  stage.addEventListener('click', () => { paused = !paused; });
  const play = (now) => {
    if (!paused && last !== null) elapsed += now - last;
    last = now;
    reel.draw(Math.floor((elapsed / 1000) * FPS) % reel.frames);
    requestAnimationFrame(play);
  };
  requestAnimationFrame(play);
}

drawHead();
showView(state.view);
if (state.tab !== 'metric') openTab(state.tab);
draw().then(() => {
  if (params.has('reel') && (state.tab !== 'metric' || state.lists?.points.length)) openReel(params.get('reel'));
});
