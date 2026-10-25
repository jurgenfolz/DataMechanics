// The battles of World War II on a map of 1937–1945. Each country takes the colour of the side it fought on that day,
// and each battle is a dot at its place, in the winner's colour, a little larger for a larger battle.
// Hover a dot for the battle's card; press it to keep the card open, with its picture and its Wikipedia link.
// The wheel zooms around the pointer, two fingers pinch, a drag pans, and a double click or the reset button shows
// the whole view. Borders come from CShapes 2.0, which draws them as the law saw them: wartime occupations are not on it.
// gettext and interpolate are Django's, from the translation catalog base.html loads.
import { escapeHtml } from './format.js';
import { GROUND, INK, SIDE_COLORS, WELL, formatDay, formatRange, placeTip, sideOn, stateHead, toDay } from './ww2.js';

const RAD = Math.PI / 180;
// The views, as [west, east, south, north] in degrees. Longitudes run on past 180, so the Pacific stays in one piece.
export const VIEWS = { world: [-22, 207, -24, 70], europe: [-14, 60, 21, 71], asia: [70, 207, -24, 56] };
export const WINNER_COLORS = { allies: SIDE_COLORS.allies, axis: SIDE_COLORS.axis, none: '#b6b9bd' };

function mix(a, b, t) {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  return `#${pa.map((v, i) => Math.round(pb[i] + (v - pb[i]) * t).toString(16).padStart(2, '0')).join('')}`;
}

// Land takes its side's colour, quiet; the countries in the battle under the pointer brighten.
const FILL = { allies: mix(SIDE_COLORS.allies, WELL, 0.32), axis: mix(SIDE_COLORS.axis, WELL, 0.42), none: '#2a2c2f' };
const FILL_LIT = { allies: mix(SIDE_COLORS.allies, WELL, 0.75), axis: mix(SIDE_COLORS.axis, WELL, 0.75), none: '#45484c' };

// The reader's zoom over the fitted map: a factor and the pan, in pixels. 1 is the whole view.
const NO_ZOOM = { k: 1, x: 0, y: 0 };
const MAX_ZOOM = 10;

function mercatorY(lat) {
  const phi = Math.max(-80, Math.min(80, lat)) * RAD;
  return -Math.log(Math.tan(Math.PI / 4 + phi / 2));
}

/** A point in projected units. Places east of the date line (Hawaii, Midway) are carried past 180°. */
function project([lon, lat]) {
  return [(lon < -150 ? lon + 360 : lon) * RAD, mercatorY(lat)];
}

/** A ring in projected units. A ring that lies mostly east of the date line moves as one piece, so it never tears. */
function ringPath(path, ring) {
  const mean = ring.reduce((sum, [lon]) => sum + lon, 0) / ring.length;
  const shift = mean < -140 ? 360 : 0;
  ring.forEach(([lon, lat], i) => {
    const x = (lon + shift) * RAD;
    const y = mercatorY(lat);
    if (i) path.lineTo(x, y);
    else path.moveTo(x, y);
  });
  path.closePath();
}

function viewBox([west, east, south, north]) {
  return [west * RAD, east * RAD, mercatorY(north), mercatorY(south)];
}

/** The width of a view over its height, on the map's projection. */
export function viewAspect(name) {
  const [x0, x1, y0, y1] = viewBox(VIEWS[name]);
  return (x1 - x0) / (y1 - y0);
}

/** The transform that fits a projected box into w × h, centred, without stretching it, then zoomed by `zoom`. */
function fit(box, w, h, zoom = NO_ZOOM) {
  const [x0, x1, y0, y1] = box;
  const k = Math.min(w / (x1 - x0), h / (y1 - y0));
  const tx = (w - (x1 - x0) * k) / 2 - x0 * k;
  const ty = (h - (y1 - y0) * k) / 2 - y0 * k;
  return { k: k * zoom.k, tx: tx * zoom.k + zoom.x, ty: ty * zoom.k + zoom.y };
}

export function prepareBorders(geojson) {
  return geojson.features.map(({ properties: p, geometry }) => {
    const path = new Path2D();
    for (const polygon of geometry.coordinates) for (const ring of polygon) ringPath(path, ring);
    return { path, start: toDay(p.start), end: toDay(p.end), state: p.state, ruler: p.ruler, name: p.name };
  });
}

export function prepareBattles(battles) {
  const prepared = battles.map((battle) => ({
    ...battle,
    startDay: toDay(battle.start),
    endDay: toDay(battle.end),
    point: project(battle.at),
    low: (battle.axisCasualties[0] || 0) + (battle.alliesCasualties[0] || 0),
  }));
  const most = Math.max(...prepared.map((battle) => battle.low));
  for (const battle of prepared) battle.size = Math.sqrt(battle.low / most);
  // Big dots first, so the small ones stay on top and can be pointed at.
  return prepared.sort((a, b) => b.low - a.low);
}

/** A dot's radius on screen: a little larger for a larger battle, never a circle to compare areas by. */
function dotRadius(battle, ink) {
  return (4 + 4.5 * battle.size) * ink;
}

/**
 * Paints the map on ctx for an area w × h: land for `day`, and the battles of `region` begun by then.
 * `whole` shows every battle at once (the whole war); `lit` is the battle under the pointer or pressed.
 */
export function paintMap(ctx, w, h, { borders, battles, states, box, day, whole, lit, region = 'world', ink = 1, zoom = NO_ZOOM }) {
  const { k, tx, ty } = fit(box, w, h, zoom);
  const parties = lit ? new Set([...lit.axis, ...lit.allies]) : null;
  // Land outside the view would spill out of the area (in a saved image, over the title): clip to it.
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, w, h);
  ctx.clip();
  ctx.save();
  ctx.setTransform(ctx.getTransform().translate(tx, ty).scale(k, k));
  ctx.lineWidth = Math.max(0.7, 0.5 * Math.sqrt(zoom.k)) / k;
  ctx.strokeStyle = GROUND;
  for (const border of borders) {
    if (border.start > day || border.end < day) continue;
    const side = sideOn(states, border.state || border.ruler, whole ? null : day) || 'none';
    ctx.fillStyle = parties?.has(border.state) ? FILL_LIT[side] : FILL[side];
    ctx.fill(border.path);
    ctx.stroke(border.path);
  }
  ctx.restore();

  for (const battle of battles) {
    if (region !== 'world' && battle.region !== region) continue;
    if (!whole && battle.startDay > day) continue;
    const x = battle.point[0] * k + tx;
    const y = battle.point[1] * k + ty;
    if (x < -20 || x > w + 20 || y < -20 || y > h + 20) continue;
    const grown = whole ? 1 : 1 - (1 - Math.min((day - battle.startDay) / 10, 1)) ** 3;
    const r = dotRadius(battle, ink) * grown;
    const fought = whole || battle.endDay >= day;
    ctx.save();
    ctx.globalAlpha = lit && lit !== battle ? 0.45 : fought ? 1 : 0.6;
    ctx.beginPath();
    ctx.arc(x, y, r + 1.5 * ink, 0, 2 * Math.PI);
    ctx.fillStyle = WELL;
    ctx.fill();
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.fillStyle = WINNER_COLORS[battle.winner];
    ctx.fill();
    if (lit === battle || (!whole && fought)) {
      ctx.beginPath();
      ctx.arc(x, y, r + 2.5 * ink, 0, 2 * Math.PI);
      ctx.strokeStyle = lit === battle ? INK : 'rgba(242, 243, 244, 0.6)';
      ctx.lineWidth = 1.2 * ink;
      ctx.stroke();
    }
    ctx.restore();
  }
  ctx.restore();
  return { k, tx, ty };
}

function flags(codes, states) {
  return codes.map((code) => states[code])
    .filter(Boolean)
    .map((state) => `<img src="${escapeHtml(state.flag)}" alt="${escapeHtml(state.name)}" title="${escapeHtml(state.name)}">`)
    .join('');
}

/** A battle's card: its picture, name, dates and result, each side's flags and casualties, and its Wikipedia link. */
export function battleTip(battle, states, units, { link = false, large = false } = {}) {
  const dates = battle.startDay === battle.endDay ? formatDay(battle.startDay)
    : `${formatDay(battle.startDay)} – ${formatDay(battle.endDay)}`;
  const side = (key, codes, casualties) => `<div class="tip__side"><i style="background:${SIDE_COLORS[key]}"></i>`
    + `<span class="tip__flags">${flags(codes, states)}</span><strong>${escapeHtml(formatRange(casualties, units))}</strong></div>`;
  const picture = battle.image ? `<img class="tip__picture" src="${escapeHtml(battle.image)}" alt="" loading="lazy">`
    + (battle.imageCredit ? `<div class="tip__credit">${escapeHtml(battle.imageCredit)}</div>` : '') : '';
  return `<div class="tip tip--battle${large ? ' tip--large' : ''}">${picture}<div class="tip__title">${escapeHtml(battle.name)}</div>`
    + `<div class="tip__muted">${escapeHtml(dates)} · ${escapeHtml(battle.text.winner)}</div>`
    + side('allies', battle.allies, battle.alliesCasualties)
    + side('axis', battle.axis, battle.axisCasualties)
    + `<div class="tip__muted">${escapeHtml(gettext('Killed, wounded, missing and captured'))}</div>`
    + (link ? `<a class="tip__link" href="${escapeHtml(battle.wiki)}" lang="en">${escapeHtml(gettext('Read on Wikipedia'))} ↗</a>` : '')
    + '</div>';
}

export function createWarMap(canvas, { states, battles, units, onHover, onPress }) {
  const well = canvas.parentElement;
  const tip = well.querySelector('[data-war-tip]');
  const reset = well.querySelector('[data-war-reset]');
  const ctx = canvas.getContext('2d');
  let borders = [];
  let width = 0;
  let height = 0;
  let box = viewBox(VIEWS.world);
  let from = box;
  let to = box;
  let moveStart = 0;
  let day = 0;
  let whole = true;
  let region = 'world';
  let lit = null;
  let pinned = null;
  let frame = 0;
  let placed = null;
  // The zoom eases towards its target, so wheel steps and pinches feel like one movement.
  let zoom = { ...NO_ZOOM };
  let zoomTarget = { ...NO_ZOOM };

  function resize() {
    const dpr = window.devicePixelRatio || 1;
    width = canvas.clientWidth;
    height = canvas.clientHeight;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    draw();
  }

  function draw() {
    if (!frame) frame = requestAnimationFrame(paint);
  }

  // A change of view glides there in 450 ms (ease-out), so the eye keeps its place.
  function paint(now) {
    frame = 0;
    const t = moveStart ? Math.min((now - moveStart) / 450, 1) : 1;
    const u = 1 - (1 - t) ** 3;
    box = from.map((v, i) => v + (to[i] - v) * u);
    const ease = 0.35;
    const near = Math.abs(zoom.k - zoomTarget.k) < 0.002 && Math.abs(zoom.x - zoomTarget.x) < 0.3 && Math.abs(zoom.y - zoomTarget.y) < 0.3;
    zoom = near ? { ...zoomTarget } : {
      k: zoom.k + (zoomTarget.k - zoom.k) * ease, x: zoom.x + (zoomTarget.x - zoom.x) * ease, y: zoom.y + (zoomTarget.y - zoom.y) * ease,
    };
    const dpr = window.devicePixelRatio || 1;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    placed = paintMap(ctx, width, height, { borders, battles, states, box, day, whole, lit: pinned || lit, region, zoom });
    if (t < 1 || !near) draw();
    else moveStart = 0;
  }

  function shownBattles() {
    return battles.filter((battle) => (region === 'world' || battle.region === region) && (whole || battle.startDay <= day));
  }

  function battleAt(px, py) {
    if (!placed) return null;
    let found = null;
    for (const battle of shownBattles()) {
      const x = battle.point[0] * placed.k + placed.tx;
      const y = battle.point[1] * placed.k + placed.ty;
      const r = dotRadius(battle, 1) + 5;
      if ((px - x) ** 2 + (py - y) ** 2 <= r * r) found = battle;  // the last hit is the smallest, drawn on top
    }
    return found;
  }

  function borderAt(px, py) {
    if (!placed) return null;
    const dpr = window.devicePixelRatio || 1;
    ctx.save();
    ctx.setTransform(dpr * placed.k, 0, 0, dpr * placed.k, dpr * placed.tx, dpr * placed.ty);
    const found = borders.find((border) => border.start <= day && day <= border.end
      && ctx.isPointInPath(border.path, px * dpr, py * dpr));
    ctx.restore();
    return found;
  }

  function borderTip(border) {
    const state = states[border.state];
    const side = sideOn(states, border.state || border.ruler, whole ? null : day);
    const label = side === 'allies' ? gettext('Allies') : side === 'axis' ? gettext('Axis') : gettext('Not at war');
    const head = state ? stateHead(state)
      : `${escapeHtml(border.name)}<span class="tip__ruler">${stateHead(states[border.ruler])}</span>`;
    return `<div class="tip"><div class="tip__head">${head}</div>`
      + `<div class="tip__muted">${escapeHtml(label)}${whole ? '' : ` · ${escapeHtml(formatDay(day))}`}</div></div>`;
  }

  // ---------- Zoom ----------
  function setZoom(k, x, y, { instant = false } = {}) {
    k = Math.min(Math.max(k, 1), MAX_ZOOM);
    zoomTarget = k === 1 ? { ...NO_ZOOM }
      : { k, x: Math.min(Math.max(x, width - width * k), 0), y: Math.min(Math.max(y, height - height * k), 0) };
    if (instant) zoom = { ...zoomTarget };
    well.classList.toggle('is-zoomed', k > 1);
    draw();
  }
  function zoomAround(px, py, factor) {
    const k = Math.min(Math.max(zoomTarget.k * factor, 1), MAX_ZOOM) / zoomTarget.k;
    setZoom(zoomTarget.k * k, px - (px - zoomTarget.x) * k, py - (py - zoomTarget.y) * k);
  }
  canvas.addEventListener('wheel', (event) => {
    event.preventDefault();
    const box2 = canvas.getBoundingClientRect();
    zoomAround(event.clientX - box2.left, event.clientY - box2.top, Math.exp(-event.deltaY * (event.deltaMode ? 0.05 : 0.0022)));
    hideTip();
  }, { passive: false });
  reset?.addEventListener('click', () => setZoom(1, 0, 0));
  canvas.addEventListener('dblclick', () => setZoom(1, 0, 0));

  // Dragging pans; two fingers pinch. A press that does not move is a click.
  const pointers = new Map();
  let drag = null;
  let pinch = null;
  let moved = false;
  canvas.addEventListener('pointerdown', (event) => {
    if (event.button) return;
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    canvas.setPointerCapture(event.pointerId);
    moved = false;
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      pinch = { distance: Math.hypot(a.x - b.x, a.y - b.y), k: zoomTarget.k };
      drag = null;
    } else if (zoomTarget.k > 1) {
      drag = { x: event.clientX - zoomTarget.x, y: event.clientY - zoomTarget.y };
    }
  });
  const endPointer = (event) => {
    pointers.delete(event.pointerId);
    if (pointers.size < 2) pinch = null;
    if (!pointers.size) drag = null;
  };
  canvas.addEventListener('pointerup', endPointer);
  canvas.addEventListener('pointercancel', endPointer);

  function hideTip() {
    if (pinned) return;
    tip.hidden = true;
  }

  canvas.addEventListener('pointermove', (event) => {
    const box2 = canvas.getBoundingClientRect();
    const px = event.clientX - box2.left;
    const py = event.clientY - box2.top;
    if (pointers.has(event.pointerId)) {
      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      moved = true;
    }
    if (pinch && pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      const mid = { x: (a.x + b.x) / 2 - box2.left, y: (a.y + b.y) / 2 - box2.top };
      const k = Math.min(Math.max(pinch.k * (Math.hypot(a.x - b.x, a.y - b.y) / pinch.distance), 1), MAX_ZOOM);
      setZoom(k, mid.x - (mid.x - zoomTarget.x) * (k / zoomTarget.k), mid.y - (mid.y - zoomTarget.y) * (k / zoomTarget.k), { instant: true });
      hideTip();
      return;
    }
    if (drag) {
      setZoom(zoomTarget.k, event.clientX - drag.x, event.clientY - drag.y, { instant: true });
      hideTip();
      return;
    }
    const battle = battleAt(px, py);
    canvas.classList.toggle('is-over-battle', Boolean(battle));
    if (battle !== lit) {
      lit = battle;
      onHover?.(battle);
      draw();
    }
    if (pinned) return;
    if (battle) {
      placeTip(tip, battleTip(battle, states, units), px, py);
      return;
    }
    const border = borderAt(px, py);
    if (border) placeTip(tip, borderTip(border), px, py);
    else tip.hidden = true;
  });
  canvas.addEventListener('pointerleave', () => {
    hideTip();
    canvas.classList.remove('is-over-battle');
    if (lit) {
      lit = null;
      onHover?.(null);
      draw();
    }
  });

  // A click on a dot keeps its card open, with the picture and the link; a click elsewhere lets it go.
  canvas.addEventListener('click', (event) => {
    if (moved) return;
    const box2 = canvas.getBoundingClientRect();
    const battle = battleAt(event.clientX - box2.left, event.clientY - box2.top);
    pin(battle, event.clientX - box2.left, event.clientY - box2.top);
    onPress?.(battle);
  });
  function pin(battle, px, py) {
    pinned = battle;
    tip.classList.toggle('is-pinned', Boolean(battle));
    if (battle) placeTip(tip, battleTip(battle, states, units, { link: true }), px, py);
    else tip.hidden = true;
    draw();
  }
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && pinned) pin(null);
  });

  new ResizeObserver(resize).observe(canvas);

  return {
    setBorders(geojson) {
      borders = prepareBorders(geojson);
      draw();
    },
    setDay(next, showWhole) {
      day = next;
      whole = showWhole;
      draw();
    },
    setView(name) {
      from = box;
      to = viewBox(VIEWS[name]);
      region = name;
      moveStart = performance.now();
      if (pinned && region !== 'world' && pinned.region !== region) pin(null);
      setZoom(1, 0, 0);
    },
    light(battle) {
      lit = battle;
      draw();
    },
    /** Shows a battle's card over its dot, as a press on the dot would. */
    show(battle) {
      if (!placed || !battle) return pin(null);
      pin(battle, battle.point[0] * placed.k + placed.tx, battle.point[1] * placed.k + placed.ty);
    },
    /** Paints the map as it is now into an area of a saved image. */
    paintInto(target, w, h, ink) {
      paintMap(target, w, h, { borders, battles, states, box: to, day, whole, lit: null, region, ink });
    },
  };
}
