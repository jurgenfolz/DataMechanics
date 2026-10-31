// Crime suspects by nationality as a video, 1080 × 1920 for Instagram Reels or 1920 × 1080 for YouTube and LinkedIn.
// tools/reel.py records it, as it records the other Politics videos.
// The bars grow in, the largest share first. A card then goes through the country's own citizens, every foreign national
// together, and the largest foreign nationalities, each lit in turn; a last card says what the shares cannot show.
// Frames are drawn on demand, and frame n is the same every time, so a recorder can take its time over each one.
// gettext and interpolate are Django's, from the translation catalog base.html loads.
import { FONT, imageWell, loadImage, paintGround, wrap } from './chart-image.js';
import { formatValue, formatWhole } from './format.js';
import {
  canvasOf, clamp, easeOut, frameReady, FORMATS, INK, INK_2, INK_3, paintFooter, paintHeader, panel,
} from './reel-frame.js';
import { COLORS, paintKey, shortName } from './suspects-chart.js';

// The pace, in seconds.
const TIME = {
  intro: 0.5,  // the empty well
  grow: 2.6,  // every bar grows in, one after another
  bar: 0.6,  // one bar growing to its length
  card: 3.2,  // one card, with its bars lit
  limits: 6,  // the last card, held to be read
  fade: 0.35,  // the lit bars changing
  swap: 0.4,  // one card giving way to the next
};
const FAINT = 0.22;  // a bar that is not lit
// The most bars each shape can show with names a phone can read; lib/crime-view.js keeps the highest shares.
export const ROWS = { reel: 10, wide: 12 };
const TOUR = 4;  // the foreign nationalities with the most people get a card each
const KEY = 44;  // the room under the well for its key

// Where the parts go in each shape, between the title's foot (`top`) and the source's top (`footer`).
// The card keeps clear of the buttons Instagram lays over a reel's right edge (`safe.right`).
const LAYOUTS = {
  // The bars under the title, the key and the card under them.
  reel: (F, top, footer) => {
    const card = { h: 280 };
    const well = { top, h: footer - 28 - top - card.h - 28 - KEY, w: F.width, pad: F.pad };
    Object.assign(card, { x: F.pad, y: well.top + well.h + KEY + 28, w: F.safe.right - F.pad });
    return { well, card };
  },
  // The bars on the left; the card on the right, level with their middle.
  wide: (F, top, footer) => {
    const h = footer - 28 - top - KEY;
    const w = Math.round(F.width * 0.58);
    const card = { x: w + 24, w: F.width - w - 24 - F.pad, h: 300 };
    card.y = top + (h - card.h) / 2;
    return { well: { top, h, w, pad: F.pad }, card };
  },
};

/**
 * Builds the video. `rows` are the chart's bars, the largest share first: { code, name, flag, population, suspects, value }.
 * `own` is the code of the country's citizens, `foreign` every foreign national together, `population` the population's label,
 * and `limits` what the shares cannot show.
 * Resolves to { canvas, frames, draw(n) }: draw(n) paints frame n on the canvas.
 */
export async function createCrimeReel({
  format = 'reel', title, unit, subtitle, explanation, flag, sources, rows, own, ownName, foreign, population, limits, units,
}) {
  const F = FORMATS[format];
  await frameReady();
  const flags = new Map(await Promise.all(rows.map(async (row) => [row.code, await loadImage(row.flag)])));
  const percent = (value) => formatValue(value, units.percent);

  // The parts that never move: ground, title, source, the key and the empty well.
  const base = canvasOf(F);
  const baseCtx = base.getContext('2d');
  paintGround(baseCtx, F.width, F.height);
  const top = paintHeader(baseCtx, F, { title, flag: await loadImage(flag), unit, subtitle, explanation }) + 30;
  const footer = paintFooter(baseCtx, F, sources, F.safe.bottom);
  const layout = LAYOUTS[format](F, top, footer);
  const { inner } = imageWell(baseCtx, layout.well.top, layout.well.h, { width: layout.well.w, pad: layout.well.pad });
  paintKey(baseCtx, { x: layout.well.pad, y: layout.well.top + layout.well.h + 12 }, ownName, F.type.explanation);

  // The bars' places: a row each, its name and flag on the left, its value at its end.
  const rowHeight = Math.min(56, (inner.h - 32) / Math.max(rows.length, 1));
  const font = Math.round(Math.max(18, Math.min(30, rowHeight * 0.52)));
  const flagHeight = Math.round(rowHeight * 0.5);
  baseCtx.font = `600 ${font}px ${FONT}`;
  const names = rows.map((row) => shortName(row.name, 16));
  const nameWidth = Math.max(0, ...names.map((name) => baseCtx.measureText(name).width));
  const x0 = inner.x + 20 + nameWidth + 14 + flagHeight * (4 / 3) + 14;
  const longest = inner.x + inner.w - 24 - font * 3.6 - x0;
  const scale = longest / Math.max(...rows.map((row) => row.value), 0.001);
  const y0 = inner.y + 16 + (inner.h - 32 - rowHeight * rows.length) / 2;

  // The story: each step lights some bars (null: all) and shows a card.
  const ownRow = rows.find((row) => row.code === own);
  const tour = rows.filter((row) => row.code !== own).sort((a, b) => b.population - a.population).slice(0, TOUR);
  const steps = [];
  let t = TIME.intro + TIME.grow;
  if (ownRow) {
    steps.push({ from: t, lit: (row) => row.code === own, card: { row: ownRow } });
    t += TIME.card;
  }
  steps.push({ from: t, lit: (row) => row.code !== own, card: { row: foreign, all: true } });
  t += TIME.card;
  for (const row of tour) {
    steps.push({ from: t, lit: (other) => other.code === row.code, card: { row } });
    t += TIME.card;
  }
  steps.push({ from: t, lit: null, card: { limits: true } });
  const end = t + TIME.limits;
  const frames = Math.ceil(end * 30) + 1;
  const stepAt = (time) => steps.findLastIndex((step) => step.from <= time);

  // A bar's brightness: what the current step asks, eased from what the step before asked.
  const brightness = (step, row) => (!step?.lit || step.lit(row) ? 1 : FAINT);
  function alphaOf(row, time, index) {
    if (index < 0) return 1;
    const now = brightness(steps[index], row);
    const before = brightness(steps[index - 1], row);
    return before + (now - before) * easeOut(clamp((time - steps[index].from) / TIME.fade));
  }

  const canvas = canvasOf(F);
  const ctx = canvas.getContext('2d');

  function draw(n) {
    const time = n / 30;
    ctx.drawImage(base, 0, 0);
    paintBars(time, stepAt(time));
    paintCards(time);
  }

  function paintBars(time, index) {
    const height = rowHeight * 0.56;
    rows.forEach((row, i) => {
      const middle = y0 + rowHeight * (i + 0.5);
      const start = TIME.intro + (i / rows.length) * (TIME.grow - TIME.bar);
      const grow = easeOut(clamp((time - start) / TIME.bar));
      ctx.save();
      ctx.globalAlpha = time < TIME.intro ? 0 : alphaOf(row, time, index) * Math.min(1, grow * 3);
      ctx.textBaseline = 'middle';
      ctx.textAlign = 'right';
      ctx.font = `${row.code === own ? 700 : 600} ${font}px ${FONT}`;
      ctx.fillStyle = row.code === own ? COLORS.own : INK_2;
      ctx.fillText(names[i], inner.x + 20 + nameWidth, middle);
      ctx.textAlign = 'left';
      const image = flags.get(row.code);
      if (image) ctx.drawImage(image, inner.x + 20 + nameWidth + 14, middle - flagHeight / 2, flagHeight * (4 / 3), flagHeight);
      const length = Math.max(row.value * scale * grow, 2);
      ctx.fillStyle = row.code === own ? COLORS.own : COLORS.foreign;
      ctx.beginPath();
      ctx.roundRect(x0, middle - height / 2, length, height, [0, 5, 5, 0]);
      ctx.fill();
      ctx.globalAlpha *= clamp((grow - 0.6) / 0.4);
      ctx.fillStyle = INK_2;
      ctx.font = `600 ${font}px ${FONT}`;
      ctx.fillText(percent(row.value), x0 + length + 12, middle);
      ctx.restore();
    });
  }

  // One card at a time: the old one sinks away just before the next step, and the new one rises in with it.
  function paintCards(time) {
    const half = TIME.swap / 2;
    steps.forEach((step, i) => {
      const until = steps[i + 1]?.from ?? end + half;
      const enter = easeOut(clamp((time - step.from) / half));
      const leave = 1 - easeOut(clamp((time - (until - half)) / half));
      const shown = Math.min(enter, leave);
      if (shown <= 0) return;
      ctx.save();
      ctx.globalAlpha *= shown;
      ctx.translate(0, (1 - enter) * 18 - (1 - leave) * 18);
      if (step.card.limits) paintLimits(ctx, layout.card);
      else paintRowCard(ctx, layout.card, step.card.row, step.card.all);
      ctx.restore();
    });
  }

  // A nationality's card, or every foreign national's: its share, large, its name, and its suspects and people.
  function paintRowCard(c, box, row, all) {
    const colour = row.code === own ? COLORS.own : COLORS.foreign;
    panel(c, box, colour);
    const pad = 32;
    let x = box.x + pad + 8;
    c.textBaseline = 'middle';
    const image = all ? null : flags.get(row.code);
    if (image) {
      c.drawImage(image, x, box.y + pad, 56, 42);
      x += 56 + 18;
    }
    c.fillStyle = INK;
    c.font = `800 42px ${FONT}`;
    c.fillText(wrap(c, row.code === own ? ownName : row.name, box.x + box.w - pad - x, 1)[0], x, box.y + pad + 22);
    c.textBaseline = 'top';
    const y = box.y + pad + 72;
    c.fillStyle = colour;
    c.font = `800 96px ${FONT}`;
    const big = percent(row.value);
    c.fillText(big, box.x + pad + 8, y);
    const left = box.x + pad + 8 + c.measureText(big).width + 32;
    const width = box.x + box.w - pad - left;
    c.fillStyle = INK_2;
    c.font = `500 26px ${FONT}`;
    let line = y + 8;
    for (const text of wrap(c, all ? gettext('of them were suspects') : gettext('of its people were suspects'), width, 2)) {
      c.fillText(text, left, line);
      line += 34;
    }
    c.fillStyle = INK_3;
    c.font = `500 22px ${FONT}`;
    for (const text of [`${gettext('Suspects')}: ${formatWhole(row.suspects, units)}`, `${population}: ${formatWhole(row.population, units)}`]) {
      c.fillText(wrap(c, text, width, 1)[0], left, line + 4);
      line += 30;
    }
  }

  // The last card: what the shares cannot show.
  function paintLimits(c, box) {
    panel(c, box, '#ffd700');
    const pad = 34;
    c.textBaseline = 'top';
    c.fillStyle = INK;
    c.font = `800 40px ${FONT}`;
    c.fillText(gettext('What these shares cannot show'), box.x + pad, box.y + pad);
    c.fillStyle = INK_2;
    c.font = `500 25px ${FONT}`;
    let y = box.y + pad + 62;
    const lines = Math.floor((box.y + box.h - pad - y) / 34);
    for (const text of wrap(c, limits, box.w - 2 * pad, lines)) {
      c.fillText(text, box.x + pad, y);
      y += 34;
    }
  }

  return { canvas, frames, draw };
}
