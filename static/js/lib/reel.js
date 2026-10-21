// A Politics reel: the chart replayed as a video, 1080 × 1920 for Instagram Reels or 1920 × 1080 for YouTube and LinkedIn.
// tools/reel.py records it.
// The line runs through the chosen years.
// The first term opens with a card at the line's first value; each later term starts where the one before it ended.
// The line draws on to the end of each term, where a card with the change pops up.
// Under the chart, the term's timeline row counts along with the line.
// A ranking by president closes the reel.
// Frames are drawn on demand, and frame n is the same every time, so a recorder can take its time over each one.
// gettext is Django's, from the translation catalog base.html loads.
import {
  createStage, FONT, imageWell, loadImage, MONO, paintGround, paintRoundFlag, paintWatermark, whenFinished, wrap,
} from './chart-image.js';
import { formatAmount, formatValue, shortRule } from './format.js';
import { BRIDGE } from './gaps.js';
import { createTermChart, paintLogoTile, paintTrend } from './term-chart.js';
import { groupRows, logoCredits, paintRow, ROW, timelineRows } from './timeline.js';

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
    brand: true,  // the gear and the name again, large, in the band under the row
  },
  // YouTube and LinkedIn, on a computer. Nothing lies over the frame for long, so margins are enough.
  // The chart's own watermark is the only brand: there is no band under the row to hold a second one.
  wide: {
    width: 1920, height: 1080, pad: 64, scale: 1.6, cardZoom: 1.7, nowZoom: 1.6, rankZoom: 1.5,
    safe: { top: 56, bottom: 1080 - 48, right: 1920 - 64 },
    type: { title: 72, flag: 66, subtitle: 28, explanation: 24, explanationLines: 2, year: 300 },
    brand: false,
  },
};

// The pace, in seconds.
const TIME = {
  intro: 1.2,  // the empty chart, before the line sets off
  pop: 0.4,  // a card popping up
  fade: 0.35,  // a card fading away
  start: 2.2,  // the first term's start card, held to be read
  end: 3,  // an end-of-term card, held to be read
  year: 0.5,  // the line, per year
  travel: 1.4,  // the line, for one term at least
  swap: 0.45,  // the timeline row of one term giving way to the next
  outro: 6,  // the ranking, held to be read when it fits
  rankTop: 2.5,  // a ranking too long to fit, held at its top
  rankEnd: 3,  // and at its end, once it has scrolled
};
const SCROLL = 110;  // px a second, for a ranking too long to fit

const INK = '#f2f3f4';
const INK_2 = '#b6b9bd';
const INK_3 = '#8b8f94';
const RULE = '#3a3d41';
const WELL = '#1d1f21';
const CARD = 'rgba(23, 25, 27, 0.95)';
const PANEL = 'rgb(23, 25, 27)';  // the ranking's panel, solid over the chart it replaces
const NOBODY = '#999999';

const clamp = (v) => Math.min(1, Math.max(0, v));
const easeOut = (v) => 1 - (1 - v) ** 3;
const easeInOut = (v) => (v < 0.5 ? 4 * v ** 3 : 1 - (-2 * v + 2) ** 3 / 2);

/**
 * Builds a reel for one series, in one of the FORMATS.
 * `data` is the country page's data for the chosen years (politics/views.py, country_data), and `range` those years.
 * Resolves to { canvas, frames, draw(n) }: draw(n) paints frame n on the canvas.
 */
export async function createReel({ format = 'reel', data, range, units, title, flag, subtitle, explanation, rankingTitle, source }) {
  const F = FORMATS[format];
  await fontsReady();
  const terms = data.presidencies.filter((p) => p.summary && p.inWindow !== false);
  const ranking = groupRows(data, 'president');
  const rows = new Map(timelineRows(data).map((row) => [row.presidency, row]));
  const parties = [...terms.flatMap(partiesOf), ...ranking.flatMap((row) => row.logos), ...[...rows.values()].flatMap((row) => row.logos)];
  const logos = new Map(await Promise.all([...new Set(parties.map((party) => party.logo).filter(Boolean))]
    .map(async (src) => [src, await loadImage(src)])));
  // A logo whose licence asks for credit is credited wherever it is shown, so the reel names it under the source.
  const credits = logoCredits([{ logos: parties }]);

  // From the top: the title, the chart's well, the source, and the timeline row of the term the line is in.
  // The row is as wide as the well, so the two line up.
  const base = canvasOf(F);
  const baseCtx = base.getContext('2d');
  paintGround(baseCtx, F.width, F.height);
  const top = paintHeader(baseCtx, F, { title, flag: await loadImage(flag), unit: data.measuredIn, subtitle, explanation }) + 36;
  const bottom = F.safe.bottom - (ROW + 12) * F.nowZoom - 24;
  const sourceTop = paintFooter(baseCtx, F, [source, credits], bottom);
  const { well, inner } = imageWell(baseCtx, top, sourceTop - 28 - top, { width: F.width, pad: F.pad });
  const nowBox = { x: well.x, w: well.w, y: bottom + 24, h: (ROW + 12) * F.nowZoom };
  await paintWatermark(baseCtx, well);
  if (F.brand) await paintBrand(baseCtx, F);
  const chart = await chartLayers(data, range, units, inner, F.scale);

  const rank = rankingLayout(baseCtx, ranking, well, F.rankZoom);
  const story = storyboard(terms, range);
  const outroLength = rank.overflow ? 0.6 + TIME.rankTop + rank.overflow / SCROLL + TIME.rankEnd : 0.6 + TIME.outro;
  const frames = Math.ceil((story.outro + (ranking.length ? outroLength : 0)) * FPS) + 1;
  const now = nowLayout(baseCtx, terms, data, units, chart, nowBox);
  const canvas = canvasOf(F);
  const ctx = canvas.getContext('2d');
  const colourAt = (year) => {
    const p = data.presidencies.find((term) => term.spans.length && term.spans[0].from < year && year <= term.spans.at(-1).to);
    return p ? p.spans.at(-1).party.color : NOBODY;
  };

  function draw(n) {
    const t = n / FPS;
    const year = story.yearAt(t);
    const tipX = chart.x(year);
    ctx.drawImage(base, 0, 0);
    paintYear(ctx, F, chart.plot, Math.floor(year + 1e-6));
    ctx.globalAlpha = easeOut(clamp(t / 0.8));
    ctx.drawImage(chart.axes, inner.x, inner.y, inner.w, inner.h);
    ctx.globalAlpha = 1;
    ctx.save();
    ctx.beginPath();
    ctx.rect(inner.x, inner.y, Math.max(0, tipX - inner.x), inner.h);
    ctx.clip();
    ctx.drawImage(chart.line, inner.x, inner.y, inner.w, inner.h);
    ctx.restore();
    paintMarks(ctx, terms, chart, year);
    const tip = chart.yAt(year);
    if (tip !== null) paintTip(ctx, tipX, tip, colourAt(year));
    for (const card of story.cards) paintCard(ctx, F, card, t, chart, tipX, logos);
    paintNow(ctx, F, now, story, t, year, rows, logos);
    const outro = clamp((t - story.outro) / 0.6);
    if (outro > 0 && ranking.length) {
      const scrolled = rank.overflow ? easeInOut(clamp((t - story.outro - 0.6 - TIME.rankTop) / (rank.overflow / SCROLL))) : 0;
      paintRanking(ctx, ranking, rank, easeOut(outro), scrolled * rank.overflow, rankingTitle, logos);
    }
  }

  return { canvas, frames, draw };
}

// ---------- The story: where the line's tip is, and which card shows, at each moment ----------
// The line's tip sets off at the first year.
// It holds there with the first term's start card, then travels to each term's last year and holds with an end card.
// The ranking follows the last term.
function storyboard(terms, [first, last]) {
  const moves = [];
  const cards = [];
  const starts = [];  // when each term's timeline row takes over
  let t = TIME.intro;
  let at = first;
  const travel = (to) => {
    if (to <= at) return;
    const length = Math.max(TIME.travel, (to - at) * TIME.year);
    moves.push({ from: at, to, t0: t, t1: t + length });
    t += length;
    at = to;
  };
  terms.forEach((p, i) => {
    const s = p.summary;
    travel(s.startYear);
    starts.push({ p, t });
    if (i === 0) {
      // The start card fades as the line sets off.
      cards.push({ kind: 'start', p, year: s.startYear, value: s.startValue, t0: t, t1: t + TIME.pop + TIME.start });
      t += TIME.pop + TIME.start;
    }
    travel(s.endYear);
    cards.push({ kind: 'end', p, year: s.endYear, value: s.endValue, t0: t, t1: t + TIME.pop + TIME.end });
    t += TIME.pop + TIME.end + TIME.fade;
  });
  travel(last);
  const yearAt = (now) => {
    let year = first;
    for (const move of moves) {
      if (now >= move.t1) year = move.to;
      else if (now > move.t0) return move.from + (move.to - move.from) * easeInOut((now - move.t0) / (move.t1 - move.t0));
      else break;
    }
    return year;
  };
  return { cards, starts, yearAt, outro: t };
}

// ---------- The chart, drawn once in two layers ----------
// The axes alone, and the line alone, each as an image. A frame shows the axes and the line up to its tip.
async function chartLayers(data, range, units, inner, scale) {
  const stage = createStage(inner.w / scale, inner.h / scale);
  try {
    const term = createTermChart(stage.element, { units, animate: false, slider: false });
    const settle = async (change) => {
      const finished = whenFinished(term.chart);
      change();
      await finished;
    };
    const snapshot = () => loadImage(term.chart.getDataURL({
      type: 'png', pixelRatio: scale, backgroundColor: 'rgba(0,0,0,0)', excludeComponents: ['dataZoom'],
    }));
    await settle(() => term.render(data, range));
    await settle(() => term.chart.setOption({ series: [{ lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 } }, { itemStyle: { opacity: 0 } }] }));
    const axes = await snapshot();
    // The line's axes keep their room but take no colour, so the two layers line up.
    const none = 'rgba(0, 0, 0, 0)';
    await settle(() => term.render(data, range));
    await settle(() => term.chart.setOption({
      xAxis: { axisLabel: { color: none }, axisLine: { lineStyle: { color: none } } },
      yAxis: { axisLabel: { color: none }, splitLine: { lineStyle: { color: none } } },
      series: [{ markLine: { lineStyle: { opacity: 0 } } }],
    }));
    const line = await snapshot();

    // Both axes are linear, so two points fix where any year and value land on the reel.
    const at = (point) => {
      const [x, y] = term.chart.convertToPixel({ seriesIndex: 0 }, point);
      return [inner.x + x * scale, inner.y + y * scale];
    };
    const [x0, y0] = at([range[0], 0]);
    const [x1, y1] = at([range[1], 1]);
    const x = (year) => x0 + ((year - range[0]) * (x1 - x0)) / (range[1] - range[0]);
    const y = (value) => y0 + value * (y1 - y0);
    const rect = term.chart.getModel().getComponent('grid', 0).coordinateSystem.getRect();
    const plot = {
      left: inner.x + rect.x * scale, top: inner.y + rect.y * scale,
      right: inner.x + (rect.x + rect.width) * scale, bottom: inner.y + (rect.y + rect.height) * scale,
    };
    term.dispose();
    const points = data.points.filter(([year]) => year >= range[0] && year <= range[1]);
    // The line's value at a year, between two values no further apart than BRIDGE years; null in an open gap.
    const valueAt = (year) => {
      for (let i = 0; i < points.length; i += 1) {
        const [ya, va] = points[i];
        if (ya === year) return va;
        const next = points[i + 1];
        if (next && ya < year && year < next[0]) {
          return next[0] - ya > BRIDGE ? null : va + ((next[1] - va) * (year - ya)) / (next[0] - ya);
        }
      }
      return null;
    };
    const yAt = (year) => {
      const value = valueAt(year);
      return value === null ? null : y(value);
    };
    return { axes, line, plot, x, y, valueAt, yAt, points };
  } finally {
    stage.remove();
  }
}

// ---------- Painting a frame ----------
// The country's round flag, then the title with the unit its values are in, in grey after it.
// Under them, the subtitle and the metric's explanation.
function paintHeader(ctx, F, { title, flag, unit, subtitle, explanation }) {
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
  if (explanation) {
    ctx.fillStyle = INK_3;
    ctx.font = `400 ${T.explanation}px ${FONT}`;
    y += 14;
    for (const line of wrap(ctx, explanation, F.width - 2 * F.pad, T.explanationLines)) {
      ctx.fillText(line, F.pad, y);
      y += T.explanation + 10;
    }
  }
  return y;
}

// The source, small, ending at `bottom`. It keeps clear of Instagram's buttons at the right. Returns its top.
function paintFooter(ctx, F, sources, bottom) {
  ctx.font = `400 22px ${FONT}`;
  const lines = sources.filter(Boolean).flatMap((text) => wrap(ctx, text, F.safe.right - F.pad, 3));
  const top = bottom - lines.length * 30;
  ctx.textBaseline = 'top';
  ctx.fillStyle = INK_3;
  lines.forEach((line, i) => ctx.fillText(line, F.pad, top + i * 30));
  return top;
}

// The gear and the name in the band Instagram covers with the caption: the frame stays whole when nothing does.
async function paintBrand(ctx, F) {
  const logo = await loadImage(document.querySelector('link[rel="icon"]')?.href);
  ctx.save();
  ctx.globalAlpha = 0.55;
  ctx.font = `700 34px ${FONT}`;
  ctx.textBaseline = 'middle';
  const name = 'Data Mechanics';
  const width = 64 + 18 + ctx.measureText(name).width;
  const x = (F.width - width) / 2;
  const y = F.safe.bottom + (F.height - F.safe.bottom) / 2;
  if (logo) ctx.drawImage(logo, x, y - 32, 64, 64);
  ctx.fillStyle = INK;
  ctx.fillText(name, x + 64 + 18, y + 2);
  ctx.restore();
}

// The year the line has reached, very large and faint behind the chart.
function paintYear(ctx, F, plot, year) {
  ctx.save();
  ctx.font = `700 condensed ${F.type.year}px ${FONT}`;
  ctx.textAlign = 'right';
  ctx.textBaseline = 'top';
  ctx.fillStyle = 'rgba(242, 243, 244, 0.05)';
  ctx.fillText(String(year), plot.right - 8, plot.top - 4);
  ctx.restore();
}

// A white dot where each term the line has passed began and ended, like the site's dots.
function paintMarks(ctx, terms, chart, year) {
  const seen = new Set();
  for (const p of terms) {
    for (const [at, value] of [[p.summary.startYear, p.summary.startValue], [p.summary.endYear, p.summary.endValue]]) {
      if (at >= year - 1e-6 || seen.has(at)) continue;
      seen.add(at);
      dot(ctx, chart.x(at), chart.y(value), 9, WELL);
      dot(ctx, chart.x(at), chart.y(value), 6.5, INK);
    }
  }
}

// The line's tip: a glowing dot in the colour of the party in office.
function paintTip(ctx, x, y, colour) {
  ctx.save();
  ctx.shadowColor = colour;
  ctx.shadowBlur = 30;
  dot(ctx, x, y, 12, colour);
  ctx.restore();
  dot(ctx, x, y, 5, INK);
}

function dot(ctx, x, y, r, colour) {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, 2 * Math.PI);
  ctx.fillStyle = colour;
  ctx.fill();
}

// ---------- Cards ----------
// A term's start party, then its end party (a leader may have changed party in office).
function partiesOf(p) {
  return [p.spans[0]?.party || p.party, p.spans.at(-1)?.party || p.party];
}

// A card pops up beside its point, moves out into place and holds; then it fades.
// It sits where it covers the least of the line drawn so far, inside the chart and clear of Instagram's buttons (placeCard).
function paintCard(ctx, F, card, t, chart, tipX, logos) {
  const popped = easeOut(clamp((t - card.t0) / TIME.pop));
  const shown = popped * (1 - clamp((t - card.t1) / TIME.fade));
  if (shown <= 0) return;
  const layout = cardLayout(ctx, card);
  const w = layout.w * F.cardZoom;
  const h = layout.h * F.cardZoom;
  const px = chart.x(card.year);
  const py = chart.y(card.value);
  const box = placeCard(chart, px, py, w, h, tipX, F.safe.right);
  // The stem runs from the point to the nearest spot on the card's edge.
  const sx = Math.min(Math.max(px, box.left + 20), box.left + w - 20);
  const sy = Math.min(Math.max(py, box.top), box.top + h);
  const length = Math.hypot(sx - px, sy - py) || 1;
  const [ux, uy] = [(sx - px) / length, (sy - py) / length];

  ctx.save();
  ctx.globalAlpha = shown;
  ctx.strokeStyle = layout.party.color;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(px + ux * 15, py + uy * 15);
  ctx.lineTo(sx, sy);
  ctx.stroke();
  // As it appears the card moves 18 px out from its point and grows from its stem's end.
  const back = (1 - popped) * 18;
  const grow = 0.94 + 0.06 * shown;
  ctx.translate(sx - ux * back, sy - uy * back);
  ctx.scale(grow, grow);
  ctx.translate(-sx, -sy);
  ctx.translate(box.left, box.top);
  ctx.scale(F.cardZoom, F.cardZoom);
  layout.paint(ctx, logos);
  ctx.restore();
}

// The card's place: a spot around its point, beside it or pushed against the chart's edges.
// Each value of the drawn line a spot covers counts as 180 px of distance, so a near spot over a little of the line beats a far one with a long stem across the chart.
// Spots more than 260 px away count only when nothing nearer fits.
// Above the point wins a tie.
function placeCard(chart, px, py, w, h, tipX, safeRight) {
  const { plot } = chart;
  const within = (v, lo, hi) => Math.min(Math.max(v, lo), hi);
  const [minLeft, maxLeft] = [plot.left + 8, Math.min(plot.right, safeRight) - w];
  const [minTop, maxTop] = [plot.top + 4, plot.bottom - h - 4];
  const lefts = [px - w / 2, px - w - 56, px + 56, minLeft, maxLeft].map((left) => within(left, minLeft, maxLeft));
  const tops = [py - 56 - h, py + 56, py - h / 2, minTop, maxTop].map((top) => within(top, minTop, maxTop));
  const gap = (box) => Math.hypot(Math.max(box.left - px, 0, px - box.left - w), Math.max(box.top - py, 0, py - box.top - h));
  const boxes = lefts.flatMap((left) => tops.map((top) => ({ left, top }))).filter((box) => gap(box) >= 30);
  const covered = (box) => chart.points.filter(([year, value]) => {
    const x = chart.x(year);
    const y = chart.y(value);
    return x <= tipX && x >= box.left - 12 && x <= box.left + w + 12 && y >= box.top - 12 && y <= box.top + h + 12;
  }).length;
  const cost = (box) => covered(box) * 180 + gap(box) + (box.top + h <= py ? 0 : 40);
  const near = boxes.filter((box) => gap(box) <= 260);
  const pool = near.length ? near : boxes;
  if (!pool.length) return { left: within(px - w / 2, minLeft, maxLeft), top: minTop };
  return pool.reduce((best, box) => (cost(box) < cost(best) ? box : best));
}

// A card laid out like the site's .term-label, in CSS pixels; paintCard scales it by the format's cardZoom.
// It holds the logo tile, a kicker with the moment and year, and the name and party.
// The first term's start card then gives the value, large.
// An end card gives the change, large, with the value it ended at small under it: the change is the story.
function cardLayout(ctx, { kind, p }) {
  const s = p.summary;
  const start = kind === 'start';
  const [startParty, endParty] = partiesOf(p);
  const party = start ? startParty : endParty;
  const moment = start ? gettext('Start of term') : p.current ? gettext('In office') : gettext('End of term');
  const kicker = `${moment} · ${start ? s.startYear : s.endYear}`.toUpperCase();
  const partyName = ` · ${party.abbreviation || party.name}`;
  const value = start ? s.startLabel : s.endLabel;
  const width = (font, text) => {
    ctx.font = font;
    return ctx.measureText(text).width;
  };
  const kickerW = width(`600 9px ${MONO}`, kicker);
  const nameW = width(`700 16px ${FONT}`, p.shortName);
  const partyW = width(`500 13px ${FONT}`, partyName);
  const valueW = width(start ? `700 19px ${MONO}` : `500 11px ${MONO}`, value);
  const changeW = start ? 0 : trendWidth(ctx, s, CARD_TREND);
  const text = Math.max(kickerW, nameW + partyW, valueW, changeW);
  const w = 12 + 40 + 12 + text + 18;
  const h = start ? 80 : 104;
  const paint = (c, logos) => {
    c.beginPath();
    c.roundRect(0, 0, w, h, 10);
    c.fillStyle = CARD;
    c.fill();
    c.save();
    c.clip();
    c.fillStyle = party.color;
    c.fillRect(w - 4, 0, 4, h);
    c.restore();
    c.beginPath();
    c.roundRect(0.5, 0.5, w - 1, h - 1, 10);
    c.strokeStyle = RULE;
    c.lineWidth = 1;
    c.stroke();
    paintLogoTile(c, party, logos.get(party.logo), 12, (h - 40) / 2, 40);
    const x = 64;
    c.textBaseline = 'middle';
    c.font = `600 9px ${MONO}`;
    c.fillStyle = INK_3;
    c.fillText(kicker, x, 19);
    c.font = `700 16px ${FONT}`;
    c.fillStyle = INK;
    c.fillText(p.shortName, x, 39);
    c.font = `500 13px ${FONT}`;
    c.fillStyle = INK_2;
    c.fillText(partyName, x + nameW, 39.5);
    if (start) {
      c.font = `700 19px ${MONO}`;
      c.fillStyle = INK;
      c.fillText(value, x, 61);
      return;
    }
    paintLargeTrend(c, s, x, 64, CARD_TREND);
    c.font = `500 11px ${MONO}`;
    c.fillStyle = INK_2;
    c.textBaseline = 'middle';
    c.fillText(value, x, 89);
  };
  return { w, h, party, paint };
}

// ---------- The term the line is in, under the chart ----------
// Its timeline row from the page, without the data bar, counting along with the line.
// It gives the start value, the value the line has reached, and the change so far.
// When the next term begins, its row takes this one's place.
function nowLayout(ctx, terms, data, units, chart, box) {
  const rule = units[data.unit];
  const live = (p, year) => {
    const s = p.summary;
    if (year >= s.endYear - 1e-6) return s;
    const value = chart.valueAt(Math.max(year, s.startYear)) ?? s.startValue;
    const amount = s.relative ? ((value - s.startValue) / s.startValue) * 100 : value - s.startValue;
    // As politics/queries.py's change_summary writes it: a fall starts with a minus sign.
    const size = formatAmount(amount, rule, data.unit, s.relative);
    const moved = /[1-9]/.test(size);
    const up = moved ? amount > 0 : null;
    return {
      ...s,
      endLabel: formatValue(value, shortRule(rule)),
      amount: moved ? amount : 0,
      change: moved ? `${amount < 0 ? '-' : ''}${size}` : '',
      up,
      good: moved && data.better ? up === (data.better === 'higher') : null,
    };
  };
  const passes = terms.flatMap((p) => chart.points
    .filter(([year]) => year >= p.summary.startYear && year <= p.summary.endYear)
    .map(([year]) => live(p, year)));
  ctx.font = `700 12px ${MONO}`;
  const trendWidth = Math.max(0, ...passes.map((s) => (s.change ? 20 + ctx.measureText(s.change).width : 0)));
  return { box, live, trendWidth };
}

function paintNow(ctx, F, now, story, t, year, rows, logos) {
  const { box } = now;
  const width = box.w / F.nowZoom - 22;
  const half = TIME.swap / 2;
  // The panel stays from the first term to the ranking; only the row inside it changes.
  const panel = easeOut(clamp((t - story.starts[0].t) / TIME.swap)) * (1 - clamp((t - story.outro) / TIME.swap));
  if (!story.starts.length || panel <= 0) return;
  ctx.save();
  ctx.globalAlpha = panel;
  ctx.beginPath();
  ctx.roundRect(box.x, box.y, box.w, box.h, 14);
  ctx.fillStyle = CARD;
  ctx.fill();
  ctx.strokeStyle = RULE;
  ctx.lineWidth = 1.5;
  ctx.stroke();
  ctx.restore();
  // One row at a time: the old one rises out, then the new one rises in.
  story.starts.forEach(({ p, t: from }, i) => {
    const until = story.starts[i + 1]?.t ?? Infinity;
    const enter = i ? easeOut(clamp((t - from - half) / half)) : 1;
    const leave = 1 - easeOut(clamp((t - until) / half));
    const shown = Math.min(enter, leave) * panel;
    if (shown <= 0 || t < from) return;
    const lift = enter < 1 ? (1 - enter) * 14 : -(1 - leave) * 14;
    const row = rows.get(p);
    ctx.save();
    ctx.globalAlpha = shown;
    ctx.beginPath();
    ctx.rect(box.x, box.y, box.w, box.h);
    ctx.clip();
    ctx.translate(box.x, box.y + lift);
    ctx.scale(F.nowZoom, F.nowZoom);
    ctx.translate(12, 6);
    const summary = now.live(p, year);
    paintRow(ctx, { ...row, presidency: { ...row.presidency, summary } }, 0,
      { width, trendWidth: now.trendWidth, scale: null }, logos, { first: true, last: true });
    // "Change since start", small, over the change.
    if (summary.change) {
      ctx.font = `600 8px ${MONO}`;
      ctx.fillStyle = INK_3;
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillText(sinceLabel(), width, ROW / 2 - 15);
      ctx.textAlign = 'left';
    }
    ctx.restore();
  });
}

// ---------- The ranking that closes the reel ----------
// The chart dims, and the leaders of the chosen years rank by their average change per year, as on the page.
// A ranking too long for the well scrolls, slowly, from its top to its end.
const RANK_ROW = 58;
const RANK_HEAD = 48;

// The panel takes the chart's place exactly: the well's width and height.
function rankingLayout(ctx, rows, well, zoom) {
  const box = { x: well.x, y: well.y, w: well.w, h: well.h };
  const css = { w: box.w / zoom, h: box.h / zoom };
  const list = rows.length * RANK_ROW + 10;
  const room = css.h - RANK_HEAD;
  const changeW = (summary) => trendWidth(ctx, summary, RANK_TREND);
  const heads = { perYear: gettext('Per year').toUpperCase(), total: gettext('Total').toUpperCase() };
  const headW = (text) => {
    ctx.font = `600 9px ${MONO}`;
    return ctx.measureText(text).width;
  };
  const totalW = Math.max(...rows.map((row) => changeW(row.total)), headW(heads.total));
  const perYearW = Math.max(...rows.map((row) => changeW(row.perYear)), headW(heads.perYear));
  const totalRight = css.w - 18;
  return {
    box, css, zoom, heads, changeW, totalRight, perYearRight: totalRight - totalW - 22, perYearW,
    overflow: Math.max(0, list - room) * zoom,
  };
}

function paintRanking(ctx, rows, layout, shown, scrolled, title, logos) {
  const { box, css, zoom, heads, changeW, totalRight, perYearRight, perYearW } = layout;
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
  ctx.fillText(heads.perYear, perYearRight, 27);
  ctx.fillText(heads.total, totalRight, 27);
  ctx.textAlign = 'left';

  // The rows, scrolled by `scrolled` reel pixels, inside the panel under its head.
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, RANK_HEAD, css.w, css.h - RANK_HEAD - 4);
  ctx.clip();
  ctx.translate(0, -scrolled / zoom);
  rows.forEach((row, i) => {
    const y = RANK_HEAD + i * RANK_ROW;
    ctx.strokeStyle = RULE;
    ctx.globalAlpha = shown * 0.6;
    ctx.beginPath();
    ctx.moveTo(18, y);
    ctx.lineTo(css.w - 18, y);
    ctx.stroke();
    ctx.globalAlpha = shown;
    ctx.font = `500 11px ${MONO}`;
    ctx.fillStyle = INK_3;
    ctx.fillText(String(row.rank), 18, y + RANK_ROW / 2);
    // A leader's parties, overlapping like the page's logo tiles.
    row.logos.slice(0, 2).forEach((party, k) => {
      const x = 36 + k * 22;
      if (k) {
        ctx.beginPath();
        ctx.roundRect(x - 2, y + (RANK_ROW - 40) / 2, 40, 40, 9);
        ctx.fillStyle = CARD;
        ctx.fill();
      }
      paintLogoTile(ctx, party, logos.get(party.logo), x, y + (RANK_ROW - 36) / 2, 36);
    });
    const textX = 82 + 22 * (Math.min(row.logos.length, 2) - 1);
    const room = perYearRight - perYearW - 16 - textX;
    ctx.font = `700 15px ${FONT}`;
    ctx.fillStyle = INK;
    ctx.fillText(wrap(ctx, row.name, room, 1)[0], textX, y + 21);
    ctx.font = `500 10px ${MONO}`;
    ctx.fillStyle = INK_3;
    ctx.fillText(wrap(ctx, row.sub || row.aside, room, 1)[0] || '', textX, y + 40);
    paintLargeTrend(ctx, row.perYear, perYearRight - changeW(row.perYear), y + RANK_ROW / 2, RANK_TREND);
    paintLargeTrend(ctx, row.total, totalRight - changeW(row.total), y + RANK_ROW / 2, RANK_TREND);
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

// ---------- Helpers ----------
const CARD_TREND = 1.75;  // the change on an end card, 1.75 times the site's size
const RANK_TREND = 1.35;  // the changes in the ranking

// The site's change (term-chart.js, paintTrend) at `k` times its size: the arrow in its circle, then the number.
function paintLargeTrend(ctx, summary, x, y, k) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(k, k);
  paintTrend(ctx, summary, 0, 0);
  ctx.restore();
}

function trendWidth(ctx, summary, k) {
  ctx.font = `700 12px ${MONO}`;
  return (ctx.measureText(summary.change).width + (summary.up === null ? 0 : 20)) * k;
}

// The words beside a term's change: it runs from the term's start to its end, or to the year the line has reached.
const sinceLabel = () => gettext('Change since start').toUpperCase();

function canvasOf(F) {
  const canvas = document.createElement('canvas');
  canvas.width = F.width;
  canvas.height = F.height;
  return canvas;
}

async function fontsReady() {
  await Promise.all([`700 condensed 84px ${FONT}`, `500 30px ${FONT}`, `400 22px ${FONT}`, `700 16px ${FONT}`,
    `700 14px ${MONO}`, `600 9px ${MONO}`].map((font) => document.fonts.load(font).catch(() => null)));
}
