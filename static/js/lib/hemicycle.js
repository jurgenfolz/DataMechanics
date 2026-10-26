// A parliament drawn as a half circle of dots, one dot a seat, the rows running from the inside out.
// Seats are handed out by angle, from the left end round to the right, so each party fills a wedge in its turn.
// The Politics page and its saved image draw it with this module.
import { FONT, MONO } from './chart-image.js';

const INNER = 0.36;  // the empty middle, as a share of the outer radius

/**
 * Where each of `seats` dots goes in a half circle that fits `box` ({ x, y, w, h }), sitting on its floor.
 * Returns { cx, cy, radius, dot, points }: the centre of the floor, the outer radius, a dot's radius, and the points
 * ({ x, y }) in the order seats are handed out, left to right.
 */
export function hemicycleLayout(seats, box) {
  // The fewest rows that hold every seat, with as much room between rows as between neighbours in a row.
  // Rows hold the same seats at any size, so they are counted on a half circle of radius 1.
  let rows = 1;
  let capacities = [];
  for (; rows < 60; rows += 1) {
    const share = (1 - INNER) / Math.max(rows - 1, 1);
    capacities = Array.from({ length: rows }, (_, i) => Math.floor((Math.PI * (INNER + i * share)) / share) + 1);
    if (capacities.reduce((a, b) => a + b, 0) >= seats) break;
  }
  // As large as the box allows, with the outer dots' own radius inside it too: few seats make large dots.
  const dotShare = 0.4 * (1 - INNER) / Math.max(rows - 1, 1);
  const radius = Math.max(10, Math.min(box.w / (2 * (1 + dotShare)), box.h / (1 + 2 * dotShare)) * 0.98);
  const inner = radius * INNER;
  const cx = box.x + box.w / 2;
  const cy = box.y + box.h - (box.h - radius) / 2;
  const step = (radius - inner) / Math.max(rows - 1, 1);
  // Each row takes its share of the seats by its length; rounding leftovers go to the outer rows.
  const total = capacities.reduce((a, b) => a + b, 0);
  const counts = capacities.map((capacity) => Math.floor((seats * capacity) / total));
  for (let i = rows - 1, left = seats - counts.reduce((a, b) => a + b, 0); left > 0; i = (i - 1 + rows) % rows, left -= 1) counts[i] += 1;
  const points = [];
  counts.forEach((count, i) => {
    const r = inner + i * step;
    for (let j = 0; j < count; j += 1) {
      const angle = count === 1 ? Math.PI / 2 : Math.PI - (j * Math.PI) / (count - 1);
      points.push({ x: cx + r * Math.cos(angle), y: cy - r * Math.sin(angle), angle, r });
    }
  });
  points.sort((a, b) => b.angle - a.angle || a.r - b.r);
  return { cx, cy, radius, dot: Math.max(1.5, step * 0.4), points };
}

/** Which party each point belongs to: `parties` are { key, seats } in their order round the half circle. */
export function seatOwners(parties) {
  return parties.flatMap((party, i) => Array.from({ length: party.seats }, () => i));
}

/**
 * Paints the half circle: every dot in its party's colour, and a caption in the middle.
 * `colorOf(party)` gives a dot's colour: the party's own by default, or its bloc's.
 * `lit` is a Set of party indices to keep bright while the others fade back; null keeps every dot bright.
 * `caption` is { value, text }: a number in large type over a line of text; null draws none.
 */
export function paintHemicycle(ctx, layout, parties, { colorOf = (party) => party.color, lit = null, caption = null, k = 1 } = {}) {
  const owners = seatOwners(parties);
  layout.points.forEach((point, i) => {
    const owner = owners[i];
    ctx.globalAlpha = !lit || lit.has(owner) ? 1 : 0.22;
    ctx.beginPath();
    ctx.arc(point.x, point.y, layout.dot, 0, 2 * Math.PI);
    ctx.fillStyle = parties[owner] ? colorOf(parties[owner]) : '#5a5e63';
    ctx.fill();
  });
  ctx.globalAlpha = 1;
  if (caption) paintCaption(ctx, layout, caption, k);
}

/** The caption in the middle of the half circle: `value` in large type over `text`. */
export function paintCaption(ctx, layout, { value, text }, k = 1) {
  ctx.textAlign = 'center';
  ctx.textBaseline = 'alphabetic';
  ctx.fillStyle = '#f2f3f4';
  ctx.font = `700 ${Math.round(layout.radius * 0.16)}px ${MONO}`;
  ctx.fillText(String(value), layout.cx, layout.cy - layout.radius * 0.06);
  ctx.fillStyle = '#8b8f94';
  ctx.font = `500 ${Math.max(11 * k, Math.round(layout.radius * 0.055))}px ${FONT}`;
  ctx.fillText(text, layout.cx, layout.cy + layout.radius * 0.02);
  ctx.textAlign = 'left';
}

/** The index of the party whose dot is under (x, y), or null. */
export function partyAt(layout, parties, x, y) {
  const owners = seatOwners(parties);
  let best = null;
  let nearest = (layout.dot * 1.8) ** 2;
  layout.points.forEach((point, i) => {
    const distance = (point.x - x) ** 2 + (point.y - y) ** 2;
    if (distance < nearest) {
      nearest = distance;
      best = owners[i];
    }
  });
  return best;
}
