// Countries over time: one line per country, its flag and name at the end of the line. Needs the global `echarts`.
// gettext is Django's, from the translation catalog base.html loads.
import { escapeHtml, formatTick, formatValue } from './format.js';

// The validated eight-colour order (dark surface). A country keeps its colour while it stays selected.
export const PALETTE = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'];
export const WORLD_COLOR = '#c9ccd0';
const WORLD = 'WLD';
const INK_2 = '#b6b9bd';
const INK_3 = '#8b8f94';
const GRID = '#2c2e30';

export function createLineChart(element, { units }) {
  const chart = echarts.init(element, null, { renderer: 'canvas' });
  new ResizeObserver(() => chart.resize()).observe(element);

  function render(data, selected) {
    const rule = units[data.unit];
    const narrow = element.clientWidth < 560;
    const lines = selected
      .filter(({ iso3 }) => data.values[iso3])
      .map(({ iso3, color }) => {
        const country = data.countries[iso3];
        const world = iso3 === WORLD;
        return {
          id: iso3,
          name: country.name,
          type: 'line',
          data: data.values[iso3],
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
      animationDuration: 500,
      animationEasing: 'cubicOut',
      grid: { left: 8, right: narrow ? 34 : 150, top: 20, bottom: 8, containLabel: true },
      xAxis: {
        type: 'category',
        data: data.years,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#3a3d41' } },
        axisTick: { show: false },
        axisLabel: { color: INK_3, fontFamily: 'JetBrains Mono, monospace', fontSize: 11, hideOverlap: true },
      },
      yAxis: {
        type: 'value',
        scale: true,
        splitNumber: 5,
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
          const rows = params
            .filter((p) => p.value !== null && p.value !== undefined)
            .sort((a, b) => b.value - a.value)
            .map((p) => {
              const country = data.countries[p.seriesId];
              return `<div class="tip__row"><i style="background:${p.color}"></i>`
                + `<img src="${escapeHtml(country.flag)}" alt=""><span>${escapeHtml(country.name)}</span>`
                + `<strong>${escapeHtml(formatValue(p.value, rule))}</strong></div>`;
            });
          const year = escapeHtml(params[0]?.axisValue ?? '');
          return `<div class="tip"><div class="tip__head">${year}</div>${rows.join('') || `<div class="tip__muted">${escapeHtml(gettext('No data'))}</div>`}</div>`;
        },
      },
      series: lines,
    }, { replaceMerge: ['series'] });
    return lines.map((line) => line.id);
  }

  return { render, chart };
}

function shortName(name) {
  return name.length > 18 ? `${name.slice(0, 17)}…` : name;
}
