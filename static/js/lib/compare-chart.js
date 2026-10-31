// Two metrics of one country over time, each on its own axis: the left select's on the left, the right select's on the right.
// Needs the global `echarts`. gettext is Django's, from the translation catalog base.html loads.
import { whenFinished } from './chart-image.js';
import { bindEventTips, eventLegendHeight, eventRoom, eventSeries, eventsIn, layoutEvents, paintEventLegend } from './events.js';
import { escapeHtml, formatTick, formatValue, tickStep } from './format.js';
import { lineData, PALETTE } from './line-chart.js';

// A line takes the colour of its side: the site's first series colour on the left, its second on the right.
export const COLORS = [PALETTE[0], PALETTE[1]];
const INK = '#f2f3f4';
const INK_2 = '#b6b9bd';
const INK_3 = '#8b8f94';
const GRID = '#2c2e30';
const DOTS = ':dots';  // the id suffix of a line's dot series
const SAVE_BUTTON = 38;  // the width of the save button's corner, at the well's top right (.chart-save)

/**
 * Draws `lines`, one or two { side, label, axis, rule, values } over `years`.
 * `side` is 0 for the left axis and 1 for the right; `axis` names the axis (what the values are in);
 * `values` are aligned with `years`, null where the source has no value.
 * `events` are the world events to mark (lib/events.js); those outside `years` are left out.
 */
// `iconsOnly` keeps the events' chips to their icons: the saved image names the events under the chart.
export function createCompareChart(element, { animate = true, iconsOnly = false } = {}) {
  const chart = echarts.init(element, null, { renderer: 'canvas' });
  const observer = new ResizeObserver(() => chart.resize());
  observer.observe(element);
  let laid = { items: [], rows: 0 };
  bindEventTips(chart, element.parentElement, () => laid);

  function render(years, lines, events = []) {
    const narrow = iconsOnly || element.clientWidth < 560;
    const margins = [58, lines.length > 1 ? 58 : 24];  // the axes' labels take about 50 px each
    const toAxis = (at) => at - years[0];
    const plotWidth = Math.max(100, element.clientWidth - margins[0] - margins[1]);
    laid = layoutEvents(eventsIn(events, years[0], years.at(-1)),
      (at) => margins[0] + (toAxis(at) / Math.max(1, years.length - 1)) * plotWidth,
      { left: margins[0], right: margins[0] + plotWidth, narrow });
    const series = lines.flatMap((line, n) => {
      const drawn = lineData(line.values);
      const color = COLORS[line.side];
      return [
        {
          id: String(line.side),
          name: line.label,
          type: 'line',
          yAxisIndex: n,
          data: drawn.data,
          showSymbol: false,
          symbolSize: 8,
          connectNulls: false,
          color,
          lineStyle: { width: 2, cap: 'round', join: 'round' },
          emphasis: { focus: 'series', lineStyle: { width: 2.5 } },
        },
        ...(drawn.dots ? [{ id: `${line.side}${DOTS}`, type: 'scatter', yAxisIndex: n, data: drawn.dots, symbolSize: 6, silent: true, color, z: 3 }] : []),
      ];
    });

    chart.setOption({
      animation: animate,
      animationDuration: 500,
      animationEasing: 'cubicOut',
      // The top leaves room for the axes' names, under the well's save button.
      // Without a right axis, the right edge keeps room for the last year's label.
      grid: { left: 8, right: lines.length > 1 ? 8 : 24, top: 52 + eventRoom(laid.rows), bottom: 8, containLabel: true },
      xAxis: {
        type: 'category',
        data: years,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#3a3d41' } },
        axisTick: { show: false },
        axisLabel: { color: INK_3, fontFamily: 'JetBrains Mono, monospace', fontSize: 11, hideOverlap: true },
      },
      yAxis: lines.map((line, n) => axis(line, n, element.clientWidth, eventRoom(laid.rows))),
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'line', lineStyle: { color: '#5a5e63', width: 1 } },
        backgroundColor: '#17191b',
        borderColor: '#3a3d41',
        padding: [10, 12],
        extraCssText: 'border-radius:10px;box-shadow:0 12px 30px rgb(0 0 0 / .5);',
        formatter(params) {
          // The real values only: a filler point on a bridged gap has no number of its own.
          const year = params[0]?.axisValue;
          const i = years.indexOf(Number(year));
          const rows = lines
            .filter((line) => line.values[i] !== null && line.values[i] !== undefined)
            .map((line) => `<div class="tip__row tip__row--group"><i style="background:${COLORS[line.side]}"></i>`
              + `<span>${escapeHtml(line.label)}</span><strong>${escapeHtml(formatValue(line.values[i], line.rule))}</strong></div>`);
          return `<div class="tip"><div class="tip__head">${escapeHtml(year ?? '')}</div>${rows.join('') || `<div class="tip__muted">${escapeHtml(gettext('No data'))}</div>`}</div>`;
        },
      },
      series: [...series, ...(laid.items.length ? [eventSeries(laid, toAxis, { narrow })] : [])],
    }, { replaceMerge: ['series', 'yAxis'] });
  }

  function dispose() {
    observer.disconnect();
    chart.dispose();
  }

  return { render, dispose, chart };
}

// An axis names what its values are in, after a short stroke of its line's colour, so each axis reads with its line.
// Only the first axis draws grid lines; the second lines its ticks up with them.
// Each name gets at most a little under half the chart's width, so the two never meet on a phone.
// The names stay above the world events' chips, which take `room` above the plot.
function axis(line, n, width, room = 0) {
  const right = line.side === 1;
  return {
    type: 'value',
    position: right ? 'right' : 'left',
    scale: true,
    alignTicks: n > 0,
    splitNumber: 5,
    minInterval: tickStep(line.rule),
    name: `{key|}  ${line.axis}`,
    nameLocation: 'end',
    nameGap: 18 + room,
    nameTruncate: { maxWidth: Math.max(width * 0.42 - (right ? SAVE_BUTTON : 0), 80) },
    nameTextStyle: {
      align: right ? 'right' : 'left',
      padding: right ? [0, SAVE_BUTTON, 0, 0] : 0,  // the right one ends before the save button
      color: INK_2,
      fontSize: 11,
      fontWeight: 600,
      fontFamily: 'Archivo, sans-serif',
      rich: { key: { width: 14, height: 2, backgroundColor: COLORS[line.side], borderRadius: 1 } },
    },
    axisLine: { show: false },
    splitLine: { show: n === 0, lineStyle: { color: GRID, width: 1 } },
    axisLabel: { color: INK_3, fontSize: 11, fontFamily: 'Archivo, sans-serif', formatter: (v) => formatTick(v, line.rule) },
  };
}

// ---------- The saved image (lib/chart-image.js) ----------
const LEGEND_ROW = 36;

/** What saveChartImage needs for the chart: how to draw it, and its legend's room and painting. */
export function compareImageParts(years, lines, events = []) {
  const marked = eventsIn(events, years[0], years.at(-1));
  return {
    belowHeight: lines.length * LEGEND_ROW + 8 + eventLegendHeight(marked),
    async draw(element) {
      const compare = createCompareChart(element, { animate: false, iconsOnly: true });
      const finished = whenFinished(compare.chart);
      compare.render(years, lines, events);
      await finished;
      return {
        chart: compare.chart,
        dispose: compare.dispose,
        below(ctx, box) {
          paintLegend(ctx, box, lines);
          paintEventLegend(ctx, { ...box, y: box.y + lines.length * LEGEND_ROW + 8 }, marked);
        },
      };
    },
  };
}

/** The image's legend: each line's colour and name, and the axis it reads on. */
function paintLegend(ctx, box, lines) {
  ctx.save();
  ctx.textBaseline = 'middle';
  ctx.lineWidth = 3;
  ctx.lineCap = 'round';
  lines.forEach((line, n) => {
    const y = box.y + n * LEGEND_ROW + LEGEND_ROW / 2;
    ctx.strokeStyle = COLORS[line.side];
    ctx.beginPath();
    ctx.moveTo(box.x, y);
    ctx.lineTo(box.x + 24, y);
    ctx.stroke();
    ctx.font = '500 18px Archivo, "Helvetica Neue", Arial, sans-serif';
    ctx.fillStyle = INK;
    ctx.fillText(line.label, box.x + 36, y);
    const after = box.x + 36 + ctx.measureText(line.label).width;
    ctx.fillStyle = INK_3;
    ctx.fillText(` · ${line.side ? gettext('right axis') : gettext('left axis')}`, after, y);
  });
  ctx.restore();
}
