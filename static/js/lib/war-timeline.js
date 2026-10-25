// The war's timeline under the map: a lane per theatre with a bar for each battle, and a gold line for the day the map
// shows. Drag the line or use the arrow keys to move it; play runs the war through. The region tabs pick the lanes.
// gettext is Django's, from the translation catalog base.html loads.
import { escapeHtml } from './format.js';
import { SIDE_COLORS, formatDay, fromDay, placeTip, toDay } from './ww2.js';

const NS = 'http://www.w3.org/2000/svg';
const THEATRES = ['west', 'east', 'mediterranean', 'asia', 'pacific'];
export const REGION_THEATRES = { world: THEATRES, europe: ['west', 'east', 'mediterranean'], asia: ['asia', 'pacific'] };
const GUTTER = 138;  // room for the lanes' names; on phones they sit over the lanes instead
const TOP = 10;
const PITCH = 9;     // one row of bars
const BAR = 6;
const LANE_GAP = 8;
const AXIS_H = 24;
// Playing runs the whole war (about 2,980 days) in some 36 seconds.
const DAYS_PER_SECOND = 82;
const WINNER_COLORS = { allies: SIDE_COLORS.allies, axis: SIDE_COLORS.axis, none: '#8b8f94' };

function svg(tag, attrs, parent) {
  const element = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, value);
  parent?.append(element);
  return element;
}

/** Bars that overlap in time go on separate rows of their lane. */
function rows(battles) {
  const ends = [];
  return battles.map((battle) => {
    let row = ends.findIndex((end) => end < battle.startDay - 6);
    if (row < 0) row = ends.length;
    ends[row] = battle.endDay;
    return row;
  });
}

export function createWarTimeline(root, { battles, first, last, theatres, onChange, onHoverBattle }) {
  const track = root.querySelector('[data-war-track]');
  const play = root.querySelector('[data-war-play]');
  const tip = root.querySelector('[data-war-timeline-tip]');
  const span = last - first;
  let day = last;
  let whole = true;
  let playing = false;
  let frame = 0;
  let lastTime = 0;
  let region = 'world';

  // The lanes, top to bottom: one per theatre of the region, each as tall as its rows of bars.
  // Without a gutter (on phones) each lane gets a row of its own for its name, above its bars.
  const lanes = [];
  let height = 0;
  function layoutLanes(labelRow) {
    lanes.length = 0;
    let y = TOP;
    for (const theatre of REGION_THEATRES[region]) {
      const own = battles.filter((battle) => battle.theatre === theatre).sort((a, b) => a.startDay - b.startDay);
      const rowOf = rows(own);
      const laneHeight = (Math.max(...rowOf, 0) + 1) * PITCH;
      lanes.push({ theatre, top: y + LANE_GAP / 2 + labelRow, height: laneHeight, battles: own, rowOf });
      y += laneHeight + LANE_GAP + labelRow;
    }
    height = y + AXIS_H;
  }

  const chart = svg('svg', { class: 'war-timeline__svg', 'aria-hidden': 'true' }, track);
  const head = document.createElement('div');
  head.className = 'war-timeline__head';
  track.append(head);

  let width = 0;
  let gutter = GUTTER;
  const xOf = (d) => gutter + ((d - first) / span) * (width - gutter - 12);
  const dayOf = (x) => Math.round(first + ((x - gutter) / (width - gutter - 12)) * span);

  const bars = new Map();

  function build() {
    width = track.clientWidth;
    gutter = width < 640 ? 0 : GUTTER;
    const labelRow = gutter ? 0 : 14;
    layoutLanes(labelRow);
    chart.replaceChildren();
    chart.setAttribute('width', width);
    chart.setAttribute('height', height);
    chart.setAttribute('viewBox', `0 0 ${width} ${height}`);
    track.style.height = `${height}px`;

    // Years along the foot, with a faint line for each.
    for (let year = fromDay(first).getUTCFullYear() + 1; year <= fromDay(last).getUTCFullYear(); year += 1) {
      const x = xOf(toDay(`${year}-01-01`));
      svg('line', { x1: x, x2: x, y1: 0, y2: height - AXIS_H + 4, class: 'war-timeline__year-line' }, chart);
      const text = svg('text', { x: x + 4, y: height - 7, class: 'war-timeline__year' }, chart);
      text.textContent = year;
    }

    const label = (text, top) => {
      const element = svg('text', { x: 0, y: top, class: 'war-timeline__lane' }, chart);
      element.textContent = text;
    };
    bars.clear();
    for (const lane of lanes) {
      label(theatres[lane.theatre], labelRow ? lane.top - 4 : lane.top + Math.min(lane.height, PITCH * 2) / 2 + 4);
      const rule = lane.top - LANE_GAP / 2 - labelRow;
      svg('line', { x1: gutter, x2: width - 12, y1: rule, y2: rule, class: 'war-timeline__rule' }, chart);
      lane.battles.forEach((battle, i) => {
        const x = xOf(battle.startDay);
        const bar = svg('rect', {
          x, y: lane.top + lane.rowOf[i] * PITCH + (PITCH - BAR) / 2, width: Math.max(xOf(battle.endDay + 1) - x, 4), height: BAR, rx: 3,
          fill: WINNER_COLORS[battle.winner], class: 'war-timeline__bar',
        }, chart);
        bars.set(bar, battle);
      });
    }
    update();
  }

  function update() {
    head.style.transform = `translateX(${xOf(day)}px)`;
    track.setAttribute('aria-valuetext', formatDay(day));
    for (const [bar, battle] of bars) {
      bar.classList.toggle('is-future', !whole && battle.startDay > day);
      bar.classList.toggle('is-now', !whole && battle.startDay <= day && day <= battle.endDay);
    }
    play.classList.toggle('is-playing', playing);
    play.setAttribute('aria-label', playing ? gettext('Pause') : gettext('Play the war'));
    onChange(day, whole);
  }

  function setDay(next, showWhole = false) {
    day = Math.min(Math.max(Math.round(next), first), last);
    whole = showWhole;
    update();
  }

  function stop() {
    playing = false;
    cancelAnimationFrame(frame);
    frame = 0;
    lastTime = 0;
    update();
  }

  function step(now) {
    const dt = lastTime ? Math.min(now - lastTime, 80) : 16;
    lastTime = now;
    const next = day + (dt / 1000) * DAYS_PER_SECOND;
    if (next >= last) {
      setDay(last, true);
      stop();
      return;
    }
    day = next;
    whole = false;
    head.style.transform = `translateX(${xOf(day)}px)`;
    update();
    frame = requestAnimationFrame(step);
  }

  play.addEventListener('click', () => {
    if (playing) {
      stop();
      return;
    }
    if (whole || day >= last) setDay(first);
    playing = true;
    frame = requestAnimationFrame(step);
  });

  // Dragging: the line follows the pointer anywhere along the track.
  let dragging = false;
  track.addEventListener('pointerdown', (event) => {
    if (playing) stop();
    dragging = true;
    track.setPointerCapture(event.pointerId);
    setDay(dayOf(event.clientX - track.getBoundingClientRect().left));
  });
  track.addEventListener('pointermove', (event) => {
    const box = track.getBoundingClientRect();
    if (dragging) {
      setDay(dayOf(event.clientX - box.left));
      return;
    }
    const bar = event.target.closest?.('.war-timeline__bar');
    const layer = tip.parentElement.getBoundingClientRect();
    if (bar && bars.has(bar)) {
      const battle = bars.get(bar);
      onHoverBattle(battle);
      placeTip(tip, `<div class="tip"><div class="tip__title">${escapeHtml(battle.name)}</div>`
        + `<div class="tip__muted">${escapeHtml(formatDay(battle.startDay))} – ${escapeHtml(formatDay(battle.endDay))}</div></div>`,
      event.clientX - layer.left, event.clientY - layer.top);
    } else {
      onHoverBattle(null);
      tip.hidden = true;
    }
  });
  const release = () => { dragging = false; };
  track.addEventListener('pointerup', release);
  track.addEventListener('pointercancel', release);
  track.addEventListener('pointerleave', () => {
    tip.hidden = true;
    onHoverBattle(null);
  });

  track.addEventListener('keydown', (event) => {
    const moves = { ArrowLeft: -7, ArrowRight: 7, PageDown: -30, PageUp: 30 };
    if (event.key in moves) setDay(day + moves[event.key]);
    else if (event.key === 'Home') setDay(first);
    else if (event.key === 'End') setDay(last, true);
    else return;
    if (playing) stop();
    event.preventDefault();
  });

  new ResizeObserver(build).observe(track);
  build();

  return {
    get day() { return day; },
    setDay(next) {
      if (playing) stop();
      setDay(next);
    },
    setRegion(next) {
      region = next;
      build();
    },
    light(battle) {
      for (const [bar, b] of bars) bar.classList.toggle('is-lit', b === battle);
    },
  };
}
