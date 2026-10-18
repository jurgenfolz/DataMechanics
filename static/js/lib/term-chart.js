// One country's metric over time, coloured by who was in office. Needs the global `echarts`, and Django's gettext and interpolate.
// The line and the area under it take the colour of the party in office. An HTML card sits over the canvas where each
// presidency ends: the party's logo, the leader, the value and the change during the presidency. One presidency's end is
// the next one's start, so that point needs no second label.
// A card goes where it covers neither another card nor the line. Without such a place it shrinks, then hides;
// only the card of the leader in office may cross the line, so the latest change always shows.
import { escapeHtml, formatTick, formatValue } from './format.js';

const INK_3 = '#8b8f94';
const GRID = '#2c2e30';
const AXIS = '#3a3d41';
const NOBODY = '#5a5e63';
const STEMS = [12, 40, 70];  // how far above or below its point a label may sit
const GAP = 4;           // the space kept clear around a label
// A card's forms, from full to smallest: logo, name and "End of term", value and change; logo, name and change; logo and change.
const FORMS = ['', 'is-compact', 'is-mini'];
const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export function createTermChart(element, { units, onZoom }) {
  const chart = echarts.init(element, null, { renderer: 'canvas' });
  const layer = document.createElement('div');
  layer.className = 'term-labels';
  layer.setAttribute('aria-hidden', 'true');
  element.parentElement.append(layer);

  let data = null;
  let labels = [];
  let dots = [];
  let frame = 0;
  let quiet = false;  // true while the page itself zooms, so onZoom reports only the reader's zooms

  const schedule = () => {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(place);
  };
  new ResizeObserver(() => {
    chart.resize();
    schedule();
  }).observe(element);
  chart.on('finished', schedule);
  chart.on('datazoom', () => {
    schedule();
    if (!quiet) onZoom?.(visibleRange());
  });

  function render(next, range) {
    data = next;
    const rule = units[data.unit];
    const spans = data.presidencies.flatMap((p) => p.spans.map((span) => ({ ...span, presidency: p })));
    const starts = data.presidencies.filter((p) => p.spans.length).map((p) => p.spans[0].from);
    layer.classList.remove('is-shown');

    chart.setOption({
      animation: !REDUCED_MOTION,
      animationDuration: 500,
      animationDurationUpdate: 250,
      animationEasing: 'cubicOut',
      grid: { left: 8, right: 20, top: 28, bottom: 56, containLabel: true },
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
        splitLine: { lineStyle: { color: GRID, width: 1 } },
        axisLabel: { color: INK_3, fontSize: 11, fontFamily: 'Archivo, sans-serif', formatter: (v) => formatTick(v, rule) },
      },
      // The stretch of line that ends at a year takes the colour of the party in office that year.
      visualMap: {
        show: false,
        type: 'piecewise',
        dimension: 0,
        seriesIndex: 0,
        pieces: spans.map((span) => ({ gt: span.from, lte: span.to, color: span.party.color })),
        outOfRange: { color: NOBODY },
      },
      dataZoom: [{
        type: 'slider',
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
          if (year === undefined) return '';
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
        data: data.points,
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
      }],
    }, { replaceMerge: ['series', 'visualMap', 'dataZoom'] });

    buildLabels();
  }

  // The presidency in office in a year, by the 1 July rule (politics/queries.py).
  function spanOf(year) {
    for (const p of data.presidencies) {
      const span = p.spans.find((s) => s.from < year && year <= s.to);
      if (span) return { party: span.party, presidency: p };
    }
    return null;
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
    return { el, stem, point: [s.endYear, s.endValue], current: p.current };
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

    for (const dot of dots) {
      const [x, y] = chart.convertToPixel({ seriesIndex: 0 }, dot.point);
      dot.el.hidden = !visible([x, y]);
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
      if (!box) continue;
      taken.push(box);
      setForm(item.el, FORMS[form]);
      item.el.style.transform = `translate(${Math.round(box.left)}px, ${Math.round(box.top)}px)`;
      const above = box.bottom <= y;
      const from = above ? box.bottom : y + 5;
      const to = above ? y - 5 : box.top;
      item.stem.style.transform = `translate(${Math.round(x)}px, ${Math.round(from)}px)`;
      item.stem.style.height = `${Math.max(0, Math.round(to - from))}px`;
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

  return { render, zoomTo, visibleRange, chart };
}

function overlaps(a, b) {
  return a.left < b.right + GAP && b.left < a.right + GAP && a.top < b.bottom + GAP && b.top < a.bottom + GAP;
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

function toneOf(summary) {
  return summary.good === null ? 'neutral' : summary.good ? 'good' : 'bad';
}

// The change in words, e.g. "Up 4.5%, better".
export function trendSaid(summary) {
  if (summary.up === null) return summary.change;
  return interpolate(SAID[summary.up ? 'up' : 'down'][toneOf(summary)], [summary.change]);
}

// The change during a presidency: an arrow and the size of the change, green when it is good for the metric, red when bad.
export function trendHtml(summary) {
  if (summary.up === null) return `<span class="trend">${escapeHtml(summary.change)}</span>`;
  const tone = toneOf(summary);
  const direction = summary.up ? 'up' : 'down';
  const said = escapeHtml(trendSaid(summary));
  return `<span class="trend trend--${tone}" title="${said}">`
    + `<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="8" fill="currentColor" opacity=".16"/>`
    + `<g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${ARROWS[direction]}</g></svg>`
    + `<span aria-hidden="true">${escapeHtml(summary.change)}</span><span class="visually-hidden">${said}</span></span>`;
}
