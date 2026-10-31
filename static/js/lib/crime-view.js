// Crime suspects by nationality on a country's Politics page: a column per nationality, with the share of its people
// whom the police registered as suspects of the chosen kinds of offence.
// The country's own citizens and the 20 foreign nationalities with the highest shares open the chart.
// Those 20 follow the chosen offences, until the nationalities are picked by hand.
// One picker chooses the kinds of offence, as a tree under Total; the other adds and removes nationalities.
// Both live in the URL (?offences=, ?nationalities=).
// gettext, ngettext and interpolate are Django's, from the translation catalog base.html loads.
import { bindSaveButton, imageName, saveChartImage } from './chart-image.js';
import { createCrimeReel, ROWS } from './crime-reel.js';
import { escapeHtml, formatValue, formatWhole } from './format.js';
import { createPicker } from './picker.js';
import { createSuspectsChart, suspectsImageParts } from './suspects-chart.js';
import { cover, createTreePicker, leaves } from './tree-picker.js';

const MAX = 30;

/**
 * Wires the tab inside `root` (templates/politics/_crime.html) to `config` (politics/crime.py, data).
 * `page` gives the country's name, flag and units, and the title for images and videos.
 * Returns { show(), createReel(format) }: show draws the chart once its tab is open, since a hidden element has no size,
 * and createReel builds the tab's video (lib/crime-reel.js).
 */
export function createCrimeView(root, config, page) {
  const card = root.querySelector('[data-crime-card]');
  const well = card.querySelector('[data-crime-well]');
  const empty = card.querySelector('[data-crime-empty]');
  const summary = card.querySelector('[data-crime-summary]');
  const top = card.querySelector('[data-crime-top]');
  const overlap = card.querySelector('[data-crime-overlap]');
  const table = card.querySelector('[data-crime-table]');
  const { units } = page;
  const tree = config.offences;
  const everyLeaf = leaves(tree);
  const nodes = new Map();
  (function index(node) {
    nodes.set(node.key, node);
    node.children.forEach(index);
  }(tree));
  const rows = config.nationalities;
  const ownName = interpolate(gettext('Citizens of %s'), [page.country]);

  const params = new URLSearchParams(window.location.search);
  const asked = (params.get('offences') || '').split(',').filter((key) => nodes.has(key));
  const state = {
    offences: new Set(asked.length ? asked.flatMap((key) => leaves(nodes.get(key))) : everyLeaf),
    // The nationalities picked by hand, or null while the chart shows the highest shares (`opening`).
    codes: (params.get('nationalities') || '').split(',').filter((code) => rows.some((row) => row.code === code)),
  };
  if (!state.codes.length) state.codes = null;
  let chart = null;

  // ---------- The chosen offences ----------
  // A whole kind of offence counts with the BKA's own number, which counts each person once.
  // Offences under other laws have no such number here (politics/crime.py), so theirs is the sum of their groups.
  const countOf = (node, counts) => (node.summed
    ? node.children.reduce((sum, child) => sum + countOf(child, counts), 0)
    : counts[node.key] ?? 0);
  const chosen = () => (state.offences.size ? cover(tree, state.offences) : []);
  const suspectsOf = (counts) => chosen().reduce((sum, node) => sum + countOf(node, counts), 0);
  // More than one count added up can count a person more than once.
  const overlapping = () => chosen().length > 1 || chosen().some((node) => node.summed);
  const isAll = () => state.offences.size === everyLeaf.length;

  /** The choice on the button: All offences, one kind, or the first kind and how many more. */
  function describe(keys) {
    if (keys.size === everyLeaf.length) return gettext('All offences');
    const picked = cover(tree, keys);
    if (!picked.length) return gettext('No offence');
    return picked.length === 1 ? picked[0].name : `${picked[0].name} +${picked.length - 1}`;
  }

  /** The choice as images and videos say it: every kind of offence named, or how many there are. */
  function offenceText() {
    if (isAll()) return gettext('All offences but those against residence and asylum law');
    const picked = chosen();
    return picked.length <= 3 ? picked.map((node) => node.name).join(', ')
      : interpolate(ngettext('%s kind of offence', '%s kinds of offence', picked.length), [picked.length]);
  }

  const offencePicker = createTreePicker(card.querySelector('[data-crime-offences]'), {
    tree,
    describe,
    noMatch: gettext('No offence matches.'),
    onChange: (keys) => {
      state.offences = keys;
      draw();
    },
  });

  const nationalityPicker = createPicker(card.querySelector('[data-crime-nationalities]'), {
    max: MAX,
    emptyLabel: gettext('Choose nationalities'),
    noMatch: gettext('No nationality matches.'),
    onToggle: (code) => {
      const codes = picked();
      state.codes = codes.includes(code) ? codes.filter((c) => c !== code) : [...codes, code];
      draw();
    },
  });
  nationalityPicker.setOptions(rows.map((row) => ({ id: row.code, name: row.name, image: row.flag })));

  /** A nationality with its suspects of the chosen offences and their share of its people. */
  function measured(row) {
    const suspects = suspectsOf(row.suspects);
    return { ...row, suspects, value: (suspects / row.population) * 100 };
  }

  /** The country's citizens and the foreign nationalities with the highest shares for the chosen offences. */
  function opening() {
    const highest = rows.filter((row) => row.code !== config.own).map(measured).sort((a, b) => b.value - a.value)
      .slice(0, config.highest).map((row) => row.code);
    return [config.own, ...highest];
  }

  const picked = () => state.codes ?? opening();

  /** The chosen nationalities, the largest share first. */
  function shown() {
    if (!state.offences.size) return [];
    return picked().map((code) => rows.find((row) => row.code === code)).filter(Boolean).map(measured)
      .sort((a, b) => b.value - a.value);
  }

  /** What the chart shows while nobody has picked the nationalities: the highest shares, and the citizens. */
  const highestText = (count) => interpolate(ngettext(
    'Shown: the %(count)s foreign nationality with the highest share, and the citizens of %(country)s.',
    'Shown: the %(count)s foreign nationalities with the highest shares, and the citizens of %(country)s.', count),
  { count, country: page.country }, true);

  // The button brings back the highest shares, which then follow the chosen offences again.
  top.addEventListener('click', () => {
    state.codes = null;
    draw();
  });

  function draw() {
    const bars = shown();
    top.setAttribute('aria-pressed', String(state.codes === null));
    chart.render(bars);
    empty.hidden = bars.length > 0;
    empty.textContent = state.offences.size ? gettext('Choose a nationality to see its share.')
      : gettext('Choose a kind of offence to see the shares.');
    offencePicker.setSelected(state.offences);
    nationalityPicker.setSelected(picked());
    overlap.hidden = !overlapping();
    drawSummary();
    drawTable();
    syncUrl();
  }

  function drawSummary() {
    if (!state.offences.size) {
      summary.textContent = '';
      return;
    }
    const own = rows.find((row) => row.code === config.own);
    const text = isAll()
      ? gettext('The share of each nationality’s people in %(country)s whom the police registered as a suspect in %(year)s: %(own)s of the citizens of %(country)s, %(foreign)s of all foreign nationals together.')
      : gettext('The share of each nationality’s people in %(country)s whom the police registered as a suspect of the chosen offences in %(year)s: %(own)s of the citizens of %(country)s, %(foreign)s of all foreign nationals together.');
    summary.textContent = [interpolate(text, {
      country: page.country,
      year: config.year,
      own: formatValue(measured(own).value, units.percent),
      foreign: formatValue(measured(config.foreign).value, units.percent),
    }, true), state.codes ? '' : highestText(config.highest)].filter(Boolean).join(' ');
  }

  // Every nationality, the most people first.
  function drawTable() {
    const heads = [gettext('Nationality'), config.population, gettext('Suspects'), gettext('Share of its people')];
    table.innerHTML = `<thead><tr>${heads.map((head) => `<th scope="col">${escapeHtml(head)}</th>`).join('')}</tr></thead>`
      + `<tbody>${rows.map(measured).map((row) => `<tr><th scope="row"><span class="war-table__state"><img class="flag" src="${escapeHtml(row.flag)}" alt="" width="20" height="15" loading="lazy">${escapeHtml(row.name)}</span></th>`
        + `<td>${formatWhole(row.population, units)}</td><td>${formatWhole(row.suspects, units)}</td>`
        + `<td>${escapeHtml(formatValue(row.value, units.percent))}</td></tr>`).join('')}</tbody>`;
  }

  function syncUrl() {
    const next = new URLSearchParams(window.location.search);
    if (isAll()) next.delete('offences');
    else next.set('offences', chosen().map((node) => node.key).join(','));
    if (state.codes) next.set('nationalities', state.codes.join(','));
    else next.delete('nationalities');
    window.history.replaceState(null, '', `${window.location.pathname}?${next}`);
  }

  const sourceLines = () => config.sources.map((source) => `${gettext('Source:')} ${source.name}`
    + (source.updated ? ` (${interpolate(gettext('updated %s'), [source.updated])})` : ''));

  bindSaveButton(card.querySelector('[data-save-image]'), (size) => saveChartImage({
    size,
    title: page.title,
    subtitle: isAll()
      ? interpolate(gettext('Suspects in %(year)s as a share of each nationality’s people in %(country)s'),
        { country: page.country, year: config.year }, true)
      : interpolate(gettext('%(offences)s: suspects in %(year)s as a share of each nationality’s people'),
        { offences: offenceText(), year: config.year }, true),
    sources: sourceLines(),
    flag: page.flag,
    filename: imageName(page.country, 'crime-suspects', config.year, !isAll() && chosen().map((node) => node.key).join('-')),
    ...suspectsImageParts(shown(), { units, own: config.own, population: config.population, ownName,
      note: state.codes ? '' : highestText(config.highest) }),
  }));

  async function createReel(format) {
    // A video shows as many bars as a phone can read: the citizens and the foreign nationalities with the highest shares.
    const all = shown();
    const kept = all.filter((row) => row.code !== config.own).slice(0, ROWS[format] - 1);
    const rows = all.filter((row) => row.code === config.own || kept.includes(row));
    const explanation = [
      interpolate(gettext('The share of each nationality’s people in %s whom the police registered as a suspect.'), [page.country]),
      // Picked by hand, the bars need no word unless the video leaves some out.
      !state.codes || rows.length < all.length ? highestText(kept.length) : '',
      overlapping() ? gettext('With several kinds of offence chosen, a person suspected of more than one counts once for each.') : '',
    ].filter(Boolean).join(' ');
    const reel = await createCrimeReel({
      format,
      title: page.title,
      unit: String(config.year),
      subtitle: offenceText(),
      explanation,
      flag: page.flag,
      sources: [`${gettext('Sources:')} ${config.sources.map((source) => source.name).join('; ')}`],
      rows,
      own: config.own,
      ownName,
      foreign: { name: gettext('All foreign nationals together'), ...measured(config.foreign) },
      population: config.population,
      limits: config.limits,
      units,
    });
    reel.filename = imageName(page.country, 'crime-suspects', config.year, format === 'wide' && 'wide').replace(/\.png$/, '.mp4');
    return reel;
  }

  function show() {
    chart ??= createSuspectsChart(card.querySelector('[data-crime-chart]'),
      { units, own: config.own, population: config.population, well });
    draw();
  }

  return { show, createReel };
}
