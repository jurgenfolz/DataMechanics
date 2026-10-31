// A kind of crime by state as a video, 1080 × 1920 for Instagram Reels or 1920 × 1080 for YouTube and LinkedIn.
// tools/reel.py records it, as it records the other Politics videos.
// The map starts empty. The states fill in one by one, the best first, each with a glow and a card that names it, its
// value and its rank; the first three are held longer. The full map holds, then a ranking of every state takes the map's
// place, best first, scrolling when it does not fit.
// Frames are drawn on demand, and frame n is the same every time, so a recorder can take its time over each one.
// gettext and interpolate are Django's, from the translation catalog base.html loads.
import { FONT, imageWell, loadImage, MONO, paintGround, wrap } from './chart-image.js';
import { formatValue } from './format.js';
import {
  canvasOf, clamp, easeOut, FPS, frameReady, FORMATS, INK, INK_2, INK_3, paintFooter, paintHeader, panel, RULE,
} from './reel-frame.js';
import { BORDER, colorScale, NO_DATA, paintMapLegend, project } from './world-map.js';

// The pace, in seconds.
const TIME = {
  intro: 0.8,  // the empty map
  first: 1.8,  // each of the first three states, held to be read
  reveal: 20,  // the rest filling in, at most: a state's share shrinks with their number
  slowest: 1.4,  // a state's share, at most
  fastest: 0.2,  // and at least
  glow: 0.9,  // a state's glow fading after it fills
  hold: 3,  // the full map, before the ranking
  outro: 6,  // the ranking, held to be read when it fits
  rankTop: 2.5,  // a ranking too long to fit, held at its top
  swap: 0.2,  // the card changing to the next state
};
const SCROLL = 110;  // px a second, for a ranking too long to fit
const SCROLL_MOST = 12;  // seconds a long ranking scrolls at most: a hundred provinces go by faster
const HELD = 3;  // the states held longer, at the start
const PANEL = 'rgb(23, 25, 27)';  // the ranking's panel, solid over the map it replaces
const GLOW = '#ffd700';
const LEGEND = 60;  // the room under the map for its legend, in CSS pixels before the scale
const RANK_ROW = 44;
const RANK_HEAD = 48;

// Where the parts go in each shape, between the title's foot (`top`) and the source's top (`footer`).
// The card keeps clear of the buttons Instagram lays over a reel's right edge (`safe.right`).
const LAYOUTS = {
  // The map under the title, its legend under it, the card under the legend.
  reel: (F, top, footer) => {
    const card = { h: 196 };
    const legend = LEGEND * F.scale / 2;
    const well = { top, h: footer - 24 - top - card.h - 20 - legend, w: F.width, pad: F.pad };
    Object.assign(card, { x: F.pad, y: well.top + well.h + legend + 20, w: F.width - 2 * F.pad });
    return { well, card, legend };
  },
  // The map on the left, its legend under it; the card on the right, level with its middle.
  wide: (F, top, footer) => {
    const legend = LEGEND * F.scale / 2;
    const h = footer - 28 - top - legend;
    const w = Math.round(F.width * 0.58);
    const card = { x: w + 24, w: F.width - w - 24 - F.pad, h: 300 };
    card.y = top + (h - card.h) / 2;
    return { well: { top, h, w, pad: F.pad }, card, legend };
  },
};

/**
 * Builds the video. `data` is the chart data's `states` (politics/crime_series.py), `year` the year shown, and `shapes`
 * the states' loaded shapes (lib/states-view.js), with their GeoJSON features and projected bounds.
 * Resolves to { canvas, frames, draw(n) }: draw(n) paints frame n on the canvas.
 */
export async function createStatesReel({ format = 'reel', data, year, units, shapes, title, explanation, flag, subtitle, sources }) {
  const F = FORMATS[format];
  await frameReady();
  const rule = units[data.unit];
  const i = data.years.indexOf(year);

  // The states with a value, best first: the lowest where lower is better, else the highest.
  const rows = Object.entries(data.values)
    .filter(([, values]) => values[i] !== null && values[i] !== undefined)
    .map(([code, values]) => ({ code, name: data.countries[code]?.name || code, value: values[i] }))
    .sort((a, b) => (data.better === 'lower' ? a.value - b.value : b.value - a.value));
  const scale = colorScale(data, rows.map((row) => row.value));
  rows.forEach((row, n) => Object.assign(row, { rank: n + 1, colour: scale.color(row.value), label: formatValue(row.value, rule) }));
  const byCode = new Map(rows.map((row) => [row.code, row]));
  // The states' flags, where the site has them (Brazil's), for the card and the ranking.
  const flags = new Map(await Promise.all(rows.map(async (row) => [row.code, await loadImage(data.countries[row.code]?.flag)])));

  // The parts that never move: ground, title, source, the well and the legend.
  const base = canvasOf(F);
  const baseCtx = base.getContext('2d');
  paintGround(baseCtx, F.width, F.height);
  const top = paintHeader(baseCtx, F, { title, flag: await loadImage(flag), unit: data.label, subtitle, explanation }) + 30;
  const footer = paintFooter(baseCtx, F, sources, F.safe.bottom);
  const layout = LAYOUTS[format](F, top, footer);
  const { well, inner } = imageWell(baseCtx, layout.well.top, layout.well.h, { width: layout.well.w, pad: layout.well.pad });
  if (format === 'reel') Object.assign(layout.card, { x: well.x, w: well.w });  // under the map, as wide as its well
  const legendScale = F.scale / 2;  // small enough for the legend's three values to keep apart
  baseCtx.save();
  baseCtx.translate(inner.x, layout.well.top + layout.well.h + 14);
  baseCtx.scale(legendScale, legendScale);
  paintMapLegend(baseCtx, { x: 0, y: 0, w: inner.w / legendScale, h: LEGEND }, data, scale, units);
  baseCtx.restore();

  // Each state's shape as a path in the well, the map fitted to the well with a margin.
  const paths = fitShapes(shapes, { x: inner.x + 14, y: inner.y + 14, w: inner.w - 28, h: inner.h - 28 });

  // When each state fills in: the first three held, the rest sharing the reveal.
  const share = Math.max(TIME.fastest, Math.min(TIME.slowest, TIME.reveal / Math.max(rows.length - HELD, 1)));
  const swap = Math.min(TIME.swap, share / 2);  // the card's change, quicker when the states come fast
  let t = TIME.intro;
  for (const row of rows) {
    row.at = t;
    t += row.rank <= HELD ? TIME.first : share;
  }
  const revealed = t;
  const rankingAt = revealed + TIME.hold;
  // The ranking takes the map's place exactly: its well's box.
  const rank = rankingLayout(baseCtx, rows, well, F.rankZoom);
  rank.flags = flags;
  const scrollTime = Math.min(rank.overflow / SCROLL, SCROLL_MOST);
  const outroLength = rank.overflow > 0 ? TIME.rankTop + scrollTime + 2.5 : TIME.outro;
  const end = rankingAt + outroLength;
  const frames = Math.ceil(end * FPS) + 1;

  const canvas = canvasOf(F);
  const ctx = canvas.getContext('2d');

  function draw(n) {
    const time = n / FPS;
    ctx.drawImage(base, 0, 0);
    paintMap(time);
    if (time < rankingAt) paintCard(time);
    const outro = clamp((time - rankingAt) / 0.5);
    if (outro > 0) {
      const scrolled = clamp((time - rankingAt - TIME.rankTop) / Math.max(scrollTime, 0.001));
      paintRanking(ctx, rows, rank, easeOut(outro), scrolled * rank.overflow, `${data.title} · ${year}`, data.better);
    }
  }

  // The states: grey until their time, then their colour, with a gold glow that fades.
  function paintMap(time) {
    ctx.save();
    for (const [code, path] of paths) {
      const row = byCode.get(code);
      const lit = row ? easeOut(clamp((time - row.at) / 0.25)) : 0;
      ctx.fillStyle = NO_DATA;
      ctx.fill(path, 'evenodd');
      if (lit > 0) {
        ctx.globalAlpha = lit;
        ctx.fillStyle = row.colour;
        ctx.fill(path, 'evenodd');
        ctx.globalAlpha = 1;
      }
    }
    ctx.strokeStyle = BORDER;
    ctx.lineWidth = 0.9 * F.scale / 1.6;
    ctx.lineJoin = 'round';
    for (const path of paths.values()) ctx.stroke(path);
    // The glow, over the borders, on the states lit a moment ago.
    for (const row of rows) {
      const age = time - row.at;
      if (age < 0 || age > TIME.glow) continue;
      const path = paths.get(row.code);
      if (!path) continue;
      ctx.globalAlpha = 1 - easeOut(age / TIME.glow);
      ctx.strokeStyle = GLOW;
      ctx.lineWidth = 2.2 * F.scale / 1.6;
      ctx.shadowColor = GLOW;
      ctx.shadowBlur = 18 * F.scale / 1.6;
      ctx.stroke(path);
    }
    ctx.restore();
  }

  // The card of the state lit last: its name, its value in its colour, and its rank among the states.
  function paintCard(time) {
    const current = rows.findLast((row) => row.at <= time);
    if (!current) return;
    const next = rows[current.rank];
    const enter = easeOut(clamp((time - current.at) / swap));
    const leave = next ? 1 - easeOut(clamp((time - (next.at - swap / 2)) / (swap / 2))) : 1;
    const shown = Math.min(enter, leave);
    if (shown <= 0) return;
    const box = layout.card;
    ctx.save();
    ctx.globalAlpha = shown;
    ctx.translate(0, (1 - enter) * 14);
    panel(ctx, box, current.colour);
    const pad = Math.round(box.h * 0.13);
    const k = box.h / 250;  // the card's type, sized with the card
    ctx.textBaseline = 'top';
    // The rank, large, at the right; the name and the value at the left.
    ctx.textAlign = 'right';
    ctx.fillStyle = current.colour;
    ctx.font = `800 ${Math.round(box.h * 0.5)}px ${FONT}`;
    const rankText = String(current.rank);
    ctx.fillText(rankText, box.x + box.w - pad, box.y + pad - 6);
    const rankWidth = ctx.measureText(rankText).width;
    ctx.fillStyle = INK_3;
    ctx.font = `500 ${Math.round(24 * k)}px ${MONO}`;
    ctx.fillText(interpolate(gettext('of %s'), [rows.length]), box.x + box.w - pad, box.y + pad + box.h * 0.5 + 4);
    ctx.textAlign = 'left';
    let nameX = box.x + pad + 8;
    const flag = flags.get(current.code);
    if (flag) {  // the state's flag before its name
      const flagH = Math.round(50 * k);
      ctx.save();
      ctx.beginPath();
      ctx.roundRect(nameX, box.y + pad + 2, flagH * (4 / 3), flagH, 4);
      ctx.clip();
      ctx.drawImage(flag, nameX, box.y + pad + 2, flagH * (4 / 3), flagH);
      ctx.restore();
      nameX += flagH * (4 / 3) + 14;
    }
    const room = box.x + box.w - pad - rankWidth - 24 - nameX;
    ctx.fillStyle = INK;
    ctx.font = `800 ${Math.round(44 * k)}px ${FONT}`;
    ctx.fillText(wrap(ctx, current.name, room, 1)[0], nameX, box.y + pad);
    ctx.fillStyle = current.colour;
    ctx.font = `800 ${fitSize(ctx, current.label, room, Math.round(84 * k), Math.round(40 * k), 800)}px ${FONT}`;
    ctx.fillText(current.label, box.x + pad + 6, box.y + pad + Math.round(64 * k));
    // A strip along the card's foot: how far the states have come.
    const strip = { x: box.x + pad + 8, y: box.y + box.h - Math.round(18 * k), w: box.w - 2 * pad - 8 };
    ctx.fillStyle = RULE;
    ctx.fillRect(strip.x, strip.y, strip.w, 4);
    ctx.fillStyle = current.colour;
    ctx.fillRect(strip.x, strip.y, strip.w * current.rank / rows.length, 4);
    ctx.restore();
  }

  return { canvas, frames, draw };
}

/** The largest font size from `most` down to `least` at which `text` fits `width`, in `weight`. */
function fitSize(ctx, text, width, most, least, weight) {
  for (let size = most; size > least; size -= 4) {
    ctx.font = `${weight} ${size}px ${FONT}`;
    if (ctx.measureText(text).width <= width) return size;
  }
  return least;
}

/** Each state's shape as a Path2D fitted into `box`, by code. */
function fitShapes(shapes, box) {
  const { left, top, right, bottom } = shapes.bounds;
  const k = Math.min(box.w / (right - left), box.h / (bottom - top));
  const x0 = box.x + (box.w - (right - left) * k) / 2;
  const y0 = box.y + (box.h - (bottom - top) * k) / 2;
  const paths = new Map();
  for (const feature of shapes.features) {
    const path = new Path2D();
    for (const polygon of feature.geometry.coordinates) {
      for (const ring of polygon) {
        ring.forEach((point, n) => {
          const [px, py] = project(point);
          const x = x0 + (px - left) * k;
          const y = y0 + (py - top) * k;
          if (n === 0) path.moveTo(x, y);
          else path.lineTo(x, y);
        });
        path.closePath();
      }
    }
    paths.set(feature.properties.code, path);
  }
  return paths;
}

// ---------- The ranking that closes the reel ----------
// The panel takes the map's place: the well's width and height. Each row is a state's rank, name, a bar in its colour
// as long as its value, and the value.
function rankingLayout(ctx, rows, well, zoom) {
  const box = { x: well.x, y: well.y, w: well.w, h: well.h };
  const css = { w: box.w / zoom, h: box.h / zoom };
  ctx.font = `700 12px ${MONO}`;
  const valueWidth = Math.max(...rows.map((row) => ctx.measureText(row.label).width), 0);
  const list = rows.length * RANK_ROW + 10;
  return { box, css, zoom, valueWidth, overflow: Math.max(0, list - (css.h - RANK_HEAD)) * zoom };
}

function paintRanking(ctx, rows, layout, shown, scrolled, title, better) {
  const { box, css, zoom, valueWidth, flags } = layout;
  const most = Math.max(...rows.map((row) => row.value), 0) || 1;
  ctx.save();
  ctx.globalAlpha = shown;
  ctx.translate(box.x, box.y + (1 - shown) * 24);
  ctx.scale(zoom, zoom);
  ctx.beginPath();
  ctx.roundRect(0, 0, css.w, css.h, 18 / zoom);
  ctx.fillStyle = PANEL;
  ctx.fill();
  ctx.strokeStyle = RULE;
  ctx.lineWidth = 1;
  ctx.stroke();

  ctx.textBaseline = 'middle';
  ctx.fillStyle = INK;
  ctx.font = `700 18px ${FONT}`;
  ctx.fillText(title, 18, 26);
  ctx.font = `600 9px ${MONO}`;
  ctx.fillStyle = INK_3;
  ctx.textAlign = 'right';
  ctx.fillText((better ? gettext('Best first') : gettext('Highest first')).toUpperCase(), css.w - 18, 27);
  ctx.textAlign = 'left';

  // The rows, scrolled by `scrolled` reel pixels, inside the panel under its head.
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, RANK_HEAD, css.w, css.h - RANK_HEAD - 4);
  ctx.clip();
  ctx.translate(0, -scrolled / zoom);
  const withFlags = rows.some((row) => flags.get(row.code));
  const nameX = withFlags ? 44 + 34 : 44;
  const nameW = Math.min(170, css.w * 0.34);
  const barX = nameX + nameW + 14;
  const barW = css.w - 18 - valueWidth - 14 - barX;
  rows.forEach((row, n) => {
    const y = RANK_HEAD + n * RANK_ROW;
    const middle = y + RANK_ROW / 2;
    ctx.strokeStyle = RULE;
    ctx.globalAlpha = shown * 0.6;
    ctx.beginPath();
    ctx.moveTo(18, y);
    ctx.lineTo(css.w - 18, y);
    ctx.stroke();
    ctx.globalAlpha = shown;
    ctx.font = `500 11px ${MONO}`;
    ctx.fillStyle = INK_3;
    ctx.fillText(String(row.rank), 18, middle);
    const flag = flags.get(row.code);
    if (flag) {
      ctx.save();
      ctx.beginPath();
      ctx.roundRect(44, middle - 9, 24, 18, 2);
      ctx.clip();
      ctx.drawImage(flag, 44, middle - 9, 24, 18);
      ctx.restore();
    }
    ctx.font = `700 14px ${FONT}`;
    ctx.fillStyle = INK;
    ctx.fillText(wrap(ctx, row.name, nameW, 1)[0], nameX, middle);
    ctx.fillStyle = row.colour;
    ctx.beginPath();
    ctx.roundRect(barX, middle - 4, Math.max(3, barW * row.value / most), 8, 4);
    ctx.fill();
    ctx.font = `700 12px ${MONO}`;
    ctx.fillStyle = INK;
    ctx.textAlign = 'right';
    ctx.fillText(row.label, css.w - 18, middle);
    ctx.textAlign = 'left';
  });
  ctx.restore();

  // While rows hide above or below, the panel's edge fades over them.
  const fade = (from, to, hidden) => {
    if (!hidden) return;
    const gradient = ctx.createLinearGradient(0, from, 0, to);
    gradient.addColorStop(0, 'rgba(23, 25, 27, 1)');
    gradient.addColorStop(1, 'rgba(23, 25, 27, 0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(1, Math.min(from, to), css.w - 2, Math.abs(to - from));
  };
  fade(RANK_HEAD, RANK_HEAD + 28, scrolled > 1);
  fade(css.h - 4, css.h - 36, scrolled < layout.overflow - 1);
  ctx.restore();
}
