// Casualties by country: one column per chosen country, soldiers and civilians stacked, with a faint segment up to the
// highest estimate. Needs the global `echarts`, and Django's gettext and interpolate.
import { whenFinished } from './chart-image.js';
import { escapeHtml, formatTick } from './format.js';
import { DEATH_COLORS, FONT, INK_2, formatRange } from './ww2.js';

export const MORE_COLOR = 'rgba(182, 185, 189, 0.3)';
const INK_3 = '#8b8f94';
const GRID = '#2c2e30';

/**
 * What a country's column holds for the parts shown: {soldiers, civilians, more}, in people, or null without a figure.
 * With both parts, the column is the lowest total estimate: soldiers are the lowest military estimate and civilians
 * the rest, since Wikipedia's totals do not always equal the sum of its parts.
 * With one part, the column is that part's lowest estimate. `more` runs on to the highest estimate.
 */
export function columnOf(row, show) {
  const low = (pair) => pair[0] ?? null;
  const high = (pair) => pair[1] ?? pair[0] ?? null;
  const civilians = (row.civilian[0] ?? 0) + (row.famine[0] ?? 0);
  const civiliansHigh = (high(row.civilian) ?? 0) + (high(row.famine) ?? 0);
  if (show.soldiers && show.civilians) {
    if (!low(row.total)) return null;
    const soldiers = Math.min(row.military[0] ?? Math.max(row.total[0] - civilians, 0), row.total[0]);
    return { soldiers, civilians: row.total[0] - soldiers, more: high(row.total) - row.total[0] };
  }
  if (show.soldiers) {
    if (low(row.military) === null) return null;
    return { soldiers: row.military[0], civilians: 0, more: high(row.military) - row.military[0] };
  }
  if (!civilians && row.civilian[0] === null && row.famine[0] === null) return null;
  return { soldiers: 0, civilians, more: civiliansHigh - civilians };
}

/** The chosen countries with a column, largest first. */
export function columns(rows, codes, show) {
  return codes.map((code) => rows.find((row) => row.code === code)).filter(Boolean)
    .map((row) => [row, columnOf(row, show)])
    .filter(([, column]) => column)
    .map(([row, column]) => ({ row, ...column }))
    .sort((a, b) => b.soldiers + b.civilians - (a.soldiers + a.civilians));
}

function shortName(name) {
  return name.length > 16 ? `${name.slice(0, 15)}…` : name;
}

export function createCasualtiesChart(element, { units, animate = true }) {
  const chart = echarts.init(element, null, { renderer: 'canvas' });
  const observer = new ResizeObserver(() => chart.resize());
  observer.observe(element);
  const rule = units.people;

  function render(rows, codes, show) {
    const shown = columns(rows, codes, show);
    const narrow = element.clientWidth < 560 || shown.length > 10;
    const rich = { name: { color: INK_2, fontSize: 11, fontWeight: 600, fontFamily: FONT, lineHeight: 14 } };
    for (const { row } of shown) {
      rich[`f_${row.code}`] = { width: narrow ? 18 : 24, height: narrow ? 13.5 : 18, backgroundColor: { image: row.flag }, borderRadius: 2 };
    }
    const byCode = Object.fromEntries(shown.map((column) => [column.row.code, column]));
    const part = (key, name, color) => ({
      id: key, name, type: 'bar', stack: 'deaths', color, barMaxWidth: 56, barCategoryGap: '36%',
      data: shown.map((column) => column[key]),
      itemStyle: { borderRadius: key === 'more' ? [4, 4, 0, 0] : 0 },
      emphasis: { focus: 'none' },
    });
    chart.setOption({
      animation: animate,
      animationDuration: 400,
      animationEasing: 'cubicOut',
      grid: { left: 8, right: 12, top: 16, bottom: 8, containLabel: true },
      xAxis: {
        type: 'category',
        data: shown.map((column) => column.row.code),
        axisLine: { lineStyle: { color: '#3a3d41' } },
        axisTick: { show: false },
        axisLabel: {
          interval: 0,
          margin: 10,
          formatter: (code) => (narrow ? `{f_${code}|}` : `{f_${code}|}\n{name|${shortName(byCode[code].row.name)}}`),
          rich,
        },
      },
      yAxis: {
        type: 'value',
        splitNumber: 5,
        splitLine: { lineStyle: { color: GRID, width: 1 } },
        axisLabel: { color: INK_3, fontSize: 11, fontFamily: FONT, formatter: (v) => formatTick(v, rule) },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(255, 255, 255, 0.04)' } },
        backgroundColor: '#17191b',
        borderColor: '#3a3d41',
        padding: [10, 12],
        extraCssText: 'border-radius:10px;box-shadow:0 12px 30px rgb(0 0 0 / .5);',
        formatter(params) {
          const { row } = byCode[params[0].axisValue];
          const line = (label, value) => `<div class="tip__line"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
          return `<div class="tip"><div class="tip__head"><img src="${escapeHtml(row.flag)}" alt="">${escapeHtml(row.name)}</div>`
            + `<div class="tip__value">${escapeHtml(formatRange(row.total, units))}</div>`
            + (show.soldiers ? line(gettext('Soldiers'), formatRange(row.military, units)) : '')
            + (show.civilians ? line(gettext('Civilians'), formatRange(row.civilian, units)) + line(gettext('Famine and disease'), formatRange(row.famine, units)) : '')
            + (row.share[0] === null ? '' : `<div class="tip__muted">${escapeHtml(interpolate(gettext('%s of its people in 1939'), [formatRange(row.share, units, units.percent)]))}</div>`)
            + '</div>';
        },
      },
      series: [
        part('soldiers', gettext('Soldiers'), DEATH_COLORS.soldiers),
        part('civilians', gettext('Civilians'), DEATH_COLORS.civilians),
        part('more', gettext('Up to the highest estimate'), MORE_COLOR),
      ],
    }, { replaceMerge: ['series', 'xAxis'] });
    return shown.map((column) => column.row.code);
  }

  function dispose() {
    observer.disconnect();
    chart.dispose();
  }

  return { render, dispose, chart };
}

/** What saveChartImage needs for the casualties chart: how to draw it, and the key under it. */
export function casualtiesImageParts(rows, codes, show, units) {
  return {
    belowHeight: 44,
    async draw(element) {
      const bars = createCasualtiesChart(element, { units, animate: false });
      const finished = whenFinished(bars.chart);
      bars.render(rows, codes, show);
      await finished;
      return { chart: bars.chart, dispose: bars.dispose, below: (ctx, box) => paintKey(ctx, box, show) };
    },
  };
}

function paintKey(ctx, box, show) {
  const keys = [
    show.soldiers && [DEATH_COLORS.soldiers, gettext('Soldiers')],
    show.civilians && [DEATH_COLORS.civilians, gettext('Civilians')],
    ['rgba(182, 185, 189, 0.45)', gettext('Up to the highest estimate')],
  ].filter(Boolean);
  ctx.save();
  ctx.font = `600 17px ${FONT}`;
  ctx.textBaseline = 'middle';
  let x = box.x;
  for (const [color, label] of keys) {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.roundRect(x, box.y + 4, 16, 14, 3);
    ctx.fill();
    ctx.fillStyle = INK_2;
    ctx.fillText(label, x + 24, box.y + 11);
    x += 24 + ctx.measureText(label).width + 30;
  }
  ctx.restore();
}

