// What every video on the site shares: its two shapes, its frame (title, the site's name under it, source) and its easing.
// lib/reel.js tells a Politics chart's story with it, lib/compass-reel.js the party compass's and lib/congress-reel.js
// the seats in Congress.
// gettext is Django's, from the translation catalog base.html loads.
import { FONT, loadImage, MONO, paintBrandLine, paintRoundFlag, wrap } from './chart-image.js';

export const FPS = 30;

// The two shapes a reel comes in: the same story, sized for where it is watched.
// `scale` draws the chart that many times its size on the site; the zooms do the same for the cards, the row and the ranking.
// `safe` is where the title starts, where the timeline row ends, and how far right the cards may reach.
// `type` holds the header's font sizes in pixels.
export const FORMATS = {
  // Instagram Reels, on a phone. Instagram lays its own buttons over a reel: about 250 px at the top, the caption at the
  // bottom, and a column of buttons at the right. The title starts below the top band, the row ends above the caption,
  // and the cards keep clear of the column. Guides disagree on the sizes: 320 px is what the caption takes.
  reel: {
    width: 1080, height: 1920, pad: 56, scale: 2.2, cardZoom: 2.3, nowZoom: 2.2, rankZoom: 2,
    safe: { top: 250, bottom: 1920 - 320, right: 1080 - 160 },
    type: { title: 84, flag: 76, subtitle: 30, explanation: 28, explanationLines: 4, year: 320 },
  },
  // YouTube and LinkedIn, on a computer. Nothing lies over the frame for long, so margins are enough.
  wide: {
    width: 1920, height: 1080, pad: 64, scale: 1.6, cardZoom: 1.7, nowZoom: 1.6, rankZoom: 1.5,
    safe: { top: 56, bottom: 1080 - 48, right: 1920 - 64 },
    type: { title: 72, flag: 66, subtitle: 28, explanation: 24, explanationLines: 2, year: 300 },
  },
};

export const INK = '#f2f3f4';
export const INK_2 = '#b6b9bd';
export const INK_3 = '#8b8f94';
export const RULE = '#3a3d41';
export const WELL = '#1d1f21';
export const CARD = 'rgba(23, 25, 27, 0.95)';

export const clamp = (v) => Math.min(1, Math.max(0, v));
export const easeOut = (v) => 1 - (1 - v) ** 3;
export const easeInOut = (v) => (v < 0.5 ? 4 * v ** 3 : 1 - (-2 * v + 2) ** 3 / 2);

let gear = null;  // the site's logo, for the line under the title; frameReady loads it

// The country's round flag, then the title with the unit its values are in, in grey after it.
// Under them, the subtitle, the metric's explanation, and the site's name in the explanation's type, a little faded.
export function paintHeader(ctx, F, { title, flag, unit, subtitle, explanation }) {
  const T = F.type;
  const lead = T.title + 4;  // a title line's height
  let y = F.safe.top;
  if (flag) paintRoundFlag(ctx, flag, F.pad, y + T.title * 0.52, T.flag);
  // The title's lines start right of the flag; everything under them starts at the edge again.
  const left = flag ? F.pad + T.flag + 22 : F.pad;
  const width = F.width - F.pad - left;
  ctx.textBaseline = 'top';
  ctx.font = `700 condensed ${T.title}px ${FONT}`;
  const lines = wrap(ctx, title, width, 2);
  const tail = unit ? ` · ${unit}` : '';
  ctx.font = `500 condensed ${T.title}px ${FONT}`;
  const tailWidth = ctx.measureText(tail).width;
  lines.forEach((line, i) => {
    ctx.font = `700 condensed ${T.title}px ${FONT}`;
    ctx.fillStyle = INK;
    ctx.fillText(line, left, y);
    const last = i === lines.length - 1;
    const lineWidth = ctx.measureText(line).width;
    y += lead;
    if (!last || !tail) return;
    ctx.font = `500 condensed ${T.title}px ${FONT}`;
    ctx.fillStyle = INK_3;
    // The unit follows the title on its last line, or takes a line of its own when it does not fit.
    if (lineWidth + tailWidth <= width) ctx.fillText(tail, left + lineWidth, y - lead);
    else {
      ctx.fillText(unit, left, y);
      y += lead;
    }
  });
  ctx.fillStyle = INK_2;
  ctx.font = `500 ${T.subtitle}px ${FONT}`;
  y += 6;
  for (const line of wrap(ctx, subtitle, F.width - 2 * F.pad, 2)) {
    ctx.fillText(line, F.pad, y);
    y += T.subtitle + 10;
  }
  ctx.fillStyle = INK_3;
  ctx.font = `400 ${T.explanation}px ${FONT}`;
  y += 14;
  if (explanation) {
    for (const line of wrap(ctx, explanation, F.width - 2 * F.pad, T.explanationLines)) {
      ctx.fillText(line, F.pad, y);
      y += T.explanation + 10;
    }
  }
  return paintBrandLine(ctx, F.pad, y, T.explanation, gear) + 10;
}

// The source, small, ending at `bottom`. It keeps clear of Instagram's buttons at the right. Returns its top.
export function paintFooter(ctx, F, sources, bottom) {
  ctx.font = `400 22px ${FONT}`;
  const lines = sources.filter(Boolean).flatMap((text) => wrap(ctx, text, F.safe.right - F.pad, 3));
  const top = bottom - lines.length * 30;
  ctx.textBaseline = 'top';
  ctx.fillStyle = INK_3;
  lines.forEach((line, i) => ctx.fillText(line, F.pad, top + i * 30));
  return top;
}

export function dot(ctx, x, y, r, colour) {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, 2 * Math.PI);
  ctx.fillStyle = colour;
  ctx.fill();
}

export function canvasOf(F) {
  const canvas = document.createElement('canvas');
  canvas.width = F.width;
  canvas.height = F.height;
  return canvas;
}

/** Loads what every frame needs before it is drawn: the fonts, and the site's logo for the line under the title. */
export async function frameReady() {
  gear = await loadImage(document.querySelector('link[rel="icon"]')?.href);
  await Promise.all([`700 condensed 84px ${FONT}`, `500 30px ${FONT}`, `400 22px ${FONT}`, `700 16px ${FONT}`,
    `700 14px ${MONO}`, `600 9px ${MONO}`].map((font) => document.fonts.load(font).catch(() => null)));
}

// A card's panel, with a bar in `accent` down its left edge.
export function panel(ctx, box, accent) {
  ctx.beginPath();
  ctx.roundRect(box.x, box.y, box.w, box.h, 20);
  ctx.fillStyle = CARD;
  ctx.fill();
  ctx.save();
  ctx.clip();
  ctx.fillStyle = accent;
  ctx.fillRect(box.x, box.y, 6, box.h);
  ctx.restore();
  ctx.beginPath();
  ctx.roundRect(box.x + 0.75, box.y + 0.75, box.w - 1.5, box.h - 1.5, 20);
  ctx.strokeStyle = RULE;
  ctx.lineWidth = 1.5;
  ctx.stroke();
}
