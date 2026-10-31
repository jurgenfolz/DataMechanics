// World events on a chart (events/catalog.py, served at events.json): a dashed line on the event's date, with a
// small chip above the plot that holds the kind's icon and the title. A span (a war, a boom) also shades its years.
// The chips sit in rows above the plot, so chips near one another never overlap; the lowest row is nearest the plot.
// The metric pages, Politics and Compare draw them (lib/line-chart.js, term-chart.js, compare-chart.js) and their
// saved images too; the Politics reel pops them in as the line passes them (lib/reel.js, paintEvents).
// The reader picks them with the pages' picker (lib/picker.js); the chosen ones are listed under the chart (eventKeys).
// gettext and interpolate are Django's, from the translation catalog base.html loads.
import { escapeHtml } from './format.js';

// A colour per kind, all from the site's series palette, so each reads on the chart well.
export const KIND_COLORS = {
  conflict: '#e66767',
  disaster: '#d95926',
  economy: '#c98500',
  energy: '#d55181',
  health: '#199e70',
  treaty: '#3987e5',
  politics: '#9085e9',
  technology: '#c9ccd0',
};

// Stroke icons on a 24 px grid, like templates/partials/icon.html: swords, a warning sign, a market line, a bolt,
// a cross, two rings, a landmark, a chip.
export const ICONS = {
  conflict: 'M3.5 3.5L15 15M20.5 3.5L9 15M6 15l3 3M18 15l-3 3M4.5 19.5L8 16M19.5 19.5L16 16',
  disaster: 'M12 3L2 20h20zM12 9.5v4.5M12 17v.5',
  economy: 'M3 17.5l5-6.5 4 4 5-8 4 3.5',
  energy: 'M13 2L4 14h7l-1 8 9-12h-7z',
  health: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 8v8M8 12h8',
  treaty: 'M14.5 12a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0zM20.5 12a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z',
  politics: 'M3 21h18M5 21V10M19 21V10M9.5 21V10M14.5 21V10M2 10l10-6 10 6z',
  technology: 'M7 7h10v10H7zM9 7V4M15 7V4M9 20v-3M15 20v-3M4 9h3M4 15h3M17 9h3M17 15h3',
};

// A chip's sizes in CSS pixels: its height, its padding, the icon, the gap before the title, the title's type and
// the height of a row of chips.
export const CHIP = { h: 20, pad: 5, icon: 12, gap: 5, font: 11, row: 24, radius: 6 };
const ROOM = 6;  // between the lowest row and the plot
const SPACING = 6;  // between two chips in a row
const FONT = 'Archivo, "Helvetica Neue", Arial, sans-serif';
const CARD = '#17191b';
const RULE = '#3a3d41';
const INK_2 = '#b6b9bd';

/** The year an ISO date falls in, as a fraction: 11 September 2001 is 2001.69. */
export function yearOf(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  const start = Date.UTC(y, 0, 1);
  return y + (Date.UTC(y, m - 1, d) - start) / (Date.UTC(y + 1, 0, 1) - start);
}

const loads = new Map();

/** The events at `url`, oldest first, each with `at` (its year as a fraction) and `until` (a span's end, Infinity while it goes on). */
export function loadEvents(url) {
  if (!loads.has(url)) {
    loads.set(url, fetch(url).then((response) => response.json()).then(({ events }) => events.map((event) => ({
      ...event,
      at: yearOf(event.date),
      until: event.end ? yearOf(event.end) : event.ongoing ? Infinity : null,
    }))));
  }
  return loads.get(url);
}

/** The events whose date falls in the years from `from` to `to`, both whole years on the chart. */
export function eventsIn(events, from, to) {
  return events.filter((event) => event.at >= from && event.at <= to);
}

/** The events whose slugs are in `slugs`, in the catalog's order. */
export function pickEvents(events, slugs) {
  const chosen = new Set(slugs);
  return events.filter((event) => chosen.has(event.slug));
}

export function iconSvg(kind, size = 16) {
  return `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.8" `
    + `stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${ICONS[kind]}"/></svg>`;
}

/** The picker's options (lib/picker.js): each event with its icon, its title and its year. */
export function eventOptions(events) {
  return events.map((event) => ({
    id: event.slug, name: event.title, meta: String(event.date.slice(0, 4)), svg: iconSvg(event.kind), color: KIND_COLORS[event.kind],
  }));
}

const language = document.documentElement.lang || 'en';
const dayFormat = new Intl.DateTimeFormat(language, { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
const monthFormat = new Intl.DateTimeFormat(language, { month: 'short', year: 'numeric', timeZone: 'UTC' });
const asDate = (iso) => new Date(`${iso}T00:00:00Z`);

/** When an event happened, as the page writes it: "11 Sep 2001", "Mar 2003 – Jul 2008", or "since Feb 2022". */
export function eventWhen(event) {
  if (event.ongoing) return interpolate(gettext('since %s'), [monthFormat.format(asDate(event.date))]);
  if (event.end) return `${monthFormat.format(asDate(event.date))} – ${monthFormat.format(asDate(event.end))}`;
  return dayFormat.format(asDate(event.date));
}

// ---------- Layout ----------
let measurer = null;
function textWidth(text, scale = 1) {
  measurer ??= document.createElement('canvas').getContext('2d');
  measurer.font = `600 ${CHIP.font * scale}px ${FONT}`;
  return measurer.measureText(text).width;
}

/**
 * Where each event's chip goes: `xOf(at)` gives the pixel of a year, `left` and `right` bound the chips,
 * `narrow` keeps the icon alone, `scale` draws everything that many times its size (the saved images and reels).
 * Returns { items, rows }: each item has its event, its line's `x`, its chip's `left` and `w`, and its `row`
 * (0 nearest the plot). Rows are filled from the earliest event on: a chip takes the lowest row with room.
 */
export function layoutEvents(events, xOf, { left, right, narrow = false, scale = 1 }) {
  const s = (v) => v * scale;
  const ends = [];
  const items = [...events].sort((a, b) => a.at - b.at).map((event) => {
    const x = xOf(event.at);
    const w = s(2 * CHIP.pad + CHIP.icon) + (narrow ? 0 : s(CHIP.gap) + textWidth(event.title, scale));
    const chipLeft = Math.max(left, Math.min(x - s(CHIP.pad + CHIP.icon / 2), right - w));
    let row = ends.findIndex((end) => end + s(SPACING) <= chipLeft);
    if (row < 0) row = ends.length;
    ends[row] = chipLeft + w;
    return { event, x, left: chipLeft, w, row };
  });
  return { items, rows: ends.length };
}

/** The room the chips need above the plot, in CSS pixels, for `rows` rows. */
export function eventRoom(rows) {
  return rows ? rows * CHIP.row + ROOM : 0;
}

/** A chip's top edge for its row, under a plot whose top is `plotTop`. */
export function chipTop(plotTop, row, scale = 1) {
  return plotTop - scale * (ROOM + (row + 1) * CHIP.row - (CHIP.row - CHIP.h) / 2);
}

/** The chips' boxes ({ left, top, right, bottom }) in CSS pixels, for anything that must keep off them. */
export function chipBoxes(laid, plotTop) {
  return laid.items.map((item) => {
    const top = chipTop(plotTop, item.row);
    return { left: item.left, top, right: item.left + item.w, bottom: top + CHIP.h };
  });
}

/**
 * The ECharts series that draws the events: a custom series, one item an event, outside the hover line's reach.
 * `toAxis(at)` turns a year into the x axis's own value (an index on a category axis), and `laid` is layoutEvents'
 * result for the same events, whose rows the chips keep; their x comes from the chart itself.
 */
export function eventSeries(laid, toAxis, { narrow = false } = {}) {
  const items = laid.items;
  return {
    id: 'events',
    type: 'custom',
    z: 4,
    clip: false,
    tooltip: { show: false },
    data: items.map((item) => ({ value: [toAxis(item.event.at), null], name: item.event.slug })),
    renderItem(params, api) {
      const item = items[params.dataIndex];
      const plot = params.coordSys;
      const plotRight = plot.x + plot.width;
      const plotBottom = plot.y + plot.height;
      // A year's pixel: the axis is linear, so a date between two years lies between their pixels.
      const pixel = (at) => {
        const v = toAxis(at);
        const whole = Math.floor(v);
        const [x0] = api.coord([whole, 0]);
        const [x1] = api.coord([whole + 1, 0]);
        return x0 + (x1 - x0) * (v - whole);
      };
      const x = pixel(item.event.at);
      const color = KIND_COLORS[item.event.kind];
      const left = Math.max(plot.x, Math.min(x - CHIP.pad - CHIP.icon / 2, plotRight - item.w));
      const top = chipTop(plot.y, item.row);
      const children = [];
      if (item.event.until !== null) {
        const until = item.event.until === Infinity ? plotRight : Math.min(pixel(item.event.until), plotRight);
        children.push({ type: 'rect', silent: true, shape: { x, y: plot.y, width: Math.max(0, until - x), height: plot.height },
          style: { fill: color, opacity: 0.07 } });
      }
      children.push({ type: 'line', silent: true, shape: { x1: x, y1: top + CHIP.h, x2: x, y2: plotBottom },
        style: { stroke: color, lineWidth: 1, lineDash: [3, 3], opacity: 0.6 } });
      children.push({ type: 'rect', shape: { x: left, y: top, width: item.w, height: CHIP.h, r: CHIP.radius },
        style: { fill: CARD, stroke: RULE, lineWidth: 1 }, emphasis: { style: { stroke: color } } });
      // The icon sits in a group placed by its transform. ECharts keeps a path built from `pathData` and does not
      // move it again through its shape, so a path placed by `shape.x` stays put when the window changes.
      children.push({ type: 'group', silent: true, x: left + CHIP.pad, y: top + (CHIP.h - CHIP.icon) / 2, children: [{
        type: 'path', silent: true,
        shape: { pathData: ICONS[item.event.kind], x: 0, y: 0, width: CHIP.icon, height: CHIP.icon, layout: 'cover' },
        style: { fill: 'none', stroke: color, lineWidth: 3, lineCap: 'round', lineJoin: 'round' },
      }] });
      if (!narrow) {
        children.push({ type: 'text', silent: true, style: {
          text: item.event.title, x: left + CHIP.pad + CHIP.icon + CHIP.gap, y: top + CHIP.h / 2, verticalAlign: 'middle',
          fill: INK_2, font: `600 ${CHIP.font}px ${FONT}`,
        } });
      }
      return { type: 'group', children };
    },
  };
}

/**
 * A card on hover over an event's chip: the title with its icon, when it happened, and what it was.
 * `well` is the element the chart sits in (position: relative); the card is placed inside it.
 */
export function bindEventTips(chart, well, laid) {
  let tip = well.querySelector('.chart-tip');
  if (!tip) {
    tip = document.createElement('div');
    tip.className = 'chart-tip';
    tip.hidden = true;
    well.append(tip);
  }
  chart.on('mouseover', { seriesId: 'events' }, (params) => {
    const event = laid().items[params.dataIndex]?.event;
    if (!event) return;
    tip.innerHTML = `<div class="tip"><div class="tip__head"><span class="event-icon" style="color:${KIND_COLORS[event.kind]}">${iconSvg(event.kind)}</span>`
      + `${escapeHtml(event.title)}</div><div class="tip__muted">${escapeHtml(eventWhen(event))} · ${escapeHtml(event.kindLabel)}</div>`
      + `<p>${escapeHtml(event.summary)}</p></div>`;
    tip.hidden = false;
    const x = Math.max(8, Math.min(params.event.offsetX - tip.offsetWidth / 2, well.clientWidth - tip.offsetWidth - 8));
    tip.style.transform = `translate(${Math.round(x)}px, ${Math.round(params.event.offsetY + 16)}px)`;
  });
  chart.on('mouseout', { seriesId: 'events' }, () => { tip.hidden = true; });
}

/** The chosen events listed under the chart, each with its icon, its title (a link to Wikipedia) and its date, and a button to remove it. */
export function renderEventKeys(container, events, onRemove) {
  container.hidden = !events.length;
  container.replaceChildren(...events.map((event) => {
    const key = document.createElement('span');
    key.className = 'event-key';
    key.setAttribute('role', 'listitem');
    key.innerHTML = `<span class="event-icon" style="color:${KIND_COLORS[event.kind]}">${iconSvg(event.kind, 14)}</span>`
      + `<a href="${escapeHtml(event.wiki)}" rel="noopener" target="_blank" title="${escapeHtml(event.summary)}">${escapeHtml(event.title)}</a>`
      + `<span class="event-key__when">${escapeHtml(eventWhen(event))}</span>`;
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.setAttribute('aria-label', interpolate(gettext('Remove %s'), [event.title]));
    remove.innerHTML = '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M1 1l8 8M9 1l-8 8" stroke="currentColor" stroke-width="1.6"/></svg>';
    remove.addEventListener('click', () => onRemove(event.slug));
    key.append(remove);
    return key;
  }));
}

const paths = new Map();
const pathOf = (kind) => {
  if (!paths.has(kind)) paths.set(kind, new Path2D(ICONS[kind]));
  return paths.get(kind);
};

// ---------- The saved images' legend (lib/chart-image.js, `below`) ----------
// The chips on an image carry the icon alone; the events are named under the chart, two to a row:
// the icon in its colour, the title and the date.
const LEGEND_ROW = 36;
const LEGEND_COLUMNS = 2;

/** The room the events' legend needs under the chart, in image pixels. */
export function eventLegendHeight(events) {
  return events.length ? Math.ceil(events.length / LEGEND_COLUMNS) * LEGEND_ROW + 8 : 0;
}

/** Paints the legend in `box` ({ x, y, w }); returns its foot. */
export function paintEventLegend(ctx, box, events) {
  const columnW = box.w / LEGEND_COLUMNS;
  ctx.save();
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'left';
  events.forEach((event, n) => {
    const x = box.x + (n % LEGEND_COLUMNS) * columnW;
    const y = box.y + Math.floor(n / LEGEND_COLUMNS) * LEGEND_ROW + LEGEND_ROW / 2;
    ctx.save();
    ctx.translate(x, y - 10);
    ctx.scale(20 / 24, 20 / 24);
    ctx.strokeStyle = KIND_COLORS[event.kind];
    ctx.lineWidth = 1.8;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.stroke(pathOf(event.kind));
    ctx.restore();
    ctx.font = `600 18px ${FONT}`;
    ctx.fillStyle = '#f2f3f4';
    ctx.fillText(event.title, x + 30, y);
    const after = x + 30 + ctx.measureText(event.title).width + 10;
    ctx.font = `400 15px ${FONT}`;
    ctx.fillStyle = '#8b8f94';
    ctx.fillText(eventWhen(event), after, y);
  });
  ctx.restore();
  return box.y + eventLegendHeight(events);
}

// ---------- Painting on a canvas (lib/reel.js) ----------
/**
 * Paints the events laid out by layoutEvents (with the reel's `scale`) on a frame.
 * `plot` is the plot's box in frame pixels, `shownOf(event)` how far each event has popped in (0 hides it, 1 is
 * in place), and `tipX` where the line's tip is: a span's shade reaches no further than the line drawn so far.
 */
export function paintEvents(ctx, laid, { plot, scale, shownOf, tipX = Infinity, xOf }) {
  for (const item of laid.items) {
    const shown = shownOf(item.event);
    if (shown <= 0) continue;
    const color = KIND_COLORS[item.event.kind];
    const top = chipTop(plot.top, item.row, scale) - (1 - shown) * 8 * scale;
    ctx.save();
    ctx.globalAlpha = shown;
    if (item.event.until !== null) {
      const until = Math.min(item.event.until === Infinity ? plot.right : Math.min(xOf(item.event.until), plot.right), tipX);
      ctx.fillStyle = color;
      ctx.globalAlpha = shown * 0.07;
      ctx.fillRect(item.x, plot.top, Math.max(0, until - item.x), plot.bottom - plot.top);
      ctx.globalAlpha = shown;
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = scale;
    ctx.setLineDash([3 * scale, 3 * scale]);
    ctx.globalAlpha = shown * 0.6;
    ctx.beginPath();
    ctx.moveTo(item.x, top + CHIP.h * scale);
    ctx.lineTo(item.x, plot.bottom);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = shown;
    paintChip(ctx, item, top, scale);
    ctx.restore();
  }
}

function paintChip(ctx, item, top, scale) {
  const color = KIND_COLORS[item.event.kind];
  const h = CHIP.h * scale;
  ctx.beginPath();
  ctx.roundRect(item.left, top, item.w, h, CHIP.radius * scale);
  ctx.fillStyle = CARD;
  ctx.fill();
  ctx.strokeStyle = RULE;
  ctx.lineWidth = scale;
  ctx.stroke();
  const icon = CHIP.icon * scale;
  ctx.save();
  ctx.translate(item.left + CHIP.pad * scale, top + (h - icon) / 2);
  ctx.scale(icon / 24, icon / 24);
  ctx.strokeStyle = color;
  ctx.lineWidth = 3;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.stroke(pathOf(item.event.kind));
  ctx.restore();
  if (item.w > (2 * CHIP.pad + CHIP.icon + 2) * scale) {
    ctx.font = `600 ${CHIP.font * scale}px ${FONT}`;
    ctx.fillStyle = INK_2;
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'left';
    ctx.fillText(item.event.title, item.left + (CHIP.pad + CHIP.icon + CHIP.gap) * scale, top + h / 2);
  }
}
