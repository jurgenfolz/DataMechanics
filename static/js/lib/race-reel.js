// A metric as a bar chart race, 1080 × 1920 for Instagram Reels or 1920 × 1080 for YouTube and LinkedIn.
// tools/reel.py records it, as it records the Politics videos.
// Year by year, the countries' bars grow and swap places, the highest value first: the twenty highest of each year, or
// the countries chosen on the page. Bars slide between their ranks, count their values up and down, and rise in from
// under the last row when a country enters the ranks.
// Frames are drawn on demand, and frame n is the same every time, so a recorder can take its time over each one.
// gettext and interpolate are Django's, from the translation catalog base.html loads.
import { FONT, imageWell, loadImage, MONO, paintGround } from './chart-image.js';
import { formatValue } from './format.js';
import {
  canvasOf, clamp, easeInOut, FPS, frameReady, FORMATS, INK, INK_2, INK_3, paintFooter, paintHeader,
} from './reel-frame.js';

// The pace, in seconds.
const TIME = {
  intro: 1,  // the first year, still
  shortest: 0.7,  // a year, at least
  longest: 2.4,  // and at most
  whole: 60,  // what every year shares, so a long series keeps moving and a short one lingers
  hold: 3.5,  // the last year, held
};
export const TOP = 20;  // the countries each year shows when none are chosen
const BAR = '#3987e5';
const LEADER = '#5598e7';
const WORLD = 'WLD';

/**
 * Builds the video. `data` is the metric's data.json, `years` the [first, last] shown, `top` how many countries each
 * year ranks (0 for the chosen ones), `selected` the chosen countries [{ iso3, color }] with the chart's colours, which
 * colour their bars; the ranked ones are blue. `unit` names what the values are in, after the title.
 * Resolves to { canvas, frames, draw(n) }: draw(n) paints frame n on the canvas.
 */
export async function createRaceReel({ format = 'reel', data, units, years, top, selected, title, unit, subtitle, explanation, sources }) {
  const F = FORMATS[format];
  await frameReady();
  const rule = units[data.unit];
  const count = top || selected.length;
  const colours = new Map(top ? [] : selected.map((country) => [country.iso3, country.color]));  // the chart's colours, when its countries race
  const chosen = top ? null : new Set(selected.map((country) => country.iso3));
  const indices = data.years.map((year, i) => i).filter((i) => data.years[i] >= years[0] && data.years[i] <= years[1]);

  // A keyframe a year: the countries ranked, highest first, with their value and the year's highest.
  const keyframes = indices.map((i) => {
    const ranked = Object.entries(data.values)
      .filter(([iso3, values]) => values[i] !== null && values[i] !== undefined && (chosen ? chosen.has(iso3) : iso3 !== WORLD))
      .map(([iso3, values]) => ({ iso3, value: values[i] }))
      .sort((a, b) => b.value - a.value)
      .slice(0, count);
    return { year: data.years[i], rows: new Map(ranked.map((row, rank) => [row.iso3, { ...row, rank }])), most: ranked[0]?.value || 1 };
  }).filter((frame) => frame.rows.size);
  const everyone = [...new Set(keyframes.flatMap((frame) => [...frame.rows.keys()]))];
  const flags = new Map(await Promise.all(everyone.map(async (iso3) => [iso3, await loadImage(data.countries[iso3]?.flag)])));

  // The parts that never move: ground, title, source and the empty well.
  const base = canvasOf(F);
  const baseCtx = base.getContext('2d');
  paintGround(baseCtx, F.width, F.height);
  const top0 = paintHeader(baseCtx, F, { title, unit, subtitle, explanation }) + 30;
  const footer = paintFooter(baseCtx, F, sources, F.safe.bottom);
  const { inner } = imageWell(baseCtx, top0, footer - 28 - top0, { width: F.width, pad: F.pad });

  // The rows' places: rank, flag and name on the left, the bar and its value to the right.
  const rowHeight = Math.min(80, (inner.h - 32) / Math.max(count, 1));
  const font = Math.round(Math.max(16, Math.min(30, rowHeight * 0.5)));
  const flagHeight = Math.round(rowHeight * 0.48);
  const nameWidth = Math.round(Math.min(F.width * 0.22, 240));
  const x0 = inner.x + 20 + font * 1.6 + flagHeight * (4 / 3) + 12 + nameWidth + 16;
  baseCtx.font = `600 ${font}px ${MONO}`;
  const valueWidth = Math.max(...keyframes.map((frame) => baseCtx.measureText(formatValue(frame.most, rule)).width));
  const longest = inner.x + inner.w - 24 - valueWidth - 14 - x0;
  const y0 = inner.y + 16;

  const perYear = Math.max(TIME.shortest, Math.min(TIME.longest, TIME.whole / Math.max(keyframes.length, 1)));
  const end = TIME.intro + (keyframes.length - 1) * perYear + TIME.hold;
  const frames = Math.ceil(end * FPS) + 1;

  const canvas = canvasOf(F);
  const ctx = canvas.getContext('2d');

  function draw(n) {
    const time = n / FPS;
    ctx.drawImage(base, 0, 0);
    const u = Math.max(0, Math.min(keyframes.length - 1, (time - TIME.intro) / perYear));
    const i = Math.min(Math.floor(u), keyframes.length - 1);
    const next = keyframes[Math.min(i + 1, keyframes.length - 1)];
    const f = u - i;
    paintYear(keyframes[i].year, next.year, f);
    paintBars(keyframes[i], next, f);
  }

  // The year, large and quiet, in the well's lower right corner; the next year fades in over it.
  function paintYear(year, nextYear, f) {
    ctx.save();
    ctx.font = `700 condensed ${Math.round(F.type.year * 0.55)}px ${FONT}`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';
    const x = inner.x + inner.w - 24;
    const y = inner.y + inner.h - 8;
    ctx.fillStyle = INK;
    ctx.globalAlpha = 0.14 * (nextYear === year ? 1 : 1 - f);
    ctx.fillText(String(year), x, y);
    if (nextYear !== year) {
      ctx.globalAlpha = 0.14 * f;
      ctx.fillText(String(nextYear), x, y);
    }
    ctx.restore();
  }

  // Every bar in either keyframe: its place slides between its ranks, its value counts between the years' values, and
  // a bar entering or leaving the ranks rises from or sinks under the last row, fading.
  function paintBars(from, to, f) {
    const slide = easeInOut(f);
    const most = from.most + (to.most - from.most) * f;
    const height = rowHeight * 0.62;
    ctx.save();
    ctx.beginPath();
    ctx.rect(inner.x, inner.y, inner.w, inner.h);
    ctx.clip();
    ctx.textBaseline = 'middle';
    const bars = [...new Set([...from.rows.keys(), ...to.rows.keys()])].map((iso3) => {
      const a = from.rows.get(iso3);
      const b = to.rows.get(iso3);
      const value = (a?.value ?? b.value) + ((b?.value ?? a.value) - (a?.value ?? b.value)) * f;
      const place = (a?.rank ?? count) + ((b?.rank ?? count) - (a?.rank ?? count)) * slide;
      const alpha = (a ? 1 : 0) + ((b ? 1 : 0) - (a ? 1 : 0)) * slide;
      return { iso3, value, place, alpha };
    });
    bars.sort((a, b) => b.place - a.place);  // the lower bars first, so a rising bar passes over them
    for (const bar of bars) {
      const middle = y0 + rowHeight * (bar.place + 0.5);
      const colour = colours.get(bar.iso3) || (bar.place < 0.5 ? LEADER : BAR);
      ctx.globalAlpha = clamp(bar.alpha);
      ctx.textAlign = 'right';
      ctx.font = `500 ${Math.round(font * 0.75)}px ${MONO}`;
      ctx.fillStyle = INK_3;
      ctx.fillText(String(Math.round(bar.place) + 1), inner.x + 20 + font * 1.2, middle);
      const image = flags.get(bar.iso3);
      const flagX = inner.x + 20 + font * 1.6;
      if (image) {
        ctx.save();
        ctx.beginPath();
        ctx.roundRect(flagX, middle - flagHeight / 2, flagHeight * (4 / 3), flagHeight, 3);
        ctx.clip();
        ctx.drawImage(image, flagX, middle - flagHeight / 2, flagHeight * (4 / 3), flagHeight);
        ctx.restore();
      }
      ctx.textAlign = 'left';
      ctx.font = `600 ${font}px ${FONT}`;
      ctx.fillStyle = bar.place < 0.5 ? INK : INK_2;
      ctx.fillText(fit(ctx, data.countries[bar.iso3]?.name || bar.iso3, nameWidth), flagX + flagHeight * (4 / 3) + 12, middle);
      const length = Math.max(3, longest * bar.value / most);
      ctx.fillStyle = colour;
      ctx.beginPath();
      ctx.roundRect(x0, middle - height / 2, length, height, [0, 6, 6, 0]);
      ctx.fill();
      ctx.font = `600 ${font}px ${MONO}`;
      ctx.fillStyle = INK;
      ctx.fillText(formatValue(bar.value, rule), x0 + length + 14, middle);
    }
    ctx.restore();
  }

  return { canvas, frames, draw };
}

/** `text` cut to fit `width` in the current font, with an ellipsis. */
function fit(ctx, text, width) {
  if (ctx.measureText(text).width <= width) return text;
  let cut = text;
  while (cut.length > 1 && ctx.measureText(`${cut}…`).width > width) cut = cut.slice(0, -1);
  return `${cut.trimEnd()}…`;
}
