// The party compass as a video, 1080 × 1920 for Instagram Reels or 1920 × 1080 for YouTube and LinkedIn.
// tools/reel.py records it, as it records the Politics charts' videos.
// The empty compass comes first; then, every few seconds, one more party pops onto it, from the economic left to the right.
// While a party is the newest, its logo is lifted and a card gives its views and its two numbers.
// A closing card names the survey and what its numbers are: experts' estimates, which other surveys may not share.
// Frames are drawn on demand, and frame n is the same every time, so a recorder can take its time over each one.
// gettext, ngettext and interpolate are Django's, from the translation catalog base.html loads.
import { FONT, imageWell, loadImage, MONO, paintGround, wrap } from './chart-image.js';
import { compassPlot, darkLogo, paintCompass, paintTile, placeMarkers, tileWidth } from './compass.js';
import {
  canvasOf, clamp, easeOut, frameReady, FORMATS, INK, INK_2, INK_3, paintFooter, paintHeader, panel, RULE,
} from './reel-frame.js';

// The pace, in seconds.
const TIME = {
  intro: 1.4,  // the empty compass, before the first party
  each: 3,  // one party: it pops in, and its card is read
  pop: 0.6,  // a logo growing into place
  swap: 0.5,  // one card giving way to the next
  outro: 5,  // every party, held to be read, with the closing card
};
// The axes' type in pixels in each shape, large enough to read on a phone: their names, and the numbers 0, 5 and 10.
const AXES = { reel: { names: 22, ticks: 20 }, wide: { names: 20, ticks: 18 } };
const TILE = 0.09;  // a logo's height, as a share of the plot's shorter side

// Where the parts go in each shape, between the title's foot (`top`) and the source's top (`footer`).
const LAYOUTS = {
  // Under the title, the compass takes the room; a compact card sits under it, above the source.
  reel: (F, top, footer) => {
    const card = { h: 220, compact: true };
    card.y = footer - 28 - card.h;
    return { well: { top, h: card.y - 28 - top, w: F.width, pad: F.pad }, card: { ...card, x: F.pad, w: F.width - 2 * F.pad } };
  },
  // The compass on the left, wider than tall; the card on the right, level with its middle.
  wide: (F, top, footer) => {
    const h = footer - 28 - top;
    const w = Math.round(F.width * 0.6);
    const card = { x: w + 24, w: F.width - w - 24 - F.pad, h: 330 };
    card.y = top + (h - card.h) / 2;
    return { well: { top, h, w, pad: F.pad }, card };
  },
};

/**
 * Builds the video for one survey's parties.
 * `items` are the parties shown, { key, economic, social, experts, then }; `parties` describes each (politics/compass.py).
 * Resolves to { canvas, frames, draw(n) }: draw(n) paints frame n on the canvas.
 */
export async function createCompassReel({ format = 'reel', title, subtitle, flag, source, logos, parties, items, survey }) {
  const F = FORMATS[format];
  await frameReady();
  const order = [...items].sort((a, b) => a.economic - b.economic || a.key.localeCompare(b.key));

  // The parts that never move: ground, title and the site's line under it, source, the well.
  const base = canvasOf(F);
  const baseCtx = base.getContext('2d');
  paintGround(baseCtx, F.width, F.height);
  const top = paintHeader(baseCtx, F, { title, flag: await loadImage(flag), unit: '', subtitle, explanation: '' }) + 30;
  const footer = paintFooter(baseCtx, F, [source], F.safe.bottom);
  const layout = LAYOUTS[format](F, top, footer);
  const { inner } = imageWell(baseCtx, layout.well.top, layout.well.h, { width: layout.well.w, pad: layout.well.pad });

  // Lines grow with the plot, which the well's shorter side limits.
  const k = Math.min(inner.w, inner.h) / 600;
  const type = AXES[format];
  // The plot fills the well, with room at the foot and on the left for the numbers, at their size.
  const plot = compassPlot(inner.w, inner.h, { top: 16, right: 16, bottom: type.ticks * 2, left: type.ticks * 2 }, { fill: true });
  plot.x += inner.x;
  plot.y += inner.y;
  const size = Math.round(Math.min(plot.w, plot.h) * TILE);
  const markers = placeMarkers(order, plot, size, (key) => tileWidth(darkLogo(parties[key], logos), size));
  const appearAt = new Map(order.map((item, i) => [item.key, TIME.intro + i * TIME.each]));
  const outro = TIME.intro + order.length * TIME.each;
  const frames = Math.ceil((outro + TIME.outro) * 30) + 1;
  const number = new Intl.NumberFormat(document.documentElement.lang, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  const canvas = canvasOf(F);
  const ctx = canvas.getContext('2d');

  function draw(n) {
    const t = n / 30;
    ctx.drawImage(base, 0, 0);
    // The newest party, while its card is up; none in the intro and the outro.
    const index = t < TIME.intro || t >= outro ? -1 : Math.floor((t - TIME.intro) / TIME.each);
    ctx.save();
    ctx.globalAlpha = easeOut(clamp(t / 0.8));
    paintCompass(ctx, plot, {
      grid: false,  // a video shows the axes alone, without grid lines
      markers, parties, logos, size, k,
      shown: (key) => clamp((t - appearAt.get(key)) / TIME.pop),
      highlight: index >= 0 ? order[index].key : null,
      fade: 0.6,
      type,
    });
    ctx.restore();
    // One card at a time: the old one sinks away just before the next party arrives, and the new one rises in with it.
    const half = TIME.swap / 2;
    const cards = [...order.map((item) => ({ from: appearAt.get(item.key), item })), { from: outro, item: null }];
    cards.forEach(({ from, item }, i) => {
      const until = cards[i + 1]?.from ?? Infinity;
      const enter = easeOut(clamp((t - from) / half));
      const leave = 1 - easeOut(clamp((t - (until - half)) / half));
      const shown = Math.min(enter, leave);
      if (shown <= 0) return;
      ctx.save();
      ctx.globalAlpha = shown;
      ctx.translate(0, (1 - enter) * 18 - (1 - leave) * 18);
      const paintCard = layout.card.compact ? paintCompactCard : paintPartyCard;
      if (item) paintCard(ctx, layout.card, parties[item.key], item, logos, number);
      else paintClosingCard(ctx, layout.card, survey, order.length);
      ctx.restore();
    });
  }

  return { canvas, frames, draw };
}

// A party's card: its logo and names, how Wikipedia describes it, and its two numbers on their scales.
function paintPartyCard(ctx, box, party, item, logos, number) {
  panel(ctx, box, party.color);
  const pad = 30;
  const logoSize = 104;
  const logo = darkLogo(party, logos);
  const logoWidth = tileWidth(logo, logoSize);
  paintTile(ctx, box.x + pad + logoWidth / 2, box.y + pad + logoSize / 2, logoSize, party, logo,
    { k: 1.6, width: logoWidth, fill: '#17191b' });
  const x = box.x + pad + logoWidth + 26;
  const width = box.x + box.w - pad - x;
  ctx.textBaseline = 'top';
  ctx.fillStyle = INK;
  ctx.font = `700 46px ${FONT}`;
  ctx.fillText(party.abbreviation, x, box.y + pad - 2);
  ctx.fillStyle = INK_2;
  ctx.font = `500 24px ${FONT}`;
  ctx.fillText(wrap(ctx, party.name, width, 1)[0], x, box.y + pad + 54);
  // An inferred place says so first, in gold, before any rename or merger.
  const note = [item.inferred ? gettext('Inferred, not measured.') : '', item.then, party.ended].filter(Boolean).join(' ');
  if (note) {
    ctx.fillStyle = item.inferred ? '#ffd700' : INK_3;
    ctx.font = `400 20px ${FONT}`;
    ctx.fillText(wrap(ctx, note, width, 1)[0], x, box.y + pad + 86);
  }
  // The views, from Wikipedia: the position in bold, then the ideologies.
  let y = box.y + pad + logoSize + 18;
  ctx.font = `700 24px ${FONT}`;
  ctx.fillStyle = INK;
  const position = `${party.position} · `;
  ctx.fillText(position, box.x + pad, y);
  const offset = ctx.measureText(position).width;
  ctx.font = `400 24px ${FONT}`;
  ctx.fillStyle = INK_2;
  ctx.fillText(wrap(ctx, party.ideologies.join(', '), box.w - 2 * pad - offset, 1)[0], box.x + pad + offset, y);
  // The two numbers, side by side.
  y += 50;
  const half = (box.w - 2 * pad - 40) / 2;
  paintScale(ctx, box.x + pad, y, half, gettext('Economy'), item.economic, gettext('Left'), gettext('Right'), party.color, number);
  paintScale(ctx, box.x + pad + half + 40, y, half, gettext('Social values'), item.social, gettext('Progressive'), gettext('Conservative'), party.color, number);
}

// The scale's type in pixels: the card's, and the compact card's.
const SCALE_TYPE = {
  full: { label: 18, number: 32, ends: 17, bar: 54, dot: 11 },
  compact: { label: 16, number: 26, ends: 16, bar: 42, dot: 9 },
};

// One axis's number over a 0–10 bar with a dot at the value and the two ends named under it.
function paintScale(ctx, x, y, width, label, value, low, high, color, number, T = SCALE_TYPE.full) {
  ctx.textBaseline = 'top';
  ctx.font = `600 ${T.label}px ${MONO}`;
  ctx.fillStyle = INK_3;
  ctx.fillText(label.toUpperCase(), x, y + (T.number - T.label) / 2 + 2);
  ctx.textAlign = 'right';
  ctx.font = `700 ${T.number}px ${MONO}`;
  ctx.fillStyle = INK;
  ctx.fillText(number.format(value), x + width, y + 2);
  ctx.textAlign = 'left';
  const barY = y + T.bar;
  ctx.fillStyle = RULE;
  ctx.beginPath();
  ctx.roundRect(x, barY, width, 6, 3);
  ctx.fill();
  const at = x + (value / 10) * width;
  ctx.beginPath();
  ctx.arc(at, barY + 3, T.dot, 0, 2 * Math.PI);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.lineWidth = 3;
  ctx.strokeStyle = '#17191b';
  ctx.stroke();
  ctx.font = `500 ${T.ends}px ${FONT}`;
  ctx.fillStyle = INK_3;
  ctx.fillText(low, x, barY + T.dot + 9);
  ctx.textAlign = 'right';
  ctx.fillText(high, x + width, barY + T.dot + 9);
  ctx.textAlign = 'left';
}

// The tall shape's card, a third shorter than the wide one's, so the compass keeps the room.
// On the left, the logo, the names and the views; on the right, the two numbers on their scales, one over the other.
function paintCompactCard(ctx, box, party, item, logos, number) {
  panel(ctx, box, party.color);
  const pad = 26;
  const logoSize = 64;
  const logo = darkLogo(party, logos);
  const logoWidth = tileWidth(logo, logoSize);
  const left = box.x + pad;
  const split = box.x + Math.round(box.w * 0.54);  // where the numbers start
  const top = box.y + pad;
  const drawn = paintTile(ctx, left + logoWidth / 2 - 6, top + logoSize / 2, logoSize, party, logo, { k: 1.4, width: logoWidth, fill: '#17191b' });
  const x = drawn.x + drawn.width + 18;
  const width = split - 30 - x;
  ctx.textBaseline = 'top';
  ctx.fillStyle = INK;
  ctx.font = `700 34px ${FONT}`;
  ctx.fillText(wrap(ctx, party.abbreviation, width, 1)[0], x, top - 2);
  ctx.fillStyle = INK_2;
  ctx.font = `500 19px ${FONT}`;
  ctx.fillText(wrap(ctx, party.name, width, 1)[0], x, top + 40);
  // Under the logo: an inferred place first, in gold, then any rename or merger; then the views, from Wikipedia.
  let y = top + logoSize + 12;
  const note = [item.inferred ? gettext('Inferred, not measured.') : '', item.then, party.ended].filter(Boolean).join(' ');
  if (note) {
    ctx.fillStyle = item.inferred ? '#ffd700' : INK_3;
    ctx.font = `400 17px ${FONT}`;
    ctx.fillText(wrap(ctx, note, split - 30 - left, 1)[0], left, y);
    y += 28;
  }
  // The position in bold, the ideologies under it.
  ctx.font = `700 19px ${FONT}`;
  ctx.fillStyle = INK;
  ctx.fillText(wrap(ctx, party.position, split - 30 - left, 1)[0], left, y);
  ctx.font = `400 19px ${FONT}`;
  ctx.fillStyle = INK_2;
  wrap(ctx, party.ideologies.join(', '), split - 30 - left, note ? 1 : 2).forEach((line, i) => ctx.fillText(line, left, y + 26 + i * 26));
  // The two numbers, one over the other.
  const scaleWidth = box.x + box.w - pad - split;
  paintScale(ctx, split, top - 2, scaleWidth, gettext('Economy'), item.economic, gettext('Left'), gettext('Right'), party.color, number, SCALE_TYPE.compact);
  paintScale(ctx, split, top + 86, scaleWidth, gettext('Social values'), item.social, gettext('Progressive'), gettext('Conservative'), party.color, number, SCALE_TYPE.compact);
}

// The last card: how many parties, from which survey, and what the numbers are. The compact card sets it smaller.
function paintClosingCard(ctx, box, survey, count) {
  panel(ctx, box, '#ffd700');
  const T = box.compact ? { pad: 26, head: 32, lead: 40, survey: 22, caveat: 20, line: 28, lines: 2 }
    : { pad: 34, head: 40, lead: 50, survey: 26, caveat: 23, line: 32, lines: 3 };
  ctx.textBaseline = 'top';
  ctx.fillStyle = INK;
  ctx.font = `700 ${T.head}px ${FONT}`;
  const head = interpolate(ngettext('%s party, as experts placed it', '%s parties, as experts placed them', count), [count]);
  let y = box.y + T.pad;
  for (const line of wrap(ctx, head, box.w - 2 * T.pad, box.compact ? 1 : 2)) {
    ctx.fillText(line, box.x + T.pad, y);
    y += T.lead;
  }
  ctx.fillStyle = INK_2;
  ctx.font = `500 ${T.survey}px ${FONT}`;
  ctx.fillText(`${survey.name}, ${survey.years}`, box.x + T.pad, y + 6);
  y += T.survey + 24;
  ctx.fillStyle = INK_3;
  ctx.font = `400 ${T.caveat}px ${FONT}`;
  const caveat = gettext('These are estimates from one survey. Other surveys place some parties elsewhere, and parties change.');
  for (const line of wrap(ctx, caveat, box.w - 2 * T.pad, T.lines)) {
    ctx.fillText(line, box.x + T.pad, y);
    y += T.line;
  }
}
