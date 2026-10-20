// Countries over time: one line per country, its flag and name at the end of the line. Needs the global `echarts`.
// gettext is Django's, from the translation catalog base.html loads.
import { loadImage, whenFinished } from './chart-image.js';
import { escapeHtml, formatTick, formatValue, tickStep } from './format.js';
import { BRIDGE } from './gaps.js';

// The validated eight-colour order (dark surface). A country keeps its colour while it stays selected.
export const PALETTE = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'];
export const WORLD_COLOR = '#c9ccd0';
const WORLD = 'WLD';
const INK_2 = '#b6b9bd';
const INK_3 = '#8b8f94';
const GRID = '#2c2e30';
const DOTS = ':dots';  // the id suffix of a country's dot series

// A country's values as the chart draws them. A short gap gets filler points on the straight line between its ends;
// the tooltip reads the real values, so a filler never shows a number.
// `dots` marks the real values a reader must see as points: both ends of a bridged gap, and a value alone between
// open gaps, which no line reaches.
function lineData(values) {
  const known = values.flatMap((value, i) => (value === null ? [] : [i]));
  const data = [...values];
  const dots = values.map(() => null);
  known.forEach((i, k) => {
    const before = k ? i - known[k - 1] : Infinity;
    const after = k < known.length - 1 ? known[k + 1] - i : Infinity;
    const bridged = (gap) => gap >= 2 && gap <= BRIDGE;
    if (bridged(before) || bridged(after) || (before > BRIDGE && after > BRIDGE)) dots[i] = values[i];
    if (!bridged(after)) return;
    const b = known[k + 1];
    for (let j = i + 1; j < b; j++) data[j] = { value: values[i] + ((values[b] - values[i]) * (j - i)) / (b - i), symbol: 'none' };
  });
  return { data, dots: dots.some((value) => value !== null) ? dots : null };
}

/**
 * The first and last index of `data.years` that any chosen country has a value for.
 * The axis runs over these years only, so a country elsewhere whose data starts in 1475 does not squeeze the lines.
 */
export function shownSpan(data, selected) {
  const ends = selected.flatMap(({ iso3 }) => {
    const values = data.values[iso3];
    const first = values ? values.findIndex((value) => value !== null) : -1;
    return first < 0 ? [] : [first, values.findLastIndex((value) => value !== null)];
  });
  return ends.length ? [Math.min(...ends), Math.max(...ends)] : [0, data.years.length - 1];
}

export function createLineChart(element, { units, animate = true, flagsOnly = false }) {
  const chart = echarts.init(element, null, { renderer: 'canvas' });
  const observer = new ResizeObserver(() => chart.resize());
  observer.observe(element);

  function render(data, selected) {
    const rule = units[data.unit];
    const narrow = flagsOnly || element.clientWidth < 560;
    const [first, last] = shownSpan(data, selected);
    const dots = [];  // a scatter series per country, for the real values at bridged gaps and lone values
    const lines = selected
      .filter(({ iso3 }) => data.values[iso3])
      .map(({ iso3, color }) => {
        const country = data.countries[iso3];
        const world = iso3 === WORLD;
        const drawn = lineData(data.values[iso3].slice(first, last + 1));
        if (drawn.dots) dots.push({ id: `${iso3}${DOTS}`, type: 'scatter', data: drawn.dots, symbolSize: 6, silent: true, color: world ? WORLD_COLOR : color, z: 3 });
        return {
          id: iso3,
          name: country.name,
          type: 'line',
          data: drawn.data,
          showSymbol: false,
          symbolSize: 8,
          connectNulls: false,
          smooth: false,
          color: world ? WORLD_COLOR : color,
          lineStyle: { width: 2, type: world ? [6, 4] : 'solid', cap: 'round', join: 'round' },
          emphasis: { focus: 'series', lineStyle: { width: 2.5 } },
          // Every line ends in its flag; wide charts add the name.
          endLabel: {
            show: true,
            distance: 8,
            formatter: () => (narrow ? '{flag|}' : `{flag|} {name|${shortName(country.name)}}`),
            rich: {
              flag: { width: 20, height: 15, backgroundColor: { image: country.flag }, borderRadius: 2 },
              name: { color: INK_2, fontSize: 12, fontWeight: 600, fontFamily: 'Archivo, sans-serif', padding: [0, 0, 0, 4] },
            },
          },
          labelLayout: { moveOverlap: 'shiftY' },
        };
      });

    chart.setOption({
      animation: animate,
      animationDuration: 500,
      animationEasing: 'cubicOut',
      grid: { left: 8, right: narrow ? 34 : 150, top: 20, bottom: 8, containLabel: true },
      xAxis: {
        type: 'category',
        data: data.years.slice(first, last + 1),
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#3a3d41' } },
        axisTick: { show: false },
        axisLabel: { color: INK_3, fontFamily: 'JetBrains Mono, monospace', fontSize: 11, hideOverlap: true },
      },
      yAxis: {
        type: 'value',
        scale: true,
        splitNumber: 5,
        minInterval: tickStep(rule),
        splitLine: { lineStyle: { color: GRID, width: 1 } },
        axisLabel: { color: INK_3, fontSize: 11, fontFamily: 'Archivo, sans-serif', formatter: (v) => formatTick(v, rule) },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'line', lineStyle: { color: '#5a5e63', width: 1 } },
        backgroundColor: '#17191b',
        borderColor: '#3a3d41',
        padding: [10, 12],
        extraCssText: 'border-radius:10px;box-shadow:0 12px 30px rgb(0 0 0 / .5);',
        formatter(params) {
          // The real values only: a filler point on a bridged gap has no number of its own.
          const rows = params
            .filter((p) => !p.seriesId.endsWith(DOTS))
            .map((p) => ({ p, value: data.values[p.seriesId]?.[first + p.dataIndex] ?? null }))
            .filter(({ value }) => value !== null)
            .sort((a, b) => b.value - a.value)
            .map(({ p, value }) => {
              const country = data.countries[p.seriesId];
              return `<div class="tip__row"><i style="background:${p.color}"></i>`
                + `<img src="${escapeHtml(country.flag)}" alt=""><span>${escapeHtml(country.name)}</span>`
                + `<strong>${escapeHtml(formatValue(value, rule))}</strong></div>`;
            });
          const year = escapeHtml(params[0]?.axisValue ?? '');
          return `<div class="tip"><div class="tip__head">${year}</div>${rows.join('') || `<div class="tip__muted">${escapeHtml(gettext('No data'))}</div>`}</div>`;
        },
      },
      series: [...lines, ...dots],
    }, { replaceMerge: ['series'] });
    return lines.map((line) => line.id);
  }

  function dispose() {
    observer.disconnect();
    chart.dispose();
  }

  return { render, dispose, chart };
}

function shortName(name) {
  return name.length > 18 ? `${name.slice(0, 17)}…` : name;
}

// ---------- The saved image (lib/chart-image.js) ----------
const LEGEND_ROW = 36;

/** What saveChartImage needs for the line chart: how to draw it, and its legend's room and painting. */
export function lineImageParts(data, selected, units) {
  const shown = selected.filter(({ iso3 }) => data.values[iso3]);
  return {
    belowHeight: Math.ceil(shown.length / 3) * LEGEND_ROW + 8,
    async draw(element) {
      // The image names the countries in its legend, so the lines end in their flags alone.
      const line = createLineChart(element, { units, animate: false, flagsOnly: true });
      const finished = whenFinished(line.chart);
      line.render(data, selected);
      await finished;
      return { chart: line.chart, dispose: line.dispose, below: (ctx, box) => paintLineLegend(ctx, box, data, shown) };
    },
  };
}

/** The legend of the saved image: each country's line colour, flag and name, three to a row. */
async function paintLineLegend(ctx, box, data, shown) {
  const flags = await Promise.all(shown.map(({ iso3 }) => loadImage(data.countries[iso3]?.flag)));
  const columnW = box.w / 3;
  ctx.save();
  ctx.textBaseline = 'middle';
  ctx.font = '500 18px Archivo, "Helvetica Neue", Arial, sans-serif';
  shown.forEach(({ iso3, color }, n) => {
    const x = box.x + (n % 3) * columnW;
    const y = box.y + Math.floor(n / 3) * LEGEND_ROW + LEGEND_ROW / 2;
    ctx.strokeStyle = iso3 === WORLD ? WORLD_COLOR : color;
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.setLineDash(iso3 === WORLD ? [6, 5] : []);
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + 24, y);
    ctx.stroke();
    ctx.setLineDash([]);
    if (flags[n]) ctx.drawImage(flags[n], x + 34, y - 9, 24, 18);
    ctx.fillStyle = '#f2f3f4';
    ctx.fillText(shortName(data.countries[iso3]?.name || iso3), x + 68, y);
  });
  ctx.restore();
}

