// A kind of crime by state, under its chart on a country's Politics page: a map in the measure open above, a year
// dropdown when there are several years, the states ranked beside the map, and the numbers in a table.
// The data come with the chart's (politics/crime_series.py, states); the shapes from the country's states.json.
// gettext and interpolate are Django's, from the translation catalog base.html loads.
import { bindSaveButton, imageName, saveChartImage } from './chart-image.js';
import { escapeHtml, formatValue } from './format.js';
import { createStatesReel } from './states-reel.js';
import { createChoropleth, mapImageParts, project, renderLegend } from './world-map.js';

/** The borders of one country's states, loaded from `url` once, for createChoropleth. */
function stateShapes(url) {
  const names = new Map();
  let loading = null;
  const shapes = {
    name: url,  // the name ECharts registers them under
    key: 'code',
    aspect: 1,  // the projected map's width over its height, known once the shapes are in
    nameOf: (code) => names.get(code),
    features: [],  // the GeoJSON features, for the video, which paints them itself (lib/states-reel.js)
    bounds: null,  // their projected bounds
    load: () => (loading ??= fetch(url).then((response) => response.json()).then((geojson) => {
      let [left, top, right, bottom] = [Infinity, Infinity, -Infinity, -Infinity];
      for (const feature of geojson.features) {
        names.set(feature.properties.code, feature.properties.name);
        for (const polygon of feature.geometry.coordinates) {
          for (const [x, y] of polygon[0].map(project)) {
            [left, top, right, bottom] = [Math.min(left, x), Math.min(top, y), Math.max(right, x), Math.max(bottom, y)];
          }
        }
      }
      shapes.aspect = (right - left) / (bottom - top);
      shapes.features = geojson.features;
      shapes.bounds = { left, top, right, bottom };
      echarts.registerMap(url, geojson);
    })),
  };
  return shapes;
}

/**
 * Wires the card inside `card` (templates/politics/country.html, data-states-card).
 * `page` gives the units, the shapes' address, and the country's name and flag for the saved image.
 * Returns { show(states, metric, field, sourceHtml) }: states is the chart data's `states`, or null to hide the card.
 */
export function createStatesView(card, page) {
  const { units } = page;
  const shapes = stateShapes(page.statesUrl);
  const map = createChoropleth(card.querySelector('[data-states-map]'), { units, shapes });
  const title = card.querySelector('[data-states-title]');
  const label = card.querySelector('[data-states-label]');
  const years = card.querySelector('[data-states-years]');
  const yearSelect = card.querySelector('[data-states-year]');
  const source = card.querySelector('[data-states-source]');
  const list = card.querySelector('[data-states-list]');
  const legend = card.querySelector('[data-states-legend]');
  const note = card.querySelector('[data-states-note]');
  const table = card.querySelector('[data-states-table]');
  const state = { data: null, year: null, metric: '', field: '' };

  async function show(states, metric, field, sourceHtml) {
    card.hidden = !states;
    state.data = states;
    if (!states) return;
    state.metric = metric;
    state.field = field;
    // The year stays when the next measure has it; otherwise the latest.
    if (!states.years.includes(state.year)) state.year = states.years.at(-1);
    title.textContent = states.title;
    label.textContent = `· ${states.label}`;
    source.innerHTML = sourceHtml;
    note.textContent = states.note;
    note.hidden = !states.note;
    years.hidden = states.years.length < 2;
    yearSelect.innerHTML = [...states.years].reverse()
      .map((year) => `<option value="${year}"${year === state.year ? ' selected' : ''}>${year}</option>`).join('');
    drawTable();
    await draw();
  }

  async function draw() {
    const { scale } = await map.render(state.data, state.year);
    renderLegend(legend, state.data, scale, units, state.data.median);
    drawList();
  }

  // The states with a value in the year, highest first; pointing at one shows it on the map.
  function drawList() {
    const { data, year } = state;
    const i = data.years.indexOf(year);
    const rule = units[data.unit];
    const rows = Object.entries(data.values).filter(([, values]) => values[i] !== null).sort((a, b) => b[1][i] - a[1][i]);
    list.innerHTML = rows.map(([code, values], n) => `<li><span class="rank-list__n">${n + 1}</span>`
      + (data.countries[code]?.flag ? `<img class="flag" src="${escapeHtml(data.countries[code].flag)}" alt="" width="28" height="21" loading="lazy">` : '')
      + `<button type="button" data-state="${escapeHtml(code)}">${escapeHtml(data.countries[code]?.name || code)}</button>`
      + `<span class="rank-list__value">${escapeHtml(formatValue(values[i], rule))}</span></li>`).join('');
  }

  // Every state and year, the newest year first.
  function drawTable() {
    const { data } = state;
    const rule = units[data.unit];
    const order = data.years.map((_, i) => i).reverse();
    const codes = Object.keys(data.values).sort((a, b) => (data.countries[a]?.name || a).localeCompare(data.countries[b]?.name || b));
    const head = [data.stateLabel, ...order.map((i) => data.years[i])];
    table.innerHTML = `<thead><tr>${head.map((cell) => `<th scope="col">${escapeHtml(String(cell))}</th>`).join('')}</tr></thead><tbody>`
      + codes.map((code) => `<tr><td>${escapeHtml(data.countries[code]?.name || code)}</td>`
        + order.map((i) => `<td>${data.values[code][i] === null ? '–' : escapeHtml(formatValue(data.values[code][i], rule))}</td>`).join('')
        + '</tr>').join('') + '</tbody>';
  }

  yearSelect.addEventListener('change', () => {
    state.year = Number(yearSelect.value);
    draw();
  });

  // A state in the list lights up on the map, with its tooltip.
  const point = (event, on) => {
    const button = event.target.closest('[data-state]');
    if (!button) return;
    map.chart.dispatchAction({ type: on ? 'highlight' : 'downplay', name: button.dataset.state });
    map.chart.dispatchAction(on ? { type: 'showTip', seriesIndex: 0, name: button.dataset.state } : { type: 'hideTip' });
  };
  for (const [kind, on] of [['mouseover', true], ['focusin', true], ['mouseout', false], ['focusout', false]]) {
    list.addEventListener(kind, (event) => point(event, on));
  }

  const sourceText = () => source.textContent.replace(/\s+/g, ' ').trim();

  bindSaveButton(card.querySelector('[data-save-image]'), (size) => state.data && saveChartImage({
    size,
    title: page.title(),
    subtitle: `${page.country} · ${state.data.title} · ${state.data.label} · ${state.year}`,
    sources: [sourceText()],
    flag: page.flag,
    filename: imageName(page.country, state.metric, state.field, 'states', String(state.year)),
    ...mapImageParts(state.data, state.year, units, shapes),
  }));

  // The video of the map in the year shown (lib/states-reel.js): the states fill in from the best, then rank.
  async function createReel(format) {
    await shapes.load();
    const { data, year } = state;
    const reel = await createStatesReel({
      format, data, year, units, shapes,
      title: page.title(),
      explanation: page.summary(),
      flag: page.flag,
      subtitle: `${page.country} · ${data.title} · ${year}`,
      sources: [sourceText()],
    });
    const name = imageName(page.country, state.metric, state.field, 'states', String(year), format === 'wide' && 'wide');
    return { ...reel, filename: name.replace(/\.png$/, '.mp4') };
  }

  return { show, createReel, hasData: () => Boolean(state.data) };
}
