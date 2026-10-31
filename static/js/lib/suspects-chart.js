// Crime suspects by nationality: one column per chosen nationality, the country's own citizens in a colour of their own.
// A column is the share of the nationality's people whom the police registered as suspects of the chosen offences.
// Where the columns would be too narrow for their names (phones, and the saved image), they turn into rows.
// Needs the global `echarts`, and Django's gettext and interpolate.
import { FONT, whenFinished } from './chart-image.js';
import { escapeHtml, formatTick, formatValue, formatWhole } from './format.js';

export const COLORS = { own: '#c98500', foreign: '#3987e5' };
const INK_2 = '#b6b9bd';
const INK_3 = '#8b8f94';
const GRID = '#2c2e30';
const ROWS_BELOW = 640;  // px: a narrower chart draws rows
const ROW = 26;  // px per row, which sets the well's height
const NAMED = 84;  // px a column needs for its name under the flag; narrower columns slant their names under the flags
const ROWS_TOP = 30;  // px above the first row, clear of the well's save button

// Rows lay out their own left margin: ECharts 6 leaves the longest name partly outside the chart.
let measure = null;
function rowsLeft(names) {
  measure ??= document.createElement('canvas').getContext('2d');
  measure.font = `700 11px ${FONT}`;
  return 12 + Math.max(0, ...names.map((name) => measure.measureText(name).width)) + 7 + 20 + 10;  // margin, name, gap, flag, gap
}

export function shortName(name, length) {
  return name.length > length ? `${name.slice(0, length - 1)}…` : name;
}

/**
 * The chart in `element`. `own` is the code of the country's own citizens; `population` names the population in the tooltip.
 * With `well`, the chart sets the well's height when it draws rows, one row per nationality.
 */
export function createSuspectsChart(element, { units, own, population, well = null, animate = true }) {
  const chart = echarts.init(element, null, { renderer: 'canvas' });
  let last = null;  // the rows of the last render, to draw again when the width calls for the other layout
  let drawnAsRows = null;
  const observer = new ResizeObserver(() => {
    if (last && (element.clientWidth < ROWS_BELOW) !== drawnAsRows) render(last);
    else chart.resize();
  });
  observer.observe(element);
  const percent = units.percent;

  /** Draws `shown`: [{ code, name, flag, population, suspects, value }], the largest share first. */
  function render(shown) {
    last = shown;
    const asRows = element.clientWidth < ROWS_BELOW;
    drawnAsRows = asRows;
    if (well) well.style.height = asRows && shown.length ? `${shown.length * ROW + ROWS_TOP + 40}px` : '';
    chart.resize();
    const named = !asRows && element.clientWidth / Math.max(shown.length, 1) >= NAMED;
    // Slanted names take room under the columns, so the well grows to keep the columns' height.
    well?.classList.toggle('is-slanted', !asRows && !named);
    const byCode = Object.fromEntries(shown.map((row) => [row.code, row]));
    const rich = {
      // In rows, the name's padding keeps it off the flag: ECharts measures padding, but not plain spaces between parts.
      name: { color: INK_2, fontSize: 11, fontWeight: 600, fontFamily: FONT, lineHeight: 14, padding: asRows ? [0, 7, 0, 0] : 0 },
      own: { color: COLORS.own, fontSize: 11, fontWeight: 700, fontFamily: FONT, lineHeight: 14, padding: asRows ? [0, 7, 0, 0] : 0 },
    };
    for (const row of shown) {
      rich[`f_${row.code}`] = { width: 20, height: 15, backgroundColor: { image: row.flag }, borderRadius: 2 };
    }
    const label = (code) => {
      const row = byCode[code];
      const style = code === own ? 'own' : 'name';
      if (asRows) return `{${style}|${shortName(row.name, 15)}}{f_${code}|}`;
      return named ? `{f_${code}|}\n{${style}|${shortName(row.name, 12)}}` : `{f_${code}|}`;
    };
    const category = {
      type: 'category',
      data: shown.map((row) => row.code),
      inverse: asRows,  // rows run from the largest share at the top
      axisLine: { lineStyle: { color: '#3a3d41' } },
      axisTick: { show: false },
      // The label's own font matches its rich parts', so the grid makes room for the longest name.
      axisLabel: { interval: 0, margin: 10, fontSize: 11, fontWeight: 600, fontFamily: FONT, formatter: label, rich },
    };
    const value = {
      type: 'value',
      splitNumber: asRows ? 4 : 5,
      splitLine: { lineStyle: { color: GRID, width: 1 } },
      axisLabel: { color: INK_3, fontSize: 11, fontFamily: FONT, formatter: (v) => formatTick(v, percent) },
    };
    chart.setOption({
      animation: animate,
      animationDuration: 400,
      animationEasing: 'cubicOut',
      grid: asRows
        ? { left: rowsLeft(shown.map((row) => shortName(row.name, 15))), right: 48, top: ROWS_TOP, bottom: 24, containLabel: false, outerBoundsMode: 'none' }
        : { left: 12, right: 12, top: 22, bottom: 8, containLabel: true },
      xAxis: asRows ? value : named ? category : [category, slanted(shown, rich)],
      yAxis: asRows ? category : value,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(255, 255, 255, 0.04)' } },
        backgroundColor: '#17191b',
        borderColor: '#3a3d41',
        padding: [10, 12],
        extraCssText: 'border-radius:10px;box-shadow:0 12px 30px rgb(0 0 0 / .5);',
        formatter(params) {
          const row = byCode[params[0].axisValue];
          const line = (text, amount) => `<div class="tip__line"><span>${escapeHtml(text)}</span><strong>${escapeHtml(amount)}</strong></div>`;
          return `<div class="tip"><div class="tip__head"><img src="${escapeHtml(row.flag)}" alt="">${escapeHtml(row.name)}</div>`
            + `<div class="tip__value">${escapeHtml(formatValue(row.value, percent))}</div>`
            + `<div class="tip__muted">${escapeHtml(gettext('of its people were suspects'))}</div>`
            + line(gettext('Suspects'), formatWhole(row.suspects, units))
            + line(population, formatWhole(row.population, units))
            + '</div>';
        },
      },
      series: [{
        type: 'bar',
        barMaxWidth: asRows ? 16 : 40,
        barCategoryGap: '30%',
        data: shown.map((row) => ({ value: row.value, itemStyle: { color: row.code === own ? COLORS.own : COLORS.foreign } })),
        itemStyle: { borderRadius: asRows ? [0, 4, 4, 0] : [4, 4, 0, 0] },
        label: {
          show: true,
          position: asRows ? 'right' : 'top',
          color: INK_2,
          fontSize: 10.5,
          fontFamily: FONT,
          formatter: ({ value: share }) => formatValue(share, percent),
        },
        emphasis: { focus: 'none' },
      }],
    }, { replaceMerge: ['series', 'xAxis', 'yAxis'] });
  }

  // Narrow columns: the flags stay upright on the first axis, and a second axis under them slants the names.
  function slanted(rows, rich) {
    const names = Object.fromEntries(rows.map((row) => [row.code, shortName(row.name, 18)]));
    return {
      type: 'category',
      data: rows.map((row) => row.code),
      position: 'bottom',
      offset: 22,
      axisLine: { show: false },
      axisTick: { show: false },
      axisPointer: { show: false },
      axisLabel: {
        interval: 0, rotate: 45, margin: 6, fontSize: 11, fontWeight: 600, fontFamily: FONT, color: INK_2,
        formatter: (code) => (code === own ? `{own|${names[code]}}` : names[code]),
        rich: { own: rich.own },
      },
    };
  }

  function dispose() {
    observer.disconnect();
    chart.dispose();
  }

  return { render, dispose, chart };
}

/**
 * What saveChartImage needs for the chart: how to draw it, and the key under it.
 * `ownName` names the country's citizens; `note`, under the key, says which nationalities the bars are.
 */
export function suspectsImageParts(shown, { ownName, note = '', ...options }) {
  return {
    belowHeight: note ? 74 : 44,
    async draw(element) {
      const bars = createSuspectsChart(element, { ...options, animate: false });
      const finished = whenFinished(bars.chart);
      bars.render(shown);
      await finished;
      return { chart: bars.chart, dispose: bars.dispose, below: (ctx, box) => paintKey(ctx, box, ownName, 17, note) };
    },
  };
}

/** The key under the image: the country's citizens and foreign nationals, each with its colour, and a `note` under them. */
export function paintKey(ctx, box, ownName, size = 17, note = '') {
  ctx.save();
  ctx.font = `600 ${size}px ${FONT}`;
  ctx.textBaseline = 'middle';
  let x = box.x;
  for (const [color, text] of [[COLORS.own, ownName], [COLORS.foreign, gettext('Foreign nationals')]]) {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.roundRect(x, box.y + 4, size - 1, size * 0.82, 3);
    ctx.fill();
    ctx.fillStyle = INK_2;
    ctx.fillText(text, x + size + 8, box.y + 4 + size * 0.41);
    x += size + 8 + ctx.measureText(text).width + size * 1.8;
  }
  if (note) {
    ctx.fillStyle = INK_3;
    ctx.font = `400 ${size - 2}px ${FONT}`;
    ctx.fillText(note, box.x, box.y + 4 + size * 1.95);
  }
  ctx.restore();
}
