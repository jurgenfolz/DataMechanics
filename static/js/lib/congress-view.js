// The seats in Congress on a country's Politics page: each house as a half circle of dots, one a seat, beside a table.
// The house is picked with the pills above the card (?house=), the term with the select in its head (?term=next for
// the members just elected), and the view with the tabs under it: by party, or by bloc (?by=bloc: left, centre, right).
// Pointing at dots or at a row lights up that party, or that bloc, in both.
// gettext and interpolate are Django's, from the translation catalog base.html loads.
import {
  bindSaveButton, FONT, handOver, imageFrame, imageName, imageWell, loadImage, MONO, sizedName, wrap,
} from './chart-image.js';
import { badgeText, escapeHtml } from './format.js';
import { hemicycleLayout, paintHemicycle, partyAt } from './hemicycle.js';
import { darkLogo, paintTile } from './compass.js';
import { createCongressReel } from './congress-reel.js';

/**
 * Wires the seats inside `root` (templates/politics/_congress.html) to `config` (politics/congress.py, data).
 * `page` gives the country's name, flag and the title for images.
 * Returns { show(house), createReel(format) }: show draws a house once its tab is open, since a hidden canvas has no size,
 * and createReel builds the open house's video (lib/congress-reel.js).
 */
export function createCongressView(root, config, page) {
  const card = root.querySelector('[data-congress-card]');
  const well = root.querySelector('[data-congress-well]');
  const canvas = root.querySelector('[data-hemicycle]');
  const list = root.querySelector('[data-seat-list]');
  const title = root.querySelector('[data-house-name]');
  const source = root.querySelector('[data-congress-source]');
  const termSelect = root.querySelector('[data-term]');
  const byTabs = [...root.querySelectorAll('[data-by]')];
  const notes = [...root.querySelectorAll('[data-note]')];
  const houses = new Map(config.houses.map((house) => [house.key, house]));
  const blocs = new Map(config.blocs.map((bloc) => [bloc.key, bloc]));
  const share = new Intl.NumberFormat(document.documentElement.lang, { style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const score = new Intl.NumberFormat(document.documentElement.lang, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const params = new URLSearchParams(window.location.search);
  const state = {
    house: config.houses[0].key,
    term: params.get('term') === 'next' && config.starts ? 'next' : 'now',
    by: params.get('by') === 'bloc' ? 'bloc' : 'party',
    lit: null,  // { party: index } or { bloc: key }: what the pointer lights up
  };
  let geometry = null;

  const house = () => houses.get(state.house);
  const term = () => house().terms.find((t) => t.key === state.term) || house().terms[0];
  const colorOf = (party) => (state.by === 'bloc' ? blocs.get(party.bloc).color : party.color);
  const blocSeats = (key) => term().parties.filter((p) => p.bloc === key).reduce((sum, p) => sum + p.seats, 0);

  // The party indices to keep bright, and the caption in the middle of the half circle.
  function lit() {
    if (!state.lit) return null;
    const parties = term().parties;
    return new Set(parties.map((_, i) => i).filter((i) => ('party' in state.lit ? i === state.lit.party : parties[i].bloc === state.lit.bloc)));
  }
  function caption() {
    if (!state.lit) return { value: term().members, text: gettext('seats') };
    if ('party' in state.lit) {
      const party = term().parties[state.lit.party];
      return { value: party.seats, text: party.abbreviation };
    }
    return { value: blocSeats(state.lit.bloc), text: blocs.get(state.lit.bloc).name };
  }

  function measure() {
    const width = well.clientWidth;
    const height = well.clientHeight;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    geometry = { width, height, ratio, layout: hemicycleLayout(term().members, { x: 12, y: 12, w: width - 24, h: height - 24 }) };
  }

  function paint() {
    const ctx = canvas.getContext('2d');
    ctx.setTransform(geometry.ratio, 0, 0, geometry.ratio, 0, 0);
    ctx.clearRect(0, 0, geometry.width, geometry.height);
    paintHemicycle(ctx, geometry.layout, term().parties, { colorOf, lit: lit(), caption: caption() });
  }

  function light(next) {
    if (JSON.stringify(next) === JSON.stringify(state.lit)) return;
    state.lit = next;
    paint();
    // A party lights its own row; a bloc lights its heading row.
    for (const row of list.children) {
      const on = Boolean(next) && ('party' in next ? row.dataset.index === String(next.party) : row.dataset.bloc === next.bloc);
      row.classList.toggle('is-lit', on);
    }
  }

  // ---------- The table: the parties, the largest first; by bloc, each bloc and then its parties ----------
  function chip(party) {
    return party.logo ? `<span class="party-chip"><img class="party-logo" src="${escapeHtml(party.logo)}" alt=""></span>`
      // A party without a profile (no party, or an independent) is named beside its chip, so the chip stays blank.
      : `<span class="party-chip"><span class="party-badge party-badge--small" style="--party:${party.color}">${party.key ? escapeHtml(badgeText(party.abbreviation)) : ''}</span></span>`;
  }

  function partyRow(party, index, detail) {
    const line = detail ? `<span title="${escapeHtml(detail)}">${escapeHtml(detail)}</span>` : '';
    return `<li class="seat-row" data-index="${index}" style="--party:${colorOf(party)}">`
      + `<i class="seat-row__swatch" aria-hidden="true"></i>${chip(party)}`
      + `<span class="seat-row__name"><strong>${escapeHtml(party.abbreviation)}</strong>${line}</span>`
      + `<span class="seat-row__seats">${party.seats}</span><span class="seat-row__share">${share.format(party.seats / term().members)}</span></li>`;
  }

  // Where the survey puts a party, for its row in the bloc view: "centre-left · 3.6".
  function placeOf(party) {
    if (party.score === null) return '';
    const text = `${party.band} · ${score.format(party.score)}`;
    return party.inferredFrom ? interpolate(gettext('%(place)s, from %(parties)s'), { place: text, parties: party.inferredFrom }, true) : text;
  }

  function drawList() {
    const { parties, members } = term();
    const rows = parties.map((party, index) => ({ party, index })).sort((a, b) => b.party.seats - a.party.seats);
    if (state.by === 'party') {
      list.setAttribute('aria-label', gettext('Seats by party'));
      list.innerHTML = rows.map(({ party, index }) => partyRow(party, index, party.name !== party.abbreviation ? party.name : '')).join('');
      return;
    }
    list.setAttribute('aria-label', gettext('Seats by bloc'));
    // The three blocs always show, so an empty one says so; parties without a place only when they hold seats.
    list.innerHTML = config.blocs.filter((bloc) => bloc.key !== 'none' || blocSeats('none')).map((bloc) => {
      const seats = blocSeats(bloc.key);
      const head = `<li class="seat-row seat-bloc" data-bloc="${bloc.key}" style="--party:${bloc.color}">`
        + '<i class="seat-row__swatch" aria-hidden="true"></i>'
        + `<span class="seat-row__name"><strong>${escapeHtml(bloc.name)}</strong><span>${escapeHtml(bloc.bands)}</span></span>`
        + `<span class="seat-row__seats">${seats}</span><span class="seat-row__share">${share.format(seats / members)}</span></li>`;
      return head + rows.filter(({ party }) => party.bloc === bloc.key).map(({ party, index }) => partyRow(party, index, placeOf(party))).join('');
    }).join('');
  }

  function drawHead() {
    const { name, seats } = house();
    const { members, sources, period } = term();
    title.textContent = period ? `· ${name}, ${period.years}` : `· ${name}`;
    const from = sources.map((s) => `<a href="${escapeHtml(s.url)}">${escapeHtml(s.name)}</a> · ${escapeHtml(s.note)}`);
    if (state.by === 'bloc') {
      from.push(`<a href="${escapeHtml(config.spectrum.url)}">${escapeHtml(config.spectrum.label)}</a> · `
        + escapeHtml(interpolate(gettext('left and right as %(experts)s political scientists placed the parties in %(year)s'), config.spectrum, true)));
    }
    const vacant = members < seats ? ` · ${escapeHtml(interpolate(gettext('%(members)s of %(seats)s seats filled'), { members, seats }, true))}` : '';
    source.innerHTML = `${escapeHtml(from.length > 1 ? gettext('Sources:') : gettext('Source:'))} ${from.join('; ')}${vacant}`;
    canvas.setAttribute('aria-label', interpolate(gettext('The %(house)s as a half circle of %(seats)s dots, one for each seat, coloured by party. The table beside it lists the seats.'),
      { house: name, seats: members }, true));
    if (termSelect) termSelect.value = state.term;
    for (const tab of byTabs) tab.setAttribute('aria-pressed', String(tab.dataset.by === state.by));
    for (const note of notes) note.hidden = note.dataset.note !== state.term && note.dataset.note !== state.by;
  }

  function draw() {
    state.lit = null;
    drawHead();
    drawList();
    measure();
    paint();
  }

  // The term and the view live in the address; the page keeps them when it rewrites it (politics-page.js, syncUrl).
  function syncUrl() {
    const next = new URLSearchParams(window.location.search);
    if (state.term === 'now') next.delete('term');
    else next.set('term', state.term);
    if (state.by === 'party') next.delete('by');
    else next.set('by', state.by);
    history.replaceState(null, '', `${window.location.pathname}?${next}`);
  }

  termSelect?.addEventListener('change', () => {
    state.term = termSelect.value;
    draw();
    syncUrl();
  });
  for (const tab of byTabs) {
    tab.addEventListener('click', () => {
      state.by = tab.dataset.by;
      draw();
      syncUrl();
    });
  }

  // What a point of the half circle or a row of the table stands for: a party, or by bloc its bloc; null for none.
  function seatTarget(event) {
    if (!geometry) return null;
    const rect = canvas.getBoundingClientRect();
    const index = partyAt(geometry.layout, term().parties, event.clientX - rect.left, event.clientY - rect.top);
    if (index === null) return null;
    return state.by === 'bloc' ? { bloc: term().parties[index].bloc } : { party: index };
  }
  function rowTarget(event) {
    const row = event.target.closest('[data-index], [data-bloc]');
    if (!row) return null;
    return row.dataset.bloc ? { bloc: row.dataset.bloc } : { party: Number(row.dataset.index) };
  }

  // A mouse lights what it points at, and the light goes when it leaves.
  // A finger lights what it taps and keeps it lit until the next tap: lifting a finger ends its pointer at once,
  // so the leave that follows every tap must not clear it. A second tap on the same thing, or beside the seats, clears it.
  let finger = false;
  root.addEventListener('pointerdown', (event) => { finger = event.pointerType !== 'mouse'; });
  const mouse = (handler) => (event) => { if (event.pointerType === 'mouse') handler(event); };
  canvas.addEventListener('pointermove', mouse((event) => light(seatTarget(event))));
  canvas.addEventListener('pointerleave', mouse(() => light(null)));
  list.addEventListener('pointerover', mouse((event) => { if (rowTarget(event)) light(rowTarget(event)); }));
  list.addEventListener('pointerleave', mouse(() => light(null)));
  for (const [element, target] of [[canvas, seatTarget], [list, rowTarget]]) {
    element.addEventListener('click', (event) => {
      if (!finger) return;
      const next = target(event);
      light(next && JSON.stringify(next) === JSON.stringify(state.lit) ? null : next);
    });
  }

  new ResizeObserver(() => {
    if (!geometry || !well.clientWidth) return;
    measure();
    paint();
  }).observe(well);

  // ---------- Save as image: the half circle, then a legend of every party, or of every bloc and its parties ----------
  bindSaveButton(card.querySelector('[data-save-image]'), async (shape) => {
    const { name } = house();
    const { parties, members, sources } = term();
    const view = state.by === 'bloc' ? ` · ${gettext('Left, centre and right')}` : '';
    const frame = await imageFrame({
      title: page.title,
      subtitle: `${interpolate(gettext('%(house)s · %(seats)s seats, %(when)s'), { house: name, seats: members, when: sources[0].note }, true)}${view}`,
      sources: [
        `${sources.length > 1 ? gettext('Sources:') : gettext('Source:')} ${sources.map((s) => s.name).join('; ')}`,
        ...(state.by === 'bloc' ? [config.spectrum.citation] : []),
      ],
      flag: page.flag,
      size: shape,
    });
    const room = frame.bottom - frame.top;
    // Portrait: the half circle over its legend. Wide: the half circle on the left, its legend on the right.
    const wide = shape === 'wide';
    const { well: box, inner } = wide ? imageWell(frame.ctx, frame.top, room, { width: Math.round(frame.width * 0.56) })
      : imageWell(frame.ctx, frame.top, Math.round(room * 0.5), { width: frame.width });
    paintHemicycle(frame.ctx, hemicycleLayout(members, { x: inner.x + 24, y: inner.y + 16, w: inner.w - 48, h: inner.h - 32 }), parties,
      { colorOf, caption: { value: members, text: gettext('seats') }, k: 1.6 });
    const legend = wide ? { x: box.x + box.w + 40, y: box.y, w: frame.width - 56 - (box.x + box.w + 40), h: room }
      : { x: box.x, y: box.y + box.h + 28, w: box.w, h: frame.bottom - box.y - box.h - 28 };
    const logos = await loadLogos(parties);
    if (state.by === 'bloc') paintBlocLegend(frame.ctx, config.blocs, parties, logos, legend);
    else paintLegend(frame.ctx, [...parties].sort((a, b) => b.seats - a.seats), logos, legend);
    await handOver([{ canvas: frame.canvas, filename: sizedName(imageName(page.country, 'congress', state.house, state.term === 'next' && term().label, state.by === 'bloc' && 'blocs'), shape) }], page.title);
  });

  // ---------- The video: the open house in the open term, by bloc and then by party, closing on the tables ----------
  async function createReel(format) {
    const { name } = house();
    const current = term();
    const { members, period, sources } = current;
    // A term with a set last day gives both days; one that ends with the next election, only its first.
    const span = period && (period.to ? gettext('%(seats)s seats, from %(from)s to %(to)s') : gettext('%(seats)s seats, since %(from)s'));
    const seats = period ? interpolate(span, { seats: members, from: period.from, to: period.to }, true) : '';
    // Under the title: the seats and the term they are for; then who the numbers are, and who placed the parties.
    const who = sources.map((s) => s.note).join('; ');
    const reel = await createCongressReel({
      format,
      title: name,
      unit: period ? period.years : '',
      subtitle: seats || capitalised(who),  // a house without terms, like Austria's Bundesrat, leads with who sits
      explanation: [seats ? `${capitalised(who)}.` : '',
        interpolate(gettext('Left, centre and right as %(experts)s political scientists placed the parties in %(year)s.'), config.spectrum, true),
      ].filter(Boolean).join(' '),
      flag: page.flag,
      sources: [`${sources.length > 1 ? gettext('Sources:') : gettext('Source:')} ${sources.map((s) => s.name).join('; ')}`, config.spectrum.citation],
      term: current,
      blocs: config.blocs,
      logos: await loadLogos(current.parties),
    });
    reel.filename = imageName(page.country, 'congress', state.house, current.label, format === 'wide' && 'wide').replace(/\.png$/, '.mp4');
    return reel;
  }

  return {
    show(key) {
      if (houses.has(key)) state.house = key;
      draw();
    },
    createReel,
  };
}

const capitalised = (text) => `${text.charAt(0).toUpperCase()}${text.slice(1)}`;

async function loadLogos(parties) {
  const files = new Set(parties.flatMap((p) => [p.logo, p.logoOnDark]).filter(Boolean));
  return new Map(await Promise.all([...files].map(async (src) => [src, await loadImage(src)])));
}

// One legend row: a swatch in `color`, the logo, the abbreviation and the seats, in a column `width` wide.
// A party without a logo leaves its place empty, as its abbreviation follows anyway.
function paintLegendRow(ctx, party, color, logos, x, y, width, rowHeight) {
  const size = Math.min(40, rowHeight - 10);
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.roundRect(x, y - size / 2, 6, size, 3);
  ctx.fill();
  if (party.logo) paintTile(ctx, x + 18 + size * 0.8, y, size, party, darkLogo(party, logos), { width: size * 1.6, fill: '#17191b', k: 1.4 });
  ctx.textBaseline = 'middle';
  ctx.font = `700 24px ${MONO}`;
  const seatsWidth = ctx.measureText(String(party.seats)).width;
  ctx.textAlign = 'right';
  ctx.fillStyle = '#f2f3f4';
  ctx.fillText(String(party.seats), x + width - 24, y);
  ctx.textAlign = 'left';
  // A long name gets smaller type, so it keeps clear of the seats.
  const left = x + 30 + size * 1.6;
  const room = x + width - 24 - seatsWidth - 14 - left;
  let type = 24;
  ctx.font = `700 ${type}px ${FONT}`;
  while (type > 16 && ctx.measureText(party.abbreviation).width > room) {
    type -= 1;
    ctx.font = `700 ${type}px ${FONT}`;
  }
  ctx.fillText(wrap(ctx, party.abbreviation, room, 1)[0], left, y);
}

// The saved image's legend by party: every party, in as many columns as its rows take to fit the box's height.
function paintLegend(ctx, parties, logos, box) {
  const columns = Math.max(2, Math.ceil(parties.length / Math.max(1, Math.floor(box.h / 56))));
  const rowsPerColumn = Math.ceil(parties.length / columns);
  const rowHeight = Math.min(56, box.h / rowsPerColumn);
  const width = box.w / columns;
  parties.forEach((party, i) => {
    const y = box.y + (i % rowsPerColumn) * rowHeight + rowHeight / 2;
    paintLegendRow(ctx, party, party.color, logos, box.x + Math.floor(i / rowsPerColumn) * width, y, width, rowHeight);
  });
}

// The saved image's legend by bloc: a column per bloc, its name and seats over its parties, the largest first.
function paintBlocLegend(ctx, blocs, parties, logos, box) {
  const groups = blocs.map((bloc) => ({ bloc, parties: parties.filter((p) => p.bloc === bloc.key).sort((a, b) => b.seats - a.seats) }))
    .filter((group) => group.bloc.key !== 'none' || group.parties.length);
  // Parties without a place join the right-hand column, under the right, so three columns always do.
  const columns = groups.slice(0, 3).map((group) => [group]);
  if (groups[3]) columns[2].push(groups[3]);
  const lines = Math.max(...columns.map((column) => column.reduce((n, group) => n + group.parties.length + 1, 0)));
  const rowHeight = Math.min(52, box.h / lines);
  const width = box.w / columns.length;
  columns.forEach((column, c) => {
    const x = box.x + c * width;
    let y = box.y + rowHeight / 2;
    for (const { bloc, parties: members } of column) {
      const seats = members.reduce((sum, p) => sum + p.seats, 0);
      ctx.fillStyle = bloc.color;
      ctx.beginPath();
      ctx.roundRect(x, y - 14, 6, 28, 3);
      ctx.fill();
      ctx.textBaseline = 'middle';
      ctx.fillStyle = '#f2f3f4';
      ctx.font = `800 26px ${FONT}`;
      ctx.fillText(bloc.name, x + 18, y);
      ctx.textAlign = 'right';
      ctx.font = `700 26px ${MONO}`;
      ctx.fillText(String(seats), x + width - 24, y);
      ctx.textAlign = 'left';
      y += rowHeight;
      for (const party of members) {
        paintLegendRow(ctx, party, bloc.color, logos, x + 18, y, width - 18, rowHeight);
        y += rowHeight;
      }
    }
  });
}
