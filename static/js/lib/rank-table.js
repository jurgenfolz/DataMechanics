// Every country of a metric in one year as a table: its rank in the world that year, its flag and name, its value.
// The rank never changes: a continent filter and the sortable columns only reorder or hide rows.
// gettext and interpolate are Django's, from the translation catalog base.html loads.
import { escapeHtml, formatValue } from './format.js';

const WORLD = 'WLD';

// Natural Earth's continents, as the data names them, with the page's words for them. Other rows (islands of the
// open ocean, Antarctica) show only under "All continents".
export const CONTINENTS = [
  ['Africa', () => gettext('Africa')],
  ['Asia', () => gettext('Asia')],
  ['Europe', () => gettext('Europe')],
  ['North America', () => gettext('North America')],
  ['Oceania', () => gettext('Oceania')],
  ['South America', () => gettext('South America')],
];

/** The countries with a value in `year`, ranked by it, the highest first: [{ iso3, name, flag, continent, value, rank }]. */
export function rankedRows(data, year) {
  const i = data.years.indexOf(year);
  return Object.entries(data.values)
    .filter(([iso3, values]) => iso3 !== WORLD && values[i] !== null && values[i] !== undefined)
    .map(([iso3, values]) => ({ iso3, value: values[i], ...data.countries[iso3], name: data.countries[iso3]?.name || iso3 }))
    .sort((a, b) => b.value - a.value)
    .map((row, n) => ({ ...row, rank: n + 1 }));
}

/**
 * The table in `container`. Returns { render(data, year, { continent, sort }) }: `continent` is a key of CONTINENTS or
 * '' for all, `sort` is { by: 'rank' | 'name' | 'value', desc }. `onSort(sort)` is called when a heading is pressed.
 */
export function createRankTable(container, { units, onSort }) {
  let current = null;

  function render(data, year, { continent = '', sort = { by: 'rank', desc: false } } = {}) {
    current = { data, year, continent, sort };
    const rule = units[data.unit];
    const all = rankedRows(data, year);
    const rows = all.filter((row) => !continent || row.continent === continent);
    const compare = {
      rank: (a, b) => a.rank - b.rank,
      name: (a, b) => a.name.localeCompare(b.name),
      value: (a, b) => a.value - b.value,
    }[sort.by] || ((a, b) => a.rank - b.rank);
    rows.sort((a, b) => (sort.desc ? -compare(a, b) : compare(a, b)));
    const heading = (by, text, numeric) => {
      const active = sort.by === by;
      const aria = active ? (sort.desc ? 'descending' : 'ascending') : 'none';
      return `<th scope="col" aria-sort="${aria}"${numeric ? ' class="is-numeric"' : ''}>`
        + `<button type="button" data-sort="${by}">${escapeHtml(text)}<span class="rank-table__arrow" aria-hidden="true"></span></button></th>`;
    };
    container.innerHTML = `<table class="rank-table"><thead><tr>${heading('rank', gettext('Rank'), true)}${heading('name', gettext('Country'))}`
      + `${heading('value', data.label, true)}</tr></thead><tbody>`
      + rows.map((row) => `<tr><td class="rank-table__rank">${row.rank}</td>`
        + `<td class="rank-table__country">${row.flag ? `<img class="flag" src="${escapeHtml(row.flag)}" alt="" width="24" height="18" loading="lazy">` : ''}`
        + `<span>${escapeHtml(row.name)}</span></td>`
        + `<td class="rank-table__value">${escapeHtml(formatValue(row.value, rule))}</td></tr>`).join('')
      + '</tbody></table>';
    return { shown: rows.length, all: all.length };
  }

  // A press on a heading sorts by it; a second press turns the order round. Rank and name start ascending, values
  // descending, the highest first.
  container.addEventListener('click', (event) => {
    const button = event.target.closest('[data-sort]');
    if (!button || !current) return;
    const by = button.dataset.sort;
    const sort = current.sort.by === by ? { by, desc: !current.sort.desc } : { by, desc: by === 'value' };
    onSort?.(sort);
  });

  return { render };
}
