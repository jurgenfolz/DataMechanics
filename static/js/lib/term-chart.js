// One country's metric over time, coloured by who was in office. Needs the global `echarts`, and Django's gettext and interpolate.
// The line and the area under it take, for each presidency, the colour of the party it ended in: one colour per
// presidency keeps the chart simple when a leader changed party in office. An HTML card sits over the canvas where each
// presidency ends: the party's logo, the leader, the value and the change during the presidency. One presidency's end is
// the next one's start, so that point needs no second label.
// A card goes where it covers neither another card nor the line. Without such a place it shrinks, then hides;
// only the card of the leader in office may cross the line, so the latest change always shows.
import { drawContained, loadImage, MONO, whenFinished } from './chart-image.js';
import { escapeHtml, formatTick, formatValue, tickStep } from './format.js';
import { BRIDGE } from './gaps.js';

const INK_3 = '#8b8f94';
const GRID = '#2c2e30';
const AXIS = '#3a3d41';
const NOBODY = '#5a5e63';
const STEMS = [12, 40, 70];  // how far above or below its point a label may sit
const GAP = 4;           // the space kept clear around a label
// A card's forms, from full to smallest: logo, name and "End of term", value and change; logo, name and change; logo and change.
const FORMS = ['', 'is-compact', 'is-mini'];
const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export function createTermChart(element, { units, onZoom, animate = true, slider = true }) {
  const chart = echarts.init(element, null, { renderer: 'canvas' });
  const layer = document.createElement('div');
  layer.className = 'term-labels';
  layer.setAttribute('aria-hidden', 'true');
  element.parentElement.append(layer);

  let data = null;
  let stretches = [];
  let labels = [];
  let dots = [];
  let frame = 0;
  let quiet = false;  // true while the page itself zooms, so onZoom reports only the reader's zooms

  const schedule = () => {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(place);
  };
  const observer = new ResizeObserver(() => {
    chart.resize();
    schedule();
  });
  observer.observe(element);
  chart.on('finished', schedule);
  chart.on('datazoom', () => {
    schedule();
    if (!quiet) onZoom?.(visibleRange());
  });

  function render(next, range) {
    data = next;
    const rule = units[data.unit];
    stretches = presidencyStretches(data);
    const starts = data.presidencies.filter((p) => p.spans.length).map((p) => p.spans[0].from);
    layer.classList.remove('is-shown');

    chart.setOption({
      animation: animate && !REDUCED_MOTION,
      animationDuration: 500,
      animationDurationUpdate: 250,
      animationEasing: 'cubicOut',
      grid: { left: 8, right: 20, top: 28, bottom: slider ? 56 : 12, containLabel: true },
      xAxis: {
        type: 'value',
        min: 'dataMin',
        max: 'dataMax',
        minInterval: 1,
        splitLine: { show: false },
        axisLine: { lineStyle: { color: AXIS } },
        axisTick: { show: false },
        axisLabel: {
          color: INK_3, fontFamily: 'JetBrains Mono, monospace', fontSize: 11, hideOverlap: true,
          formatter: (v) => (Number.isInteger(v) ? String(v) : ''),
        },
      },
      yAxis: {
        type: 'value',
        scale: true,
        splitNumber: 5,
        minInterval: tickStep(rule),
        splitLine: { lineStyle: { color: GRID, width: 1 } },
        axisLabel: { color: INK_3, fontSize: 11, fontFamily: 'Archivo, sans-serif', formatter: (v) => formatTick(v, rule) },
      },
      // The stretch of line that ends at a year takes the colour of the party in office that year.
      visualMap: {
        show: false,
        type: 'piecewise',
        dimension: 0,
        seriesIndex: 0,
        pieces: stretches.map((stretch) => ({ gt: stretch.from, lte: stretch.to, color: stretch.party.color })),
        outOfRange: { color: NOBODY },
      },
      dataZoom: [{
        type: 'slider',
        show: slider,
        xAxisIndex: 0,
        startValue: range?.[0],
        endValue: range?.[1],
        minValueSpan: 4,
        height: 24,
        bottom: 10,
        borderColor: AXIS,
        backgroundColor: 'rgba(255,255,255,0.02)',
        fillerColor: 'rgba(255,215,0,0.08)',
        dataBackground: { lineStyle: { color: '#5a5e63', width: 1 }, areaStyle: { color: '#2c2e30', opacity: 1 } },
        selectedDataBackground: { lineStyle: { color: '#b6b9bd', width: 1 }, areaStyle: { color: '#3a3d41', opacity: 1 } },
        handleStyle: { color: '#ffd700', borderColor: '#ffd700' },
        moveHandleStyle: { color: '#3a3d41' },
        emphasis: { handleStyle: { color: '#ffe24d', borderColor: '#ffe24d' }, moveHandleStyle: { color: '#5a5e63' } },
        textStyle: { color: INK_3, fontFamily: 'JetBrains Mono, monospace', fontSize: 11 },
        labelFormatter: (v) => String(Math.round(v)),
        brushSelect: false,
      }],
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'line', lineStyle: { color: '#5a5e63', width: 1 } },
        backgroundColor: '#17191b',
        borderColor: AXIS,
        padding: [10, 12],
        extraCssText: 'border-radius:10px;box-shadow:0 12px 30px rgb(0 0 0 / .5);',
        formatter(params) {
          const [year, value] = params[0]?.value || [];
          if (year === undefined || value === null) return '';
          const span = spanOf(year);
          const who = span
            ? `<div class="tip__who">${logoHtml(span.party)}<span>${escapeHtml(span.presidency.shortName)}`
              + `<em>${escapeHtml(span.party.abbreviation || span.party.name)}</em></span></div>`
            : '';
          return `<div class="tip"><div class="tip__head">${year}</div>`
            + `<div class="tip__value">${escapeHtml(formatValue(value, rule))}</div>${who}</div>`;
        },
      },
      series: [{
        type: 'line',
        data: withBreaks(data.points),
        showSymbol: false,
        symbolSize: 8,
        lineStyle: { width: 2.5, cap: 'round', join: 'round' },
        areaStyle: { opacity: 0.16 },
        emphasis: { disabled: true },
        // A thin dashed line where each presidency's stretch begins.
        markLine: {
          silent: true,
          symbol: 'none',
          animation: false,
          label: { show: false },
          lineStyle: { color: AXIS, type: [3, 4], width: 1 },
          data: starts.map((x) => ({ xAxis: x })),
        },
      }, {
        // A value alone between open gaps: no line reaches it, so a dot in its leader's party colour shows it.
        type: 'scatter',
        data: lonePoints(data.points).map((point) => ({ value: point, itemStyle: { color: spanOf(point[0])?.party.color || INK_3 } })),
        symbolSize: 6,
        silent: true,
        z: 3,
      }],
    }, { replaceMerge: ['series', 'visualMap', 'dataZoom'] });

    buildLabels();
  }

  // The presidency in office in a year, by the 1 July rule (politics/queries.py).
  function spanOf(year) {
    return stretches.find((stretch) => stretch.from < year && year <= stretch.to) || null;
  }

  function buildLabels() {
    layer.replaceChildren();
    const withData = data.presidencies.filter((p) => p.summary);
    // The current presidency first, then the longest: they win when two labels want the same place.
    const order = [...withData].sort((a, b) => Number(b.current) - Number(a.current)
      || (b.summary.endYear - b.summary.startYear) - (a.summary.endYear - a.summary.startYear));
    labels = order.map(label);
    const points = new Map();
    for (const p of withData) {
      for (const [year, value] of [[p.summary.startYear, p.summary.startValue], [p.summary.endYear, p.summary.endValue]]) {
        points.set(year, [year, value]);
      }
    }
    dots = [...points.values()].map((point) => {
      const el = document.createElement('span');
      el.className = 'term-dot';
      layer.append(el);
      return { el, point };
    });
    for (const item of labels) {
      layer.append(item.stem, item.el);
      item.sizes = FORMS.map((form) => {
        setForm(item.el, form);
        return { w: item.el.offsetWidth, h: item.el.offsetHeight };
      });
    }
  }

  // The card at the end of a presidency, with the logo of the party it ended in.
  function label(p) {
    const s = p.summary;
    const party = p.spans.at(-1)?.party || p.party;
    const el = document.createElement('div');
    el.className = 'term-label';
    el.style.setProperty('--party', party.color);
    el.innerHTML = `${logoHtml(party)}<span class="term-label__text">`
      + `<span class="term-label__kicker"><strong>${escapeHtml(p.shortName)}</strong>`
      + `<span class="term-label__full"> · ${escapeHtml(p.current ? gettext('In office') : gettext('End of term'))}</span></span>`
      + `<span class="term-label__row"><span class="term-label__value term-label__full">${escapeHtml(s.endLabel)}</span>`
      + `${trendHtml(s)}</span></span>`;
    const stem = document.createElement('span');
    stem.className = 'term-stem';
    stem.style.setProperty('--party', party.color);
    return { el, stem, point: [s.endYear, s.endValue], current: p.current, party, presidency: p, placed: null };
  }

  function setForm(el, form) {
    el.classList.remove(...FORMS.filter(Boolean));
    if (form) el.classList.add(form);
  }

  // ---------- Placing the labels ----------
  function place() {
    if (!data) return;
    const rect = plotRect();
    if (!rect) return;
    const bounds = { left: rect.x, top: 4, right: element.clientWidth - 4, bottom: rect.y + rect.height };
    const visible = ([x, y]) => x >= rect.x - 1 && x <= rect.x + rect.width + 1 && y >= rect.y - 1 && y <= rect.y + rect.height + 1;
    const line = data.points.map((point) => chart.convertToPixel({ seriesIndex: 0 }, point));
    const taken = [];
    // The well's "Save as image" button sits in the top right corner: cards keep clear of it.
    if (element.parentElement.querySelector('[data-save-image]')) {
      taken.push({ left: element.clientWidth - 44, top: 0, right: element.clientWidth, bottom: 40 });
    }

    for (const dot of dots) {
      const [x, y] = chart.convertToPixel({ seriesIndex: 0 }, dot.point);
      dot.el.hidden = !visible([x, y]);
      dot.at = dot.el.hidden ? null : [x, y];
      if (dot.el.hidden) continue;
      dot.el.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
      taken.push({ left: x - 6, top: y - 6, right: x + 6, bottom: y + 6 });
    }

    const free = (box) => box.left >= bounds.left && box.right <= bounds.right && box.top >= bounds.top
      && box.bottom <= bounds.bottom && !taken.some((other) => overlaps(box, other));
    const fits = (box) => free(box) && !crossesLine(box, line);

    for (const item of labels) {
      const [x, y] = chart.convertToPixel({ seriesIndex: 0 }, item.point);
      let box = null;
      let form = 0;
      if (visible([x, y])) {
        for (; form < FORMS.length && !box; form += 1) box = candidates(x, y, item.sizes[form], bounds).find(fits);
        form -= 1;
        if (!box && item.current) box = candidates(x, y, item.sizes[form], bounds).find(free);
      }
      item.el.hidden = !box;
      item.stem.hidden = !box;
      item.placed = null;
      if (!box) continue;
      taken.push(box);
      setForm(item.el, FORMS[form]);
      item.el.style.transform = `translate(${Math.round(box.left)}px, ${Math.round(box.top)}px)`;
      const above = box.bottom <= y;
      const from = above ? box.bottom : y + 5;
      const to = above ? y - 5 : box.top;
      item.stem.style.transform = `translate(${Math.round(x)}px, ${Math.round(from)}px)`;
      item.stem.style.height = `${Math.max(0, Math.round(to - from))}px`;
      item.placed = { box, form, stem: { x, from, to } };
    }
    layer.classList.add('is-shown');
  }

  // A card reaches left over its own presidency; failing that, right or centred. It tries below and above its point,
  // near first. At the plot's edges a card slides inwards, over its stem.
  function candidates(x, y, { w, h }, bounds) {
    const lefts = [x - w + 12, x - 12, x - w / 2].map((left) => Math.min(Math.max(left, bounds.left), bounds.right - w))
      .filter((left) => left <= x - 6 && left + w >= x + 6);
    const tops = STEMS.flatMap((stem) => [y + stem, y - stem - h]);
    return tops.flatMap((top) => lefts.map((left) => ({ left, top, right: left + w, bottom: top + h })));
  }

  // ECharts keeps the plot area on its grid model; the public API has no getter for it.
  function plotRect() {
    return chart.getModel()?.getComponent('grid', 0)?.coordinateSystem?.getRect();
  }

  function visibleRange() {
    const rect = plotRect();
    if (!rect) return null;
    return [rect.x, rect.x + rect.width].map((px) => chart.convertFromPixel({ xAxisIndex: 0 }, px));
  }

  function zoomTo(range) {
    quiet = true;
    chart.dispatchAction(range ? { type: 'dataZoom', startValue: range[0], endValue: range[1] } : { type: 'dataZoom', start: 0, end: 100 });
    quiet = false;
  }

  // ---------- The saved image (lib/chart-image.js) ----------
  // The cards are HTML, so the chart's own image leaves them out: this paints them, their stems and the dots on a canvas
  // where the chart's image sits at (x0, y0) at `scale` times its size.
  async function paintLabels(ctx, x0, y0, scale) {
    place();
    const logos = new Map(await Promise.all(labels.filter((l) => l.placed && l.party.logo)
      .map(async (l) => [l.party.logo, await loadImage(l.party.logo)])));
    ctx.save();
    ctx.translate(x0, y0);
    ctx.scale(scale, scale);
    for (const item of labels) {
      if (!item.placed) continue;
      const { x, from, to } = item.placed.stem;
      ctx.strokeStyle = item.party.color;
      ctx.globalAlpha = 0.75;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, from);
      ctx.lineTo(x, to);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }
    for (const dot of dots) {
      if (!dot.at) continue;
      ctx.beginPath();
      ctx.arc(dot.at[0], dot.at[1], 7, 0, 2 * Math.PI);
      ctx.fillStyle = '#1d1f21';
      ctx.fill();
      ctx.beginPath();
      ctx.arc(dot.at[0], dot.at[1], 5, 0, 2 * Math.PI);
      ctx.fillStyle = '#f2f3f4';
      ctx.fill();
    }
    for (const item of labels) if (item.placed) paintCard(ctx, item, logos.get(item.party.logo));
    ctx.restore();
  }

  // Nothing to show: the line, the cards and the dots all go, and the old data with them, so a resize draws nothing back.
  function clear() {
    cancelAnimationFrame(frame);
    data = null;
    labels = [];
    dots = [];
    layer.replaceChildren();
    layer.classList.remove('is-shown');
    chart.clear();
  }

  function dispose() {
    observer.disconnect();
    cancelAnimationFrame(frame);
    chart.dispose();
  }

  return { render, clear, zoomTo, visibleRange, paintLabels, dispose, chart };
}

/**
 * Each presidency's stretch of the line, from the year before its first year to its last, in the colour of the party
 * it ended in. The rule keeps one colour per presidency; the table and the timeline still show every party it held.
 */
function presidencyStretches(data) {
  return data.presidencies.filter((p) => p.spans.length).map((p) => ({
    from: p.spans[0].from,
    to: p.spans.at(-1).to,
    party: p.spans.at(-1).party,
    presidency: p,
  }));
}

/** What saveChartImage needs for this chart: how to draw it, without its slider, at the zoom on screen. */
export function termImageParts(data, range, units) {
  return {
    async draw(element) {
      const term = createTermChart(element, { units, animate: false, slider: false });
      const finished = whenFinished(term.chart);
      term.render(data, range);
      await finished;
      return { chart: term.chart, dispose: term.dispose, paint: term.paintLabels };
    },
  };
}

const SANS = 'Archivo, "Helvetica Neue", Arial, sans-serif';
const TONES = { good: '#2bc892', bad: '#f2545b', neutral: '#b6b9bd' };

// One card, laid out like .term-label in site.css: logo tile, then the name line and the value and change line.
function paintCard(ctx, item, logo) {
  const { box, form } = item.placed;
  const { left, top } = box;
  const w = box.right - box.left;
  const h = box.bottom - box.top;
  const p = item.presidency;
  const s = p.summary;
  ctx.save();
  ctx.beginPath();
  ctx.roundRect(left, top, w, h, 8);
  ctx.fillStyle = 'rgba(23, 25, 27, 0.94)';
  ctx.fill();
  ctx.clip();
  ctx.fillStyle = item.party.color;
  ctx.fillRect(left + w - 4, top, 4, h);
  ctx.restore();
  ctx.beginPath();
  ctx.roundRect(left + 0.5, top + 0.5, w - 1, h - 1, 8);
  ctx.strokeStyle = '#3a3d41';
  ctx.lineWidth = 1;
  ctx.stroke();

  const tile = FORMS[form] === 'is-mini' ? 26 : 32;
  const tileX = left + 6;
  const tileY = top + (h - tile) / 2;
  paintLogoTile(ctx, item.party, logo, tileX, tileY, tile);

  const textX = tileX + tile + 8;
  ctx.textBaseline = 'middle';
  if (FORMS[form] === 'is-mini') {
    paintTrend(ctx, s, textX, top + h / 2);
    return;
  }
  const kickerY = top + h / 2 - 9;
  const rowY = top + h / 2 + 9;
  ctx.font = `700 12px ${SANS}`;
  ctx.fillStyle = '#f2f3f4';
  ctx.fillText(p.shortName, textX, kickerY);
  let rowX = textX;
  if (!FORMS[form]) {
    const nameW = ctx.measureText(p.shortName).width;
    ctx.font = `400 11px ${SANS}`;
    ctx.fillStyle = '#8b8f94';
    ctx.fillText(` · ${p.current ? gettext('In office') : gettext('End of term')}`, textX + nameW, kickerY);
    ctx.font = `700 12px ${MONO}`;
    ctx.fillStyle = '#f2f3f4';
    ctx.fillText(s.endLabel, textX, rowY);
    rowX += ctx.measureText(s.endLabel).width + 8;
  }
  paintTrend(ctx, s, rowX, rowY);
}

export function paintLogoTile(ctx, party, logo, x, y, size) {
  ctx.beginPath();
  ctx.roundRect(x, y, size, size, 7);
  ctx.fillStyle = '#f2f3f4';
  ctx.fill();
  if (logo) {
    drawContained(ctx, logo, x + 2, y + 2, size - 4, size - 4);
  } else if (party.abbreviation) {
    ctx.beginPath();
    ctx.roundRect(x + 2, y + 2, size - 4, size - 4, 5);
    ctx.fillStyle = party.color;
    ctx.fill();
    ctx.fillStyle = '#121416';
    ctx.font = `700 9px ${MONO}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(party.abbreviation, x + size / 2, y + size / 2);
    ctx.textAlign = 'left';
  }
}

// The arrow in its tinted circle, then the size of the change, like trendHtml.
export function paintTrend(ctx, summary, x, y) {
  ctx.font = `700 12px ${MONO}`;
  ctx.textBaseline = 'middle';
  if (summary.up === null) {
    ctx.fillStyle = TONES.neutral;
    ctx.fillText(summary.change, x, y);
    return;
  }
  const color = TONES[toneOf(summary)];
  ctx.fillStyle = color;
  ctx.globalAlpha = 0.16;
  ctx.beginPath();
  ctx.arc(x + 8, y, 8, 0, 2 * Math.PI);
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.6;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.beginPath();
  if (summary.up) {
    ctx.moveTo(x + 5.5, y + 2.5); ctx.lineTo(x + 10.5, y - 2.5);
    ctx.moveTo(x + 6.5, y - 2.5); ctx.lineTo(x + 10.5, y - 2.5); ctx.lineTo(x + 10.5, y + 1.5);
  } else {
    ctx.moveTo(x + 5.5, y - 2.5); ctx.lineTo(x + 10.5, y + 2.5);
    ctx.moveTo(x + 10.5, y - 1.5); ctx.lineTo(x + 10.5, y + 2.5); ctx.lineTo(x + 6.5, y + 2.5);
  }
  ctx.stroke();
  ctx.fillText(summary.change, x + 20, y);
}

function overlaps(a, b) {
  return a.left < b.right + GAP && b.left < a.right + GAP && a.top < b.bottom + GAP && b.top < a.bottom + GAP;
}

// The points with a break in the middle of every gap longer than BRIDGE years (lib/gaps.js).
function withBreaks(points) {
  return points.flatMap((point, i) => {
    const before = points[i - 1];
    return before && point[0] - before[0] > BRIDGE ? [[Math.round((before[0] + point[0]) / 2), null], point] : [point];
  });
}

// The points with an open gap of more than BRIDGE years on both sides.
function lonePoints(points) {
  const gap = (i, j) => (points[i] && points[j] ? Math.abs(points[i][0] - points[j][0]) : Infinity);
  return points.filter((_, i) => gap(i, i - 1) > BRIDGE && gap(i, i + 1) > BRIDGE);
}

// Whether the line passes through a box. Between two points the line is straight, so its height over the part of
// each segment above the box lies between the heights at that part's two ends.
function crossesLine(box, line) {
  const left = box.left - GAP;
  const right = box.right + GAP;
  for (let i = 1; i < line.length; i += 1) {
    const [x1, y1] = line[i - 1];
    const [x2, y2] = line[i];
    if (x2 < left || x1 > right || x2 === x1) continue;
    const at = (x) => y1 + ((y2 - y1) * (x - x1)) / (x2 - x1);
    const ya = at(Math.max(x1, left));
    const yb = at(Math.min(x2, right));
    if (Math.max(ya, yb) >= box.top - GAP && Math.min(ya, yb) <= box.bottom + GAP) return true;
  }
  return false;
}

// A party's logo on a light tile, or its initials on its colour when it has no logo.
export function logoHtml(party) {
  const title = escapeHtml(party.name);
  if (party.logo) return `<span class="party-chip" title="${title}"><img class="party-logo" src="${escapeHtml(party.logo)}" alt="${escapeHtml(party.abbreviation)}"></span>`;
  if (party.abbreviation) return `<span class="party-chip" title="${title}"><span class="party-badge" style="--party:${party.color}">${escapeHtml(party.abbreviation)}</span></span>`;
  return `<span class="party-chip" title="${title}"><span class="party-badge party-badge--none">–</span></span>`;
}

const ARROWS = {
  up: '<path d="M5.5 10.5l5-5M6.5 5.5h4v4"/>',
  down: '<path d="M5.5 5.5l5 5M10.5 6.5v4h-4"/>',
};

// How a change reads out loud and on hover, by its direction and whether it is good for the metric.
const SAID = {
  up: { good: gettext('Up %s, better'), bad: gettext('Up %s, worse'), neutral: gettext('Up %s') },
  down: { good: gettext('Down %s, better'), bad: gettext('Down %s, worse'), neutral: gettext('Down %s') },
};

/** 'good', 'bad' or 'neutral': how a presidency's change reads for the metric. */
export function toneOf(summary) {
  return summary.good === null ? 'neutral' : summary.good ? 'good' : 'bad';
}

// The change in words, e.g. "Down 4.5%, worse": the words give the direction, so the minus sign goes.
export function trendSaid(summary) {
  if (summary.up === null) return summary.change;
  return interpolate(SAID[summary.up ? 'up' : 'down'][toneOf(summary)], [summary.change.replace(/^-/, '')]);
}

// The change during a presidency: an arrow and the size of the change, green when it is good for the metric, red when bad.
export function trendHtml(summary) {
  if (summary.up === null) return `<span class="trend trend--none">${escapeHtml(summary.change)}</span>`;
  const tone = toneOf(summary);
  const direction = summary.up ? 'up' : 'down';
  const said = escapeHtml(trendSaid(summary));
  return `<span class="trend trend--${tone}" title="${said}">`
    + `<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="8" fill="currentColor" opacity=".16"/>`
    + `<g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${ARROWS[direction]}</g></svg>`
    + `<span aria-hidden="true">${escapeHtml(summary.change)}</span><span class="visually-hidden">${said}</span></span>`;
}
