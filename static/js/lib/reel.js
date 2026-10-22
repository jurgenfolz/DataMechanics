// A Politics reel: the chart replayed as a video, 1080 × 1920 for Instagram Reels or 1920 × 1080 for YouTube and LinkedIn.
// tools/reel.py records it.
// The line runs through the chosen years.
// The first term opens with a card at the line's first value; each later term starts where the one before it ended.
// The line draws on to the end of each term, where a card with the change pops up.
// Under the chart, the term's timeline row counts along with the line.
// Then the comparison group's dashed line (politics/comparison.py) draws the same way, more quietly, and at each term's
// end a card sets the country's value beside the group's: changes can mislead there, since a fast rise can still end
// below the group.
// A ranking by president closes the reel: by change per year, or, with a group, by how far ahead of it each leader
// left the country.
// Without a comparison group the reel has neither the group's pass nor its values.
// Frames are drawn on demand, and frame n is the same every time, so a recorder can take its time over each one.
// gettext and interpolate are Django's, from the translation catalog base.html loads.
import {
  createStage, FONT, imageWell, loadImage, MONO, paintBrandName, paintGround, paintRoundFlag, paintWatermark, whenFinished, wrap,
} from './chart-image.js';
import { formatAmount, formatValue, shortRule } from './format.js';
import { BRIDGE } from './gaps.js';
import { createTermChart, GROUP_COLOR, paintLogoTile, paintTrend } from './term-chart.js';
import { groupRows, logoCredits, paintRow, ROW, timelineRows, valueRange } from './timeline.js';

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
  compareGap: 1,  // between the country's line and the group's
  win: 0.75,  // on a comparison card, when the better change's highlight sets off
  trace: 0.6,  // its outline drawing itself around the row
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
const BETTER = '#2bc892';  // Better Green, the site's colour for a good change
const CARD_TREND = 1.75;  // the change on an end card, 1.75 times the site's size
const RANK_TREND = 1.35;  // the changes in the ranking

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
  // The group's pass needs its dashed line, and its value at the end of the terms it covers.
  const compared = Boolean(data.comparison && data.comparison.points.length > 1 && terms.some((p) => p.summary.compare));
  const ranking = compared ? byLead(groupRows(data, 'president')) : groupRows(data, 'president');
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
  const chart = await chartLayers(data, range, units, inner, F.scale, compared);

  const columns = compared ? valueColumns(data) : changeColumns();
  const rank = rankingLayout(baseCtx, ranking, well, F.rankZoom, columns, compared ? 32 : 22);
  const story = storyboard(terms, range, compared ? data.comparison : null);
  const outroLength = rank.overflow ? 0.6 + TIME.rankTop + rank.overflow / SCROLL + TIME.rankEnd : 0.6 + TIME.outro;
  const frames = Math.ceil((story.outro + (ranking.length ? outroLength : 0)) * FPS) + 1;
  const now = nowLayout(baseCtx, terms, data, units, chart, nowBox);
  const group = { label: data.comparison?.short, country: data.country, better: data.better };
  const canvas = canvasOf(F);
  const ctx = canvas.getContext('2d');
  const colourAt = (year) => {
    const p = data.presidencies.find((term) => term.spans.length && term.spans[0].from < year && year <= term.spans.at(-1).to);
    return p ? p.spans.at(-1).party.color : NOBODY;
  };

  // A layer revealed from the plot's left edge up to `x`.
  const reveal = (layer, x) => {
    ctx.save();
    ctx.beginPath();
    ctx.rect(inner.x, inner.y, Math.max(0, x - inner.x), inner.h);
    ctx.clip();
    ctx.drawImage(layer, inner.x, inner.y, inner.w, inner.h);
    ctx.restore();
  };

  function draw(n) {
    const t = n / FPS;
    const year = story.yearAt(t);
    const tipX = chart.x(year);
    const comparing = compared && t >= story.compareStart;
    const groupYear = comparing ? story.groupYearAt(t) : null;
    ctx.drawImage(base, 0, 0);
    paintYear(ctx, F, chart.plot, Math.floor((comparing ? groupYear : year) + 1e-6));
    ctx.globalAlpha = easeOut(clamp(t / 0.8));
    ctx.drawImage(chart.axes, inner.x, inner.y, inner.w, inner.h);
    ctx.globalAlpha = 1;
    reveal(chart.line, tipX);
    paintMarks(ctx, terms, chart, year);
    // The line drawn so far, in pixels: cards keep off it.
    const drawn = chart.points.filter(([at]) => at <= year).map(([at, value]) => [chart.x(at), chart.y(value)]);
    if (comparing) {
      const groupX = chart.x(groupYear);
      ctx.globalAlpha = easeOut(clamp((t - story.compareStart) / 0.6));
      reveal(chart.group, groupX);
      ctx.globalAlpha = 1;
      const groupY = chart.groupYAt(groupYear);
      // A group far from the country runs off the chart (valueBounds in lib/term-chart.js); its tip goes with it.
      if (groupY !== null && groupY >= chart.plot.top && groupY <= chart.plot.bottom) paintTip(ctx, groupX, groupY, GROUP_COLOR, 0.6);
      drawn.push(...chart.groupPoints.filter(([at]) => at <= groupYear).map(([at, value]) => [chart.x(at), chart.y(value)]));
    } else {
      const tip = chart.yAt(year);
      if (tip !== null) paintTip(ctx, tipX, tip, colourAt(year));
    }
    for (const card of story.cards) paintCard(ctx, F, card, t, chart, drawn, logos, group);
    paintNow(ctx, F, now, story, t, year, rows, logos);
    const outro = clamp((t - story.outro) / 0.6);
    if (outro > 0 && ranking.length) {
      const scrolled = rank.overflow ? easeInOut(clamp((t - story.outro - 0.6 - TIME.rankTop) / (rank.overflow / SCROLL))) : 0;
      paintRanking(ctx, ranking, rank, easeOut(outro), scrolled * rank.overflow, rankingTitle, logos, t - story.outro);
    }
  }

  return { canvas, frames, draw };
}

// ---------- The story: where the line's tip is, and which card shows, at each moment ----------
// The line's tip sets off at the first year.
// It holds there with the first term's start card, then travels to each term's last year and holds with an end card.
// With a comparison group, the group's tip then makes the same journey, with a card at each term's end.
// The ranking follows.
function storyboard(terms, [first, last], comparison) {
  const moves = [];
  const groupMoves = [];
  const cards = [];
  const starts = [];  // when each term's timeline row takes over; `final` rows show the whole term
  let t = TIME.intro;
  let at = first;
  let tracks = moves;
  const travel = (to) => {
    if (to <= at) return;
    const length = Math.max(TIME.travel, (to - at) * TIME.year);
    tracks.push({ from: at, to, t0: t, t1: t + length });
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

  let compareStart = Infinity;
  if (comparison) {
    t += TIME.compareGap;
    compareStart = t;
    at = first;
    tracks = groupMoves;
    const groupAt = new Map(comparison.points);
    for (const p of terms) {
      const s = p.summary;
      starts.push({ p, t, final: true });
      travel(s.endYear);
      if (s.compare && groupAt.has(s.endYear)) {
        cards.push({ kind: 'compare', p, year: s.endYear, value: groupAt.get(s.endYear), t0: t, t1: t + TIME.pop + TIME.end });
        t += TIME.pop + TIME.end + TIME.fade;
      }
    }
    travel(last);
  }

  const along = (tracksOf) => (now) => {
    let year = first;
    for (const move of tracksOf) {
      if (now >= move.t1) year = move.to;
      else if (now > move.t0) return move.from + (move.to - move.from) * easeInOut((now - move.t0) / (move.t1 - move.t0));
      else break;
    }
    return year;
  };
  return { cards, starts, yearAt: along(moves), groupYearAt: along(groupMoves), compareStart, outro: t };
}

// ---------- The chart, drawn once in two layers ----------
// The axes alone, and the line alone, each as an image. A frame shows the axes and the line up to its tip.
async function chartLayers(data, range, units, inner, scale, compared) {
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
    // Series 0 is the country's line, 1 its lone dots, 2 the comparison group's dashed line (lib/term-chart.js).
    const hidden = { lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, itemStyle: { opacity: 0 } };
    await settle(() => term.render(data, range));
    await settle(() => term.chart.setOption({ series: [hidden, hidden, hidden] }));
    const axes = await snapshot();
    // The other layers' axes keep their room but take no colour, so the layers line up.
    const none = 'rgba(0, 0, 0, 0)';
    const bare = {
      xAxis: { axisLabel: { color: none }, axisLine: { lineStyle: { color: none } } },
      yAxis: { axisLabel: { color: none }, splitLine: { lineStyle: { color: none } } },
    };
    await settle(() => term.render(data, range));
    await settle(() => term.chart.setOption({ ...bare, series: [{ markLine: { lineStyle: { opacity: 0 } } }, {}, hidden] }));
    const line = await snapshot();
    let group = null;
    if (compared) {
      await settle(() => term.render(data, range));
      await settle(() => term.chart.setOption({ ...bare, series: [{ ...hidden, markLine: { lineStyle: { opacity: 0 } } }, hidden, {}] }));
      group = await snapshot();
    }

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
    // The group's line: its height at a year, straight between its yearly values.
    const groupPoints = (data.comparison?.points || []).filter(([year]) => year >= range[0] && year <= range[1]);
    const groupYAt = (year) => {
      const i = groupPoints.findIndex(([at]) => at >= year);
      if (i < 0) return null;
      const [yb, vb] = groupPoints[i];
      if (yb === year || i === 0) return yb === year ? y(vb) : null;
      const [ya, va] = groupPoints[i - 1];
      return yb - ya > BRIDGE ? null : y(va + ((vb - va) * (year - ya)) / (yb - ya));
    };
    return { axes, line, group, plot, x, y, valueAt, yAt, points, groupPoints, groupYAt };
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
  ctx.textBaseline = 'middle';
  const size = 32;
  const width = 64 + 18 + paintBrandName(ctx, 0, 0, size, { measure: true });
  const x = (F.width - width) / 2;
  const y = F.safe.bottom + (F.height - F.safe.bottom) / 2;
  if (logo) ctx.drawImage(logo, x, y - 32, 64, 64);
  paintBrandName(ctx, x + 64 + 18, y + 2, size);
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

// A line's tip: a glowing dot in the colour of the party in office, or `size` times smaller for the group's quieter line.
function paintTip(ctx, x, y, colour, size = 1) {
  ctx.save();
  ctx.shadowColor = colour;
  ctx.shadowBlur = 30 * size;
  dot(ctx, x, y, 12 * size, colour);
  ctx.restore();
  dot(ctx, x, y, 5 * size, size < 1 ? WELL : INK);
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
function paintCard(ctx, F, card, t, chart, drawn, logos, group) {
  const popped = easeOut(clamp((t - card.t0) / TIME.pop));
  const shown = popped * (1 - clamp((t - card.t1) / TIME.fade));
  if (shown <= 0) return;
  const layout = cardLayout(ctx, card, group);
  // A comparison card holds two changes, so it is drawn a little smaller to find room beside both lines.
  const zoom = F.cardZoom * (card.kind === 'compare' ? 0.85 : 1);
  const w = layout.w * zoom;
  const h = layout.h * zoom;
  const px = chart.x(card.year);
  const py = Math.min(Math.max(chart.y(card.value), chart.plot.top), chart.plot.bottom);
  const box = placeCard(chart, px, py, w, h, drawn, F.safe.right, card.kind === 'compare');
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
  ctx.scale(zoom, zoom);
  layout.paint(ctx, logos, t - card.t0);
  ctx.restore();
}

// The card's place: a spot around its point, beside it or pushed against the chart's edges.
// `drawn` holds the pixels of the lines drawn so far.
// Each value of the drawn line a spot covers counts as 180 px of distance, so a near spot over a little of the line beats a far one with a long stem across the chart.
// Spots more than 260 px away count only when nothing nearer fits, or, with `far`, when the near ones would cover the
// lines: a comparison card is large, and it must not hide the lines it compares.
// Above the point wins a tie.
function placeCard(chart, px, py, w, h, drawn, safeRight, far = false) {
  const { plot } = chart;
  const within = (v, lo, hi) => Math.min(Math.max(v, lo), hi);
  const [minLeft, maxLeft] = [plot.left + 8, Math.min(plot.right, safeRight) - w];
  const [minTop, maxTop] = [plot.top + 4, plot.bottom - h - 4];
  const lefts = [px - w / 2, px - w - 56, px + 56, minLeft, maxLeft].map((left) => within(left, minLeft, maxLeft));
  const tops = [py - 56 - h, py + 56, py - h / 2, minTop, maxTop].map((top) => within(top, minTop, maxTop));
  const gap = (box) => Math.hypot(Math.max(box.left - px, 0, px - box.left - w), Math.max(box.top - py, 0, py - box.top - h));
  const boxes = lefts.flatMap((left) => tops.map((top) => ({ left, top }))).filter((box) => gap(box) >= 30);
  const covered = (box) => drawn.filter(([x, y]) => x >= box.left - 12 && x <= box.left + w + 12
    && y >= box.top - 12 && y <= box.top + h + 12).length;
  const cost = (box) => covered(box) * 180 + gap(box) + (box.top + h <= py ? 0 : 40);
  const near = boxes.filter((box) => gap(box) <= 260);
  const best = (pool) => pool.reduce((winner, box) => (cost(box) < cost(winner) ? box : winner));
  if (!boxes.length) return { left: within(px - w / 2, minLeft, maxLeft), top: minTop };
  const nearest = near.length ? best(near) : null;
  if (nearest && !(far && covered(nearest))) return nearest;
  return best(boxes);
}

// A card laid out like the site's .term-label, in CSS pixels; paintCard scales it by the format's cardZoom.
// It holds the logo tile, a kicker with the moment and year, and the name and party.
// The first term's start card then gives the value, large.
// An end card gives the change, large, with the value it ended at small under it: the change is the story.
// A comparison card gives the term's change and the group's, each beside its name (compareLayout).
function cardLayout(ctx, card, group) {
  if (card.kind === 'compare') return compareLayout(ctx, card, group);
  const { kind, p } = card;
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

// The comparison card: the end card's head, then the country's value and the group's at the end of the term.
// Once the card is up, a green outline draws itself around the better value, which turns green, and a check pops onto
// the outline's corner.
function compareLayout(ctx, { p }, group) {
  const s = p.summary;
  const party = partiesOf(p)[1];
  const moment = p.current ? gettext('In office') : gettext('End of term');
  const kicker = `${moment} · ${s.endYear}`.toUpperCase();
  const partyName = ` · ${party.abbreviation || party.name}`;
  const rows = [
    { name: String(group.country).toUpperCase(), end: { value: s.endValue, label: s.endLabel }, y: 72 },
    { name: String(group.label).toUpperCase(), end: { value: s.compare.endValue, label: s.compare.endLabel }, y: 106 },
  ];
  const winner = rows[winnerOf(rows[0].end, rows[1].end, group.better)];
  const valueFont = `700 ${12 * CARD_TREND}px ${MONO}`;
  const width = (font, text) => {
    ctx.font = font;
    return ctx.measureText(text).width;
  };
  const nameW = width(`700 16px ${FONT}`, p.shortName);
  const labelW = Math.max(...rows.map((row) => width(`600 9px ${MONO}`, row.name)));
  const valueW = Math.max(...rows.map((row) => width(valueFont, row.end.label)));
  const text = Math.max(width(`600 9px ${MONO}`, kicker), nameW + width(`500 13px ${FONT}`, partyName), labelW + 16 + valueW);
  const w = 12 + 40 + 12 + text + 18;
  const h = 126;
  const paint = (c, logos, age) => {
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
    paintLogoTile(c, party, logos.get(party.logo), 12, 16, 40);
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
    const traced = winner ? paintWinner(c, { x: 56, y: winner.y - 15, w: w - 68, h: 30 }, age - TIME.win) : 0;
    for (const row of rows) {
      c.font = `600 9px ${MONO}`;
      c.fillStyle = INK_3;
      c.fillText(row.name, x, row.y);
      paintValue(c, row.end.label, x + labelW + 16 + valueW, row.y, valueFont, row === winner ? traced : 0);
    }
  };
  return { w, h, party, paint };
}

// A value right-aligned at `right`, in Bright Ink, turning `green` of the way to Better Green as it wins.
function paintValue(c, text, right, y, font, green) {
  c.save();
  c.font = font;
  c.textAlign = 'right';
  c.textBaseline = 'middle';
  c.fillStyle = INK;
  c.fillText(text, right, y);
  if (green > 0) {
    c.globalAlpha *= green;
    c.fillStyle = BETTER;
    c.fillText(text, right, y);
  }
  c.restore();
}

// Which of two values ({ value, label }) is better for the metric: 0 for `a`, 1 for `b`, -1 for neither.
// The higher wins, or the lower where lower is better. Neither wins when the metric has no better direction, or when
// both read the same.
function winnerOf(a, b, better) {
  if (!better || !a || !b || a.label === b.label) return -1;
  const higher = a.value > b.value ? 0 : 1;
  return better === 'higher' ? higher : 1 - higher;
}

// The winner's highlight, `age` seconds after it sets off: a green outline traces the box, the box takes a green tint,
// and a check pops onto its top-left corner. Returns how far the outline has traced, from 0 to 1.
function paintWinner(c, box, age) {
  if (age <= 0) return 0;
  const traced = easeOut(clamp(age / TIME.trace));
  const radius = 8;
  const around = 2 * (box.w + box.h) - (8 - 2 * Math.PI) * radius;
  c.save();
  c.globalAlpha *= 0.1 * traced;
  c.beginPath();
  c.roundRect(box.x, box.y, box.w, box.h, radius);
  c.fillStyle = BETTER;
  c.fill();
  c.restore();
  c.save();
  c.beginPath();
  c.roundRect(box.x, box.y, box.w, box.h, radius);
  c.setLineDash([around * traced, around]);
  c.strokeStyle = BETTER;
  c.lineWidth = 1.5;
  // A glow that flares as the outline closes, then settles.
  c.shadowColor = BETTER;
  c.shadowBlur = 4 + 10 * Math.sin(Math.PI * clamp(age / (TIME.trace + 0.4)));
  c.stroke();
  c.restore();
  paintCheck(c, box.x, box.y, clamp((age - TIME.trace) / 0.25));
  return traced;
}

// The winner's green check, centred on (x, y), `popped` of the way through popping up: it overshoots a little, like the
// cards do.
function paintCheck(c, x, y, popped) {
  if (popped <= 0) return;
  const size = 7 * (popped < 1 ? 1.25 * easeOut(popped) - 0.25 * popped ** 2 : 1);
  c.save();
  c.translate(x, y);
  dot(c, 0, 0, size + 1.5, CARD);
  dot(c, 0, 0, size, BETTER);
  c.scale(size / 7, size / 7);
  c.beginPath();
  c.moveTo(-3.2, 0.2);
  c.lineTo(-1, 2.4);
  c.lineTo(3.4, -2.2);
  c.strokeStyle = WELL;
  c.lineWidth = 1.8;
  c.lineCap = 'round';
  c.lineJoin = 'round';
  c.stroke();
  c.restore();
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
  const changeWidth = Math.max(0, ...passes.map((s) => (s.change ? 20 + ctx.measureText(s.change).width : 0)),
    ...terms.map((p) => ctx.measureText(p.summary.endLabel).width));
  return { box, live, trendWidth: changeWidth, group: data.comparison };
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
  story.starts.forEach(({ p, t: from, final }, i) => {
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
    // The country's pass counts the change along with its line; the group's pass gives each term's value at its end,
    // and the group's under it.
    const summary = final ? atTheEnd(p.summary) : now.live(p, year);
    paintRow(ctx, { ...row, presidency: { ...row.presidency, summary } }, 0,
      { width, trendWidth: now.trendWidth, scale: null, group: final ? now.group : null },
      logos, { first: true, last: true });
    // "Change since start", small, over the change.
    if (summary.change) {
      ctx.font = `600 8px ${MONO}`;
      ctx.fillStyle = INK_3;
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillText(final ? gettext('At end of term').toUpperCase() : sinceLabel(), width, final && summary.compare ? 2 : ROW / 2 - 15);
      ctx.textAlign = 'left';
    }
    ctx.restore();
  });
}

// A term's summary that reads as its value at the end, and the group's, instead of the changes.
function atTheEnd(s) {
  const value = (summary) => ({ ...summary, change: summary.endLabel, up: null });
  return { ...value(s), compare: s.compare && value(s.compare) };
}

// ---------- The ranking that closes the reel ----------
// The chart dims, and the leaders of the chosen years rank by their average change per year, as on the page.
// With a comparison group they rank instead by how far ahead of the group they left the country: the year of their last
// term's end, the country's value then and the group's, in Bright Ink, the better one green with the cards' check.
// A ranking too long for the well scrolls, slowly, from its top to its end.
const RANK_ROW = 58;
const RANK_HEAD = 48;
const RANK_VALUE = `700 ${12 * RANK_TREND}px ${MONO}`;

// The leaders by their lead over the group, best first (politics/queries.py, at_the_end).
// Leaders without the group's value follow, unranked.
function byLead(rows) {
  const ranked = rows.filter((row) => row.lead !== null).sort((a, b) => b.lead - a.lead);
  return [...ranked.map((row, i) => ({ ...row, rank: i + 1 })), ...rows.filter((row) => row.lead === null).map((row) => ({ ...row, rank: '' }))];
}

// The ranking's columns, right to left: each has a head, a row's width, and a painter that right-aligns at `right`.
// `pop` is how far the row's winner check has popped up.
function changeColumns() {
  const column = (head, pick) => ({
    head,
    width: (c, row) => trendWidth(c, pick(row), RANK_TREND),
    paint: (c, row, right, y) => paintLargeTrend(c, pick(row), right - trendWidth(c, pick(row), RANK_TREND), y, RANK_TREND),
  });
  return [column(gettext('Total'), (row) => row.total), column(gettext('Per year'), (row) => row.perYear)];
}

function valueColumns(data) {
  const measure = (c, text) => {
    c.font = RANK_VALUE;
    return c.measureText(text).width;
  };
  const column = (head, side) => {
    const entry = (row) => (side ? row.compareEnd : row.end);
    return {
      head,
      width: (c, row) => measure(c, entry(row)?.label || '–'),
      paint(c, row, right, y, pop) {
        const won = winnerOf(row.end, row.compareEnd, data.better) === side;
        paintValue(c, entry(row)?.label || '–', right, y, RANK_VALUE, won ? clamp(pop * 2) : 0);
        if (won) paintCheck(c, right - measure(c, entry(row).label) - 13, y, pop);
      },
    };
  };
  const year = {
    head: gettext('Year'),
    width: (c, row) => measure(c, String(row.end.year)),
    paint(c, row, right, y) {
      c.save();
      c.font = `500 ${11 * RANK_TREND}px ${MONO}`;
      c.fillStyle = INK_3;
      c.textAlign = 'right';
      c.fillText(String(row.end.year), right, y);
      c.restore();
    },
  };
  return [column(data.comparison.short, 1), column(data.country, 0), year];
}

// The panel takes the chart's place exactly: the well's width and height. Columns stand `gap` apart.
function rankingLayout(ctx, rows, well, zoom, columns, gap) {
  const box = { x: well.x, y: well.y, w: well.w, h: well.h };
  const css = { w: box.w / zoom, h: box.h / zoom };
  const list = rows.length * RANK_ROW + 10;
  const room = css.h - RANK_HEAD;
  let right = css.w - 18;
  const placed = columns.map((column) => {
    ctx.font = `600 9px ${MONO}`;
    const head = column.head.toUpperCase();
    const width = Math.max(ctx.measureText(head).width, ...rows.map((row) => column.width(ctx, row)));
    const at = { ...column, head, right, width };
    right -= width + gap;
    return at;
  });
  return { box, css, zoom, columns: placed, textRight: right + gap - 16, overflow: Math.max(0, list - room) * zoom };
}

// `age` is the time since the ranking began to appear; the winners' checks pop up once it is in place, row after row.
function paintRanking(ctx, rows, layout, shown, scrolled, title, logos, age) {
  const { box, css, zoom, columns, textRight } = layout;
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
  for (const column of columns) ctx.fillText(column.head, column.right, 27);
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
    ctx.textBaseline = 'middle';
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
    const room = textRight - textX;
    ctx.font = `700 15px ${FONT}`;
    ctx.fillStyle = INK;
    ctx.fillText(wrap(ctx, row.name, room, 1)[0], textX, y + 21);
    ctx.font = `500 10px ${MONO}`;
    ctx.fillStyle = INK_3;
    ctx.fillText(wrap(ctx, row.sub || row.aside, room, 1)[0] || '', textX, y + 40);
    const pop = clamp((age - 0.9 - i * 0.12) / 0.25);
    for (const column of columns) column.paint(ctx, row, column.right, y + RANK_ROW / 2, pop);
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
