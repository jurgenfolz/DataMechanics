// The war one entry at a time, as the Politics timeline lists presidents, in two tabs: the battles in the order they
// began (dates, a dot in the winner's colour, the battle's picture, its name with the flags of both sides, each side's
// casualties and a pie of the two), and the other events of the war (pacts, invasions, surrenders).
// Pressing a battle shows it on the map; every entry links to its Wikipedia article. The region tabs filter both.
// gettext and interpolate are Django's, from the translation catalog base.html loads.
import { escapeHtml } from './format.js';
import { SIDE_COLORS, formatDay, formatRange, placeTip, toDay } from './ww2.js';
import { WINNER_COLORS, battleTip } from './war-map.js';

const FLAGS_SHOWN = 3;
const KIND_COLORS = { war: '#b6b9bd', diplomacy: '#9085e9', crime: '#e66767', bombing: '#c98500' };

function flags(codes, states) {
  const shown = codes.slice(0, FLAGS_SHOWN);
  const more = codes.length - shown.length;
  return shown.map((code) => {
    const state = states[code];
    return state ? `<img class="flag" src="${escapeHtml(state.flag)}" alt="${escapeHtml(state.name)}" title="${escapeHtml(state.name)}" loading="lazy">` : '';
  }).join('') + (more > 0 ? `<i class="battle-row__more">+${more}</i>` : '');
}

const wikiLink = (url) => `<a class="battle-row__link" href="${escapeHtml(url)}" lang="en" title="${escapeHtml(gettext('Read on Wikipedia'))}">W<span class="visually-hidden">${escapeHtml(gettext('Read on Wikipedia'))}</span></a>`;

export function createBattleList(root, { battles, events, states, units, onPick }) {
  const list = root.querySelector('[data-battle-rows]');
  const eventList = root.querySelector('[data-event-rows]');
  const tabs = [...root.querySelectorAll('[data-list-tab]')];
  const heads = root.querySelectorAll('[data-list-head]');
  const tip = root.querySelector('[data-list-tip]');
  const ordered = [...battles].sort((a, b) => a.startDay - b.startDay || a.name.localeCompare(b.name));
  let region = 'world';
  let tab = 'battles';
  let pressed = null;

  const rows = new Map();
  for (const battle of ordered) {
    const item = document.createElement('li');
    item.className = 'term-row term-row--battle';
    item.style.setProperty('--party', WINNER_COLORS[battle.winner]);
    item.dataset.region = battle.region;
    // The start and the end on a line each, so a long month ("set. de 1939") fits the column.
    const dates = battle.startDay === battle.endDay ? escapeHtml(formatDay(battle.startDay))
      : `<span>${escapeHtml(formatDay(battle.startDay, 'month'))} –</span> <span>${escapeHtml(formatDay(battle.endDay, 'month'))}</span>`;
    // The pie: each side's share of the lowest estimates; a battle without a figure for a side shows the other's whole.
    const share = battle.low ? (100 * (battle.alliesCasualties[0] || 0)) / battle.low : 50;
    const picture = battle.image ? `<img class="battle-row__picture" src="${escapeHtml(battle.image)}" alt="" loading="lazy">` : '<span class="battle-row__picture battle-row__picture--none"></span>';
    item.innerHTML = `<span class="term-row__years">${dates}</span><span class="term-row__rail"></span>${picture}`
      + `<span class="term-row__who"><button type="button" class="battle-row__name" aria-pressed="false">${escapeHtml(battle.name)}</button>`
      + `<span class="battle-row__sides"><span>${flags(battle.allies, states)}</span><span>${flags(battle.axis, states)}</span><span class="battle-row__theatre">${escapeHtml(battle.text.theatre)}</span></span></span>`
      + `<span class="battle-row__values"><span><i style="background:${SIDE_COLORS.allies}"></i>${escapeHtml(formatRange(battle.alliesCasualties, units))}</span>`
      + `<span><i style="background:${SIDE_COLORS.axis}"></i>${escapeHtml(formatRange(battle.axisCasualties, units))}</span></span>`
      + `<span class="battle-row__pie" style="background: conic-gradient(${SIDE_COLORS.allies} 0 ${share.toFixed(1)}%, ${SIDE_COLORS.axis} ${share.toFixed(1)}% 100%)" aria-hidden="true"></span>`
      + `<span class="battle-row__result">${escapeHtml(battle.text.winner)}</span>${wikiLink(battle.wiki)}`;
    // Hovering the picture opens the battle's card, as on the map, with the picture at a larger size.
    const tile = item.querySelector('.battle-row__picture');
    tile.addEventListener('pointermove', (event) => {
      const layer = tip.parentElement.getBoundingClientRect();
      placeTip(tip, battleTip(battle, states, units, { large: true }), event.clientX - layer.left, event.clientY - layer.top);
    });
    tile.addEventListener('pointerleave', () => { tip.hidden = true; });
    item.querySelector('.battle-row__name').addEventListener('click', () => {
      pressed = pressed === battle ? null : battle;
      for (const [other, row] of rows) row.querySelector('.battle-row__name').setAttribute('aria-pressed', String(other === pressed));
      onPick(pressed);
    });
    rows.set(battle, item);
  }
  list.replaceChildren(...rows.values());

  eventList.replaceChildren(...events.map((event) => {
    const item = document.createElement('li');
    item.className = 'term-row term-row--event';
    item.style.setProperty('--party', KIND_COLORS[event.kind]);
    item.dataset.region = event.region;
    item.innerHTML = `<span class="term-row__years">${escapeHtml(formatDay(toDay(event.date)))}</span><span class="term-row__rail"></span>`
      + `<span class="term-row__who"><strong>${escapeHtml(event.name)}</strong><span>${escapeHtml(event.text.kind)}</span></span>`
      + wikiLink(event.wiki);
    return item;
  }));

  function apply() {
    for (const row of [...list.children, ...eventList.children]) {
      row.hidden = region !== 'world' && row.dataset.region !== region && row.dataset.region !== 'world';
    }
    list.hidden = tab !== 'battles';
    eventList.hidden = tab !== 'events';
    heads.forEach((head) => { head.hidden = tab !== 'battles'; });
    for (const button of tabs) button.setAttribute('aria-pressed', String(button.dataset.listTab === tab));
  }
  for (const button of tabs) button.addEventListener('click', () => { tab = button.dataset.listTab; apply(); });
  apply();

  return {
    setRegion(next) {
      region = next;
      apply();
    },
    light(battle) {
      for (const [other, row] of rows) row.classList.toggle('is-lit', other === battle);
    },
  };
}
