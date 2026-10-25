// The party compass, drawn on a canvas. The Politics page, its saved image and its video all draw it with this module.
// The economic axis runs left to right, 0 to 10; the social axis bottom to top, 0 progressive to 10 conservative.
// Each party is its logo, with no frame, on its point; a party whose place is inferred carries a small gold asterisk.
// Tiles that would overlap are pushed apart, and a thin line in the party's colour leads from a moved tile back to its point.
// gettext is Django's, from the translation catalog base.html loads.
import { containedRect, FONT, MONO } from './chart-image.js';

const GRID = '#2c2e30';
const CROSS = '#4a4d52';
const INK_2 = '#b6b9bd';
const INK_3 = '#8b8f94';
const WELL = '#1d1f21';
const GOLD = '#ffd700';
const TICKS = [0, 2.5, 5, 7.5, 10];
const MAX_ASPECT = 1.6;  // how much wider than tall the plot may grow, to use a wide screen

/**
 * The plot inside a box of `width` × `height`, leaving `pad` for the tick numbers, centred across.
 * It is as wide as the box allows, up to MAX_ASPECT times its height, and never taller than wide.
 * With `fill`, as in a video, it takes the whole box instead, its two axes stretched to fit: a tall frame gets a tall plot.
 */
export function compassPlot(width, height, pad = { top: 8, right: 8, bottom: 26, left: 30 }, { fill = false } = {}) {
  const room = { w: Math.max(0, width - pad.left - pad.right), h: Math.max(0, height - pad.top - pad.bottom) };
  if (fill) return { x: pad.left, y: pad.top, ...room };
  const w = Math.min(room.w, room.h * MAX_ASPECT);
  const h = Math.min(room.h, w);
  return { x: pad.left + (room.w - w) / 2, y: pad.top, w, h };
}

/** Where a party's economic and social scores land, in pixels. */
export function toPixel(plot, economic, social) {
  return [plot.x + (economic / 10) * plot.w, plot.y + (1 - social / 10) * plot.h];
}

/** The logo tile's height for a plot: large enough to read, small enough for a crowded centre. */
export function tileSize(plot) {
  return Math.round(Math.min(46, Math.max(26, Math.min(plot.w, plot.h) * 0.068)));
}

/** A tile's width: as wide as its logo's shape asks, from square up to twice its height, for wordmarks. */
export function tileWidth(logo, size) {
  const aspect = logo?.naturalWidth ? logo.naturalWidth / logo.naturalHeight : 1;
  return Math.round(size * Math.min(2, Math.max(1, aspect)));
}

/**
 * Places each party's tile: on its point, or pushed off it until no two tiles overlap.
 * `items` are { key, economic, social, inferred }; `widthOf(key)` is a tile's width, and every tile is `size` tall.
 * Returns { key, px, py, x, y, w, inferred }: the point, the tile's centre and width, and whether the place is inferred.
 * The same items always land in the same places, so a video's frames agree.
 */
export function placeMarkers(items, plot, size, widthOf = () => size, gap = 4) {
  const markers = items.map((item) => {
    const [px, py] = toPixel(plot, item.economic, item.social);
    return { key: item.key, px, py, x: px, y: py, w: widthOf(item.key), inferred: Boolean(item.inferred) };
  });
  for (let round = 0; round < 400; round += 1) {
    let moved = false;
    for (let i = 0; i < markers.length; i += 1) {
      for (let j = i + 1; j < markers.length; j += 1) {
        const [a, b] = [markers[i], markers[j]];
        let [dx, dy] = [b.x - a.x, b.y - a.y];
        const [overX, overY] = [(a.w + b.w) / 2 + gap - Math.abs(dx), size + gap - Math.abs(dy)];
        if (overX <= 0 || overY <= 0) continue;
        moved = true;
        // Apart along the line between the two, so a crowd spreads around itself rather than into a column.
        // Two tiles on one spot part along a fixed slant, the first to the left.
        if (Math.hypot(dx, dy) < 0.5) [dx, dy] = [1, 0.6];
        const length = Math.hypot(dx, dy);
        const push = (Math.min(overX, overY) / 2 + 0.25) * 0.5;
        a.x -= (dx / length) * push;
        a.y -= (dy / length) * push;
        b.x += (dx / length) * push;
        b.y += (dy / length) * push;
      }
    }
    for (const marker of markers) {
      // A pull back towards its own point keeps each tile as close to it as the others allow.
      marker.x += (marker.px - marker.x) * 0.04;
      marker.y += (marker.py - marker.y) * 0.04;
      marker.x = Math.min(Math.max(marker.x, plot.x + marker.w / 2), plot.x + plot.w - marker.w / 2);
      marker.y = Math.min(Math.max(marker.y, plot.y + size / 2), plot.y + plot.h - size / 2);
    }
    if (!moved) break;
  }
  return markers;
}

/** The marker whose tile holds the point (x, y), the one drawn last when tiles touch; null for none. */
export function markerAt(markers, x, y, size) {
  for (let i = markers.length - 1; i >= 0; i -= 1) {
    const m = markers[i];
    if (Math.abs(x - m.x) <= m.w / 2 && Math.abs(y - m.y) <= size / 2) return m;
  }
  return null;
}

/**
 * Paints the compass: grid, axes and their names, then the markers.
 * `parties` maps a key to { color, logo, logoOnDark, abbreviation }; `logos` maps a logo's address to its loaded image.
 * `shown(key)` gives how far a marker has appeared, from 0 to 1 (1 by default).
 * `highlight` is the key of a marker to lift above the others, which then fade to `fade`.
 * `k` scales lines and type, for the saved image and the video.
 * `type` sets the axes' type in pixels, { names, ticks }: by default it grows with `k`; a video sets its own, to read on a phone.
 */
export function paintCompass(ctx, plot, { markers, parties, logos, size, shown = () => 1, highlight = null, fade = 0.4, k = 1, type = null }) {
  paintAxes(ctx, plot, k, type || { names: 11 * k, ticks: 10 * k });
  const order = highlight ? [...markers.filter((m) => m.key !== highlight), ...markers.filter((m) => m.key === highlight)] : markers;
  for (const marker of order) {
    const appeared = shown(marker.key);
    if (appeared <= 0) continue;
    const party = parties[marker.key];
    const faded = highlight && marker.key !== highlight ? fade : 1;
    ctx.save();
    ctx.globalAlpha *= Math.min(1, appeared * 1.4) * faded;
    // The line from a moved tile back to its point, and the point itself.
    if (Math.hypot(marker.x - marker.px, marker.y - marker.py) > 2 * k) {
      ctx.strokeStyle = party.color;
      ctx.globalAlpha *= 0.8;
      ctx.lineWidth = 1.5 * k;
      ctx.beginPath();
      ctx.moveTo(marker.px, marker.py);
      ctx.lineTo(marker.x, marker.y);
      ctx.stroke();
      ctx.globalAlpha /= 0.8;
    }
    dot(ctx, marker.px, marker.py, 4.5 * k, WELL);
    dot(ctx, marker.px, marker.py, 3 * k, party.color);
    // The tile grows into place, overshooting a little, and the highlighted one stands a size larger.
    const grow = popScale(appeared) * (marker.key === highlight ? 1.18 : 1);
    const drawn = paintTile(ctx, marker.x, marker.y, size * grow, party, darkLogo(party, logos), {
      lifted: marker.key === highlight, k, width: marker.w * grow,
    });
    if (marker.inferred) paintInferredMark(ctx, drawn.x + drawn.width + 4 * k, drawn.y + 2 * k, k);
    ctx.restore();
  }
}

function paintAxes(ctx, plot, k, type) {
  const { x, y, w, h } = plot;
  ctx.save();
  ctx.lineWidth = 1 * k;
  ctx.strokeStyle = GRID;
  for (const tick of TICKS) {
    ctx.beginPath();
    ctx.moveTo(x + (tick / 10) * w, y);
    ctx.lineTo(x + (tick / 10) * w, y + h);
    ctx.moveTo(x, y + (tick / 10) * h);
    ctx.lineTo(x + w, y + (tick / 10) * h);
    ctx.stroke();
  }
  // The centre cross: 5 on both axes.
  ctx.strokeStyle = CROSS;
  ctx.lineWidth = 1.5 * k;
  ctx.beginPath();
  ctx.moveTo(x + w / 2, y);
  ctx.lineTo(x + w / 2, y + h);
  ctx.moveTo(x, y + h / 2);
  ctx.lineTo(x + w, y + h / 2);
  ctx.stroke();

  ctx.fillStyle = INK_3;
  ctx.font = `500 ${type.ticks}px ${MONO}`;
  ctx.textBaseline = 'top';
  ctx.textAlign = 'center';
  for (const tick of [0, 5, 10]) ctx.fillText(String(tick), x + (tick / 10) * w, y + h + type.ticks * 0.7);
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  for (const tick of [0, 5, 10]) ctx.fillText(String(tick), x - type.ticks * 0.8, y + (1 - tick / 10) * h);

  // The ends of the two axes, named inside the plot along the centre cross.
  ctx.font = `700 ${type.names}px ${FONT}`;
  ctx.fillStyle = INK_2;
  const inset = type.names * 0.7;
  const gap = type.names * 0.45;  // between a name and the line it runs along
  ctx.textBaseline = 'bottom';
  ctx.textAlign = 'left';
  ctx.fillText(gettext('Economic left').toUpperCase(), x + inset, y + h / 2 - gap);
  ctx.textAlign = 'right';
  ctx.fillText(gettext('Economic right').toUpperCase(), x + w - inset, y + h / 2 - gap);
  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';
  ctx.fillText(gettext('Conservative').toUpperCase(), x + w / 2 + gap * 1.4, y + inset);
  ctx.textBaseline = 'bottom';
  ctx.fillText(gettext('Progressive').toUpperCase(), x + w / 2 + gap * 1.4, y + h - inset);
  ctx.restore();
}

/**
 * A party's logo, fitted inside a box `size` tall and `width` wide (square by default), with no frame.
 * Behind the logo, a block of `fill`, the chart's own ground by default, hides the lines it covers.
 * `lifted` adds a shadow under the block.
 * A party without a free logo shows its abbreviation instead, in its colour.
 * Returns where the logo landed, { x, y, width, height }, for a mark beside it.
 */
export function paintTile(ctx, cx, cy, size, party, logo, { lifted = false, k = 1, width = size, fill = WELL } = {}) {
  const inset = size * 0.1;
  const box = { x: cx - width / 2 + inset, y: cy - size / 2 + inset, width: width - 2 * inset, height: size - 2 * inset };
  const drawn = logo ? containedRect(logo, box.x, box.y, box.width, box.height) : box;
  ctx.save();
  if (lifted) {
    ctx.shadowColor = 'rgba(0, 0, 0, 0.55)';
    ctx.shadowBlur = 18 * k;
    ctx.shadowOffsetY = 6 * k;
  }
  ctx.beginPath();
  ctx.roundRect(drawn.x - inset, drawn.y - inset, drawn.width + 2 * inset, drawn.height + 2 * inset, size * 0.22);
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.restore();
  if (logo) {
    ctx.drawImage(logo, drawn.x, drawn.y, drawn.width, drawn.height);
  } else {
    ctx.save();
    ctx.fillStyle = party.color;
    ctx.font = `800 ${Math.round(size * 0.32)}px ${FONT}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(party.abbreviation, cx, cy + 1);
    ctx.restore();
  }
  return drawn;
}

// The mark of an inferred place: a gold asterisk at the logo's top right corner, as on the list under the chart.
function paintInferredMark(ctx, x, y, k) {
  ctx.save();
  ctx.fillStyle = GOLD;
  ctx.font = `800 ${16 * k}px ${FONT}`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('*', x, y + 3 * k);
  ctx.restore();
}

/** The logo to draw on a dark ground: its light-ink copy where it has one. */
export function darkLogo(party, logos) {
  return logos.get(party.logoOnDark) || logos.get(party.logo);
}

function dot(ctx, x, y, r, colour) {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, 2 * Math.PI);
  ctx.fillStyle = colour;
  ctx.fill();
}

// How large a tile is as it appears: it grows from 60% and overshoots by about 8% before it settles.
function popScale(appeared) {
  if (appeared >= 1) return 1;
  const t = Math.max(0, appeared);
  return 0.6 + 0.4 * (1 + 2.2 * (t - 1) ** 3 + 1.2 * (t - 1) ** 2);
}
