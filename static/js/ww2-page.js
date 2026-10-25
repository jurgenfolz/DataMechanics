// The World War II page: casualties by country (a column chart with a country picker and the parts to show), the
// battle map with the war's timeline under it, and the battles one by one. The casualties chart and the map save as
// Instagram images. The chart's state (countries, parts) lives in the URL so a view can be shared.
// gettext and interpolate are Django's, from the translation catalog base.html loads.
import { SCALE, bindSaveButton, handOver, imageFrame, imageName, imageWell, saveChartImage } from './lib/chart-image.js';
import { createBattleList } from './lib/battle-list.js';
import { casualtiesImageParts, createCasualtiesChart } from './lib/casualties-chart.js';
import { createPicker } from './lib/picker.js';
import { createWarMap, prepareBattles, viewAspect } from './lib/war-map.js';
import { createWarTimeline } from './lib/war-timeline.js';
import { FONT, INK_2, SIDE_COLORS, formatDay, fromDay, prepareStates, toDay } from './lib/ww2.js';

const config = JSON.parse(document.getElementById('ww2-config').textContent);
const { units } = config;
const first = toDay(config.first);
const last = toDay(config.last);
const states = prepareStates(config.states, last);

function sourceText(source) {
  return source ? `${gettext('Source:')} ${source.name} · ${interpolate(gettext('fetched %s'), [source.fetched])}` : '';
}

// ---------- Casualties by country ----------
const casualtiesCard = document.querySelector('[data-casualties]');
const keys = casualtiesCard.querySelector('[data-keys]');
const empty = casualtiesCard.querySelector('[data-casualties-empty]');
const MAX_COUNTRIES = 12;
// The main belligerents open the chart.
const MAIN_COUNTRIES = ['su', 'cn', 'de', 'pl', 'jp', 'us', 'gb', 'fr', 'it'];
const DEFAULT_COUNTRIES = MAIN_COUNTRIES.filter((code) => config.deaths.some((row) => row.code === code && row.total[0]));

const params = new URLSearchParams(window.location.search);
const state = {
  countries: (params.get('countries') || '').split(',').filter((code) => config.deaths.some((row) => row.code === code)),
  show: { soldiers: params.get('show') !== 'civilians', civilians: params.get('show') !== 'soldiers' },
};
if (!state.countries.length) state.countries = DEFAULT_COUNTRIES;

const casualties = createCasualtiesChart(casualtiesCard.querySelector('[data-casualties-chart]'), { units });
const picker = createPicker(casualtiesCard.querySelector('[data-picker]'), {
  max: MAX_COUNTRIES,
  onToggle: (code) => {
    state.countries = state.countries.includes(code) ? state.countries.filter((c) => c !== code) : [...state.countries, code];
    drawCasualties();
  },
});
picker.setOptions(config.deaths.map((row) => ({ id: row.code, name: row.name, image: row.flag })));

function drawCasualties() {
  const shown = casualties.render(config.deaths, state.countries, state.show);
  empty.hidden = shown.length > 0;
  picker.setSelected(state.countries);
  drawKeys(shown);
  syncUrl();
}

function drawKeys(shown) {
  keys.replaceChildren(...state.countries.map((code) => {
    const row = config.deaths.find((r) => r.code === code);
    const key = document.createElement('span');
    key.className = 'series-key';
    key.setAttribute('role', 'listitem');
    const flag = document.createElement('img');
    flag.className = 'flag';
    flag.src = row.flag;
    flag.alt = '';
    const name = document.createElement('span');
    name.textContent = shown.includes(code) ? row.name : interpolate(gettext('%s (no data)'), [row.name]);
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.setAttribute('aria-label', interpolate(gettext('Remove %s'), [row.name]));
    remove.innerHTML = '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M1 1l8 8M9 1l-8 8" stroke="currentColor" stroke-width="1.6"/></svg>';
    remove.addEventListener('click', () => {
      state.countries = state.countries.filter((c) => c !== code);
      drawCasualties();
    });
    key.append(flag, name, remove);
    return key;
  }));
}

for (const button of casualtiesCard.querySelectorAll('[data-part]')) {
  button.addEventListener('click', () => {
    const part = button.dataset.part;
    const other = part === 'soldiers' ? 'civilians' : 'soldiers';
    // One part stays on: hiding the last one would leave nothing to show.
    if (state.show[part] && !state.show[other]) return;
    state.show[part] = !state.show[part];
    button.setAttribute('aria-pressed', String(state.show[part]));
    drawCasualties();
  });
}

function syncUrl() {
  const next = new URLSearchParams(window.location.search);
  const sameAsDefault = state.countries.length === DEFAULT_COUNTRIES.length && state.countries.every((c, i) => c === DEFAULT_COUNTRIES[i]);
  if (sameAsDefault) next.delete('countries');
  else next.set('countries', state.countries.join(','));
  if (state.show.soldiers && state.show.civilians) next.delete('show');
  else next.set('show', state.show.soldiers ? 'soldiers' : 'civilians');
  const query = next.toString();
  window.history.replaceState(null, '', `${window.location.pathname}${query ? `?${query}` : ''}${window.location.hash}`);
}

drawCasualties();

bindSaveButton(casualtiesCard.querySelector('[data-save-image]'), () => saveChartImage({
  title: gettext('World War II: casualties by country'),
  subtitle: state.show.soldiers && state.show.civilians ? gettext('Deaths in the war, soldiers and civilians, lowest to highest estimate.')
    : state.show.soldiers ? gettext('Military deaths, lowest to highest estimate.') : gettext('Civilian deaths, lowest to highest estimate.'),
  sources: [sourceText(config.sources.deaths)],
  filename: imageName('world-war-ii', 'casualties'),
  ...casualtiesImageParts(config.deaths, state.countries, state.show, units),
}));

// ---------- Battles and timeline ----------
const warCard = document.querySelector('[data-war]');
const battles = prepareBattles(config.battles);
const events = config.events.map((event) => ({ ...event, day: toDay(event.date) }));
const dateLabel = warCard.querySelector('[data-war-date]');
const caption = warCard.querySelector('[data-war-caption]');
let view = 'world';
let current = { day: last, whole: true };

let timeline = null;
let battleList = null;
const map = createWarMap(warCard.querySelector('[data-war-map]'), {
  states,
  battles,
  units,
  onHover: (battle) => { timeline?.light(battle); battleList?.light(battle); },
  onPress: (battle) => { if (battle) timeline?.setDay(battle.startDay); },
});
fetch(config.bordersUrl).then((response) => response.json()).then((geojson) => map.setBorders(geojson));

// While the war plays, the latest event of the past seven weeks names itself over the map.
let captionEvent = null;
function showCaption(day, whole) {
  const event = whole ? null : events.findLast((e) => e.day <= day && day - e.day < 50 && (view === 'world' || e.region === view || e.region === 'world'));
  if (event === captionEvent) return;
  captionEvent = event;
  caption.classList.toggle('is-shown', Boolean(event));
  if (event) caption.innerHTML = `<time>${formatDay(event.day)}</time>${event.name}`;
}

timeline = createWarTimeline(warCard.querySelector('[data-war-timeline]'), {
  battles,
  first,
  last,
  theatres: config.theatres,
  onChange(day, whole) {
    current = { day, whole };
    map.setDay(day, whole);
    dateLabel.textContent = whole ? `${formatDay(first, 'month')} – ${formatDay(last, 'month')}` : formatDay(day);
    dateLabel.classList.toggle('is-whole', whole);
    showCaption(day, whole);
  },
  onHoverBattle: (battle) => { map.light(battle); battleList?.light(battle); },
});

for (const button of warCard.querySelectorAll('[data-war-views] button')) {
  button.addEventListener('click', () => {
    view = button.dataset.view;
    for (const other of warCard.querySelectorAll('[data-war-views] button')) {
      other.setAttribute('aria-pressed', String(other === button));
    }
    map.setView(view);
    timeline.setRegion(view);
    battleList.setRegion(view);
  });
}

/** A row of keys under a saved image's well: a swatch and a label each. */
function paintKeys(ctx, x, y, keysToPaint) {
  ctx.save();
  ctx.font = `600 17px ${FONT}`;
  ctx.textBaseline = 'middle';
  for (const { color, label } of keysToPaint) {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.roundRect(x, y - 7, 16, 14, 3);
    ctx.fill();
    ctx.fillStyle = INK_2;
    ctx.fillText(label, x + 24, y);
    x += 24 + ctx.measureText(label).width + 30;
  }
  ctx.restore();
}

bindSaveButton(warCard.querySelector('[data-war-save]'), async () => {
  const title = gettext('World War II: the battles');
  const subtitle = current.whole ? gettext('Every battle on the map, 1937 to 1945. Circles: casualties of both sides.')
    : interpolate(gettext('The war on %s. Circles: casualties of both sides.'), [formatDay(current.day)]);
  const { canvas, ctx, top, bottom } = await imageFrame({
    title,
    subtitle,
    sources: [sourceText(config.sources.battles), sourceText(config.sources.borders)],
  });
  const height = Math.min(bottom - top - 44, (canvas.width - 104) / viewAspect(view) + 60);
  const { well, inner } = imageWell(ctx, top, height);
  ctx.save();
  ctx.translate(inner.x, inner.y);
  ctx.scale(SCALE, SCALE);
  map.paintInto(ctx, inner.w / SCALE, inner.h / SCALE, 1);
  ctx.restore();
  paintKeys(ctx, well.x + 4, well.y + well.h + 26, [
    { color: SIDE_COLORS.allies, label: gettext('Allies') },
    { color: SIDE_COLORS.axis, label: gettext('Axis') },
    { color: '#2a2c2f', label: gettext('Not at war') },
  ]);
  const day = current.whole ? '' : fromDay(current.day).toISOString().slice(0, 10);
  await handOver([{ canvas, filename: imageName('world-war-ii', 'battles', day) }], title);
});

// ---------- Battle by battle ----------
battleList = createBattleList(document.querySelector('[data-battle-list]'), {
  battles,
  events,
  states,
  units,
  onPick(battle) {
    if (!battle) {
      map.show(null);
      return;
    }
    timeline.setDay(battle.startDay);
    warCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    // The map's card opens over the dot once the scroll has settled and the day's map is drawn.
    setTimeout(() => map.show(battle), 500);
  },
});
