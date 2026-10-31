// The party compass on a country's Politics page: where one expert survey at a time places the parties on two axes.
// The survey and the parties shown are picked above the chart; the survey lives in the URL (?survey=).
// Pointing at a logo shows the party's tooltip beside it, never over it; pressing the logo pins the tooltip.
// Switching the survey slides each party from its old place to its new one, which shows how far the surveys disagree.
// A party a survey left out has an inferred place: an asterisk on the chart, a note in its tooltip, and a list under the chart.
// gettext, ngettext and interpolate are Django's, from the translation catalog base.html loads.
import {
  bindSaveButton, handOver, imageFrame, imageName, imageWell, loadImage, SCALE, sizedName,
} from './chart-image.js';
import { compassPlot, darkLogo, markerAt, paintCompass, placeMarkers, tileSize, tileWidth } from './compass.js';
import { createCompassReel } from './compass-reel.js';
import { badgeText, escapeHtml } from './format.js';
import { createPicker } from './picker.js';

const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const SLIDE = 650;  // ms a party takes to slide to its place in another survey
const PAD = { top: 14, right: 14, bottom: 30, left: 34 };

/**
 * Wires the compass inside `root` (templates/politics/_compass.html) to `config` (politics/compass.py, data).
 * `page` gives the country's name, flag and the title for images and videos.
 * Returns { show(), openReel(mode) }: show() draws it once its tab is open, since a hidden canvas has no size.
 */
export function createCompassView(root, config, page) {
  const card = root.querySelector('[data-compass-card]');
  const well = root.querySelector('[data-compass-well]');
  const canvas = root.querySelector('[data-compass]');
  const tip = root.querySelector('[data-tip]');
  const surveySelect = root.querySelector('[data-survey]');
  const surveyLabel = root.querySelector('[data-survey-label]');
  const source = root.querySelector('[data-compass-source]');
  const method = root.querySelector('[data-method]');
  const citation = root.querySelector('[data-citation]');
  const inferredNote = root.querySelector('[data-inferred]');
  const table = root.querySelector('[data-compass-table]');
  const params = new URLSearchParams(window.location.search);
  const surveys = new Map(config.surveys.map((survey) => [survey.key, survey]));
  const number = new Intl.NumberFormat(document.documentElement.lang, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const percent = new Intl.NumberFormat(document.documentElement.lang, { style: 'percent', maximumFractionDigits: 0 });

  const state = {
    survey: surveys.has(params.get('survey')) ? params.get('survey') : config.surveys[0].key,
    hidden: new Set(),  // parties the reader took off the chart; they stay off when the survey changes
    hover: null,  // the party under the pointer
    pinned: null,  // the party whose tooltip a press pinned
    markers: [],  // where each shown party is drawn now
    slide: null,  // { from, start } while parties slide to another survey's places
  };
  let logos = new Map();
  let geometry = null;
  let started = false;

  const picker = createPicker(root.querySelector('[data-picker]'), {
    imageClass: 'picker__logo',
    emptyLabel: gettext('Choose parties'),
    allLabel: gettext('All parties'),
    noMatch: gettext('No party matches.'),
    onToggle(key) {
      if (state.hidden.has(key)) state.hidden.delete(key);
      else state.hidden.add(key);
      picker.setSelected(shownItems().map((item) => item.key));
      redraw();
    },
  });

  // ---------- Data ----------
  const positions = (survey = state.survey) => config.positions[survey];
  const shownItems = () => positions().filter((p) => !state.hidden.has(p.party)).map((p) => ({ ...p, key: p.party }));
  const positionOf = (key) => positions().find((p) => p.party === key);
  const widthOf = (size) => (key) => tileWidth(darkLogo(config.parties[key], logos), size);

  // ---------- Drawing ----------
  // The canvas fills the well at the screen's pixel density; the plot is as large as fits (lib/compass.js).
  function measure() {
    const width = well.clientWidth;
    const height = well.clientHeight;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    const plot = compassPlot(width, height, PAD);
    geometry = { width, height, ratio, plot, size: tileSize(plot) };
  }

  const target = () => placeMarkers(shownItems(), geometry.plot, geometry.size, widthOf(geometry.size));

  function paint(markers, shown = () => 1) {
    const ctx = canvas.getContext('2d');
    ctx.setTransform(geometry.ratio, 0, 0, geometry.ratio, 0, 0);
    ctx.clearRect(0, 0, geometry.width, geometry.height);
    paintCompass(ctx, geometry.plot, {
      markers, parties: config.parties, logos, size: geometry.size, shown, highlight: state.pinned || state.hover,
    });
  }

  function redraw() {
    if (!geometry) return;
    state.slide = null;
    state.markers = target();
    paint(state.markers);
  }

  // From one survey's places to another's: parties in both slide, those in only one fade out or in.
  function slideTo(previous) {
    const to = target();
    if (REDUCED_MOTION || !previous.length) {
      redraw();
      return;
    }
    state.slide = { from: new Map(previous.map((m) => [m.key, m])), start: performance.now() };
    const toKeys = new Set(to.map((m) => m.key));
    const step = (now) => {
      if (!state.slide) return;
      const t = Math.min(1, (now - state.slide.start) / SLIDE);
      const eased = t < 0.5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2;
      const mix = (a, b) => a + (b - a) * eased;
      const leaving = [...state.slide.from.values()].filter((m) => !toKeys.has(m.key));
      const moving = to.map((m) => {
        const was = state.slide.from.get(m.key);
        return was ? { ...m, px: mix(was.px, m.px), py: mix(was.py, m.py), x: mix(was.x, m.x), y: mix(was.y, m.y) } : m;
      });
      state.markers = [...leaving, ...moving];
      paint(state.markers, (key) => (state.slide.from.has(key) ? (toKeys.has(key) ? 1 : 1 - eased) : eased));
      if (t < 1) requestAnimationFrame(step);
      else redraw();
    };
    requestAnimationFrame(step);
  }

  // ---------- The tooltip ----------
  function tipHtml(key) {
    const party = config.parties[key];
    const position = positionOf(key);
    const scale = (value, low, high) => `<span class="compass-tip__scale" aria-hidden="true"><i style="left: ${value * 10}%"></i></span>`
      + `<span class="compass-tip__ends" aria-hidden="true"><span>${escapeHtml(low)}</span><span>${escapeHtml(high)}</span></span>`;
    const notes = [position.then, party.ended].filter(Boolean).map((note) => `<p class="compass-tip__note">${escapeHtml(note)}</p>`).join('');
    const inferred = position.inferred ? `<p class="compass-tip__inferred">${escapeHtml(position.note)}</p>` : '';
    const placed = position.inferred ? ''
      : `${escapeHtml(interpolate(ngettext('Placed by at least %s expert', 'Placed by at least %s experts', position.experts), [position.experts]))} · `;
    const chip = party.logo ? `<span class="party-chip compass-tip__logo"><img class="party-logo" src="${escapeHtml(party.logo)}" alt=""></span>`
      : `<span class="party-chip compass-tip__logo"><span class="party-badge" style="--party:${party.color}">${escapeHtml(badgeText(party.abbreviation))}</span></span>`;
    return `<div class="compass-tip__head">${chip}`
      + `<div><strong>${escapeHtml(party.abbreviation)}</strong><span>${escapeHtml(party.name)}</span></div></div>${inferred}${notes}`
      + '<dl class="compass-tip__axes">'
      + `<div><dt>${escapeHtml(gettext('Economy'))}</dt><dd><strong>${number.format(position.economic)}</strong>${scale(position.economic, gettext('Left'), gettext('Right'))}</dd></div>`
      + `<div><dt>${escapeHtml(gettext('Social values'))}</dt><dd><strong>${number.format(position.social)}</strong>${scale(position.social, gettext('Progressive'), gettext('Conservative'))}</dd></div>`
      + '</dl>'
      + `<p class="compass-tip__views"><strong>${escapeHtml(party.position)}</strong> · ${escapeHtml(party.ideologies.join(', '))}</p>`
      + `<p class="compass-tip__meta">${placed}<a href="${escapeHtml(party.viewsSource)}" rel="noopener">${escapeHtml(gettext('Views: Wikipedia'))}</a></p>`;
  }

  // The tooltip goes beside the logo, or under or over it, wherever it fits without covering it.
  // Where nothing fits, as on a phone, it docks under the chart instead, so it never hides the chart.
  function showTip(key) {
    const marker = state.markers.find((m) => m.key === key);
    if (!key || !marker) {
      tip.hidden = true;
      return;
    }
    tip.innerHTML = tipHtml(key);
    tip.hidden = false;
    tip.classList.toggle('is-pinned', state.pinned === key);
    tip.classList.remove('is-docked');
    const { width, height } = tip.getBoundingClientRect();
    const gap = 12;
    const tile = { left: marker.x - marker.w / 2, right: marker.x + marker.w / 2, top: marker.y - geometry.size / 2, bottom: marker.y + geometry.size / 2 };
    const middle = { x: marker.x - width / 2, y: marker.y - height / 2 };
    const spots = [
      [tile.right + gap, middle.y], [tile.left - gap - width, middle.y],
      [middle.x, tile.bottom + gap], [middle.x, tile.top - gap - height],
    ];
    const inside = ([left, top]) => left >= 8 && top >= 8 && left + width <= geometry.width - 8 && top + height <= geometry.height - 8;
    const clampSpot = ([left, top]) => [Math.min(Math.max(8, left), geometry.width - width - 8), Math.min(Math.max(8, top), geometry.height - height - 8)];
    const covers = ([left, top]) => left < tile.right && left + width > tile.left && top < tile.bottom && top + height > tile.top;
    const spot = spots.find(inside) || spots.map(clampSpot).find((s) => !covers(s));
    if (!spot) {
      tip.classList.add('is-docked');
      tip.style.transform = '';
      tip.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      return;
    }
    tip.style.transform = `translate(${Math.round(spot[0])}px, ${Math.round(spot[1])}px)`;
  }

  function pointerAt(event) {
    const rect = canvas.getBoundingClientRect();
    return markerAt(state.markers, event.clientX - rect.left, event.clientY - rect.top, geometry.size)?.key || null;
  }

  canvas.addEventListener('pointermove', (event) => {
    if (state.pinned || state.slide || !geometry) return;
    const key = pointerAt(event);
    canvas.style.cursor = key ? 'pointer' : '';
    if (key === state.hover) return;
    state.hover = key;
    paint(state.markers);
    showTip(key);
  });
  canvas.addEventListener('pointerleave', () => {
    if (state.pinned || !state.hover) return;
    state.hover = null;
    paint(state.markers);
    showTip(null);
  });
  canvas.addEventListener('click', (event) => {
    const key = pointerAt(event);
    state.pinned = key && key !== state.pinned ? key : null;
    state.hover = key;
    paint(state.markers);
    showTip(state.pinned);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || !state.pinned) return;
    state.pinned = null;
    paint(state.markers);
    showTip(null);
  });

  // ---------- Around the chart ----------
  function drawSurvey() {
    const survey = surveys.get(state.survey);
    surveyLabel.textContent = `· ${survey.name}, ${survey.years}`;
    const licence = survey.licence ? ` · ${escapeHtml(survey.licence)}` : '';
    source.innerHTML = `${escapeHtml(gettext('Source:'))} <a href="${escapeHtml(survey.url)}">${escapeHtml(survey.name)}</a> (${escapeHtml(survey.years)})${licence}`;
    method.textContent = survey.method;
    citation.innerHTML = `${escapeHtml(survey.citation)} <a class="text-link" href="${escapeHtml(survey.url)}">${escapeHtml(survey.url.replace(/^https?:\/\//, ''))}</a>`;
    picker.setOptions(positions().map((p) => ({ party: config.parties[p.party], key: p.party }))
      .map(({ party, key }) => ({ id: key, name: `${party.abbreviation} · ${party.name}`, label: party.abbreviation, image: party.logo }))
      .sort((a, b) => a.label.localeCompare(b.label)));
    picker.setSelected(shownItems().map((item) => item.key));
    drawInferred(survey);
    drawTable();
  }

  // Which parties this survey left out, and how their places were inferred, in a sentence or two under the chart.
  function drawInferred(survey) {
    const names = (how) => positions().filter((p) => p.inferred === how).map((p) => config.parties[p.party].abbreviation);
    const fromScale = names('scale');
    const fromMergers = names('merger');
    const fit = config.fits[state.survey];
    const parts = [];
    if (fromScale.length && fit) {
      parts.push(interpolate(gettext('%(parties)s are inferred from where 519 political scientists put them on one left-right scale in 2018 (Bolognesi, Ribeiro and Codato). For the parties %(survey)s did place, that scale explains %(economic)s of the differences on the economy and %(social)s on social values.'),
        { parties: fromScale.join(', '), survey: survey.name, economic: percent.format(fit.economic), social: percent.format(fit.social) }, true));
    }
    if (fromMergers.length) {
      parts.push(interpolate(gettext('%(parties)s are the average of the parties that merged into them.'), { parties: fromMergers.join(', ') }, true));
    }
    inferredNote.hidden = !parts.length;
    inferredNote.innerHTML = parts.length ? `<strong>${escapeHtml(gettext('Inferred, marked *:'))}</strong> ${escapeHtml(parts.join(' '))}` : '';
  }

  function drawTable() {
    const rows = [...positions()].sort((a, b) => a.economic - b.economic).map((p) => {
      const party = config.parties[p.party];
      const experts = p.inferred ? escapeHtml(gettext('inferred')) : p.experts;
      return `<tr><td>${escapeHtml(party.abbreviation)}</td><td>${escapeHtml(party.name)}</td><td>${number.format(p.economic)}</td>`
        + `<td>${number.format(p.social)}</td><td>${experts}</td></tr>`;
    });
    const heads = [gettext('Party'), gettext('Name'), gettext('Economy, 0 left to 10 right'),
      gettext('Social values, 0 progressive to 10 conservative'), gettext('Experts, at least')];
    table.innerHTML = `<thead><tr>${heads.map((head) => `<th scope="col">${escapeHtml(head)}</th>`).join('')}</tr></thead>`
      + `<tbody>${rows.join('')}</tbody>`;
  }

  surveySelect.addEventListener('change', () => {
    const previous = state.markers;
    state.survey = surveySelect.value;
    state.pinned = null;
    state.hover = null;
    showTip(null);
    const next = new URLSearchParams(window.location.search);
    if (state.survey === config.surveys[0].key) next.delete('survey');
    else next.set('survey', state.survey);
    history.replaceState(null, '', `${window.location.pathname}?${next}`);
    drawSurvey();
    slideTo(previous);
  });

  new ResizeObserver(() => {
    if (!started || !well.clientWidth) return;
    measure();
    redraw();
    showTip(state.pinned);
  }).observe(well);

  // ---------- Save as image ----------
  function imageText() {
    const survey = surveys.get(state.survey);
    return {
      title: page.title,
      subtitle: interpolate(gettext('As experts placed the parties · %(survey)s, %(years)s'), { survey: survey.name, years: survey.years }, true),
      sources: [`${gettext('Source:')} ${survey.citation}`, gettext('*: inferred places. Logos: Wikimedia Commons, in the public domain.')],
    };
  }

  bindSaveButton(card.querySelector('[data-save-image]'), async (shape) => {
    const { title, subtitle, sources } = imageText();
    const frame = await imageFrame({ title, subtitle, sources, flag: page.flag, size: shape });
    const { inner } = imageWell(frame.ctx, frame.top, frame.bottom - frame.top, { width: frame.width });
    const plot = compassPlot(inner.w, inner.h, { top: PAD.top * SCALE, right: PAD.right * SCALE, bottom: PAD.bottom * SCALE, left: PAD.left * SCALE });
    plot.x += inner.x;
    plot.y += inner.y;
    const size = Math.round(Math.min(plot.w, plot.h) * 0.07);
    paintCompass(frame.ctx, plot, { markers: placeMarkers(shownItems(), plot, size, widthOf(size)), parties: config.parties, logos, size, k: SCALE });
    await handOver([{ canvas: frame.canvas, filename: sizedName(imageName(page.country, 'party-positions', state.survey), shape) }], title);
  });

  // ---------- The video (lib/compass-reel.js) ----------
  async function createReel(format) {
    await loadLogos();
    const survey = surveys.get(state.survey);
    const { title, subtitle, sources } = imageText();
    const reel = await createCompassReel({
      format, title, subtitle, flag: page.flag, source: sources[0], logos, parties: config.parties, items: shownItems(), survey,
    });
    reel.filename = imageName(page.country, 'party-positions', state.survey, format === 'wide' && 'wide').replace(/\.png$/, '.mp4');
    return reel;
  }

  async function loadLogos() {
    if (logos.size) return;
    const files = Object.values(config.parties).flatMap((party) => [party.logo, party.logoOnDark]).filter(Boolean);
    logos = new Map(await Promise.all(files.map(async (src) => [src, await loadImage(src)])));
  }

  return {
    async show() {
      if (!started) {
        started = true;
        surveySelect.value = state.survey;
        drawSurvey();
      }
      measure();
      redraw();
      await loadLogos();
      redraw();
    },
    createReel,
  };
}
