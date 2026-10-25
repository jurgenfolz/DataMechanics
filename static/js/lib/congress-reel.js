// A house of Congress as a video, 1080 × 1920 for Instagram Reels or 1920 × 1080 for YouTube and LinkedIn.
// tools/reel.py records it, as it records the Politics charts' videos.
// The seats fill the half circle fast, left to right, in their bloc's colour; then a card goes through the blocs, left,
// centre and right, each lit in turn.
// The seats then turn to their party's colour, and a card goes through the largest parties, from the fewest seats to the most.
// The tables close it: the blocs and every party, with their seats.
// Frames are drawn on demand, and frame n is the same every time, so a recorder can take its time over each one.
// gettext and interpolate are Django's, from the translation catalog base.html loads.
import { FONT, imageWell, loadImage, MONO, paintGround, wrap } from './chart-image.js';
import { darkLogo, paintTile, tileWidth } from './compass.js';
import { hemicycleLayout, paintCaption, seatOwners } from './hemicycle.js';
import {
  canvasOf, clamp, easeInOut, easeOut, frameReady, FORMATS, INK, INK_2, INK_3, paintFooter, paintHeader, panel, RULE,
} from './reel-frame.js';

// The pace, in seconds.
const TIME = {
  intro: 0.6,  // the empty half circle
  fill: 2.2,  // every seat pops in, left to right
  pop: 0.3,  // one seat growing into place
  bloc: 3.4,  // one bloc lit, with its card
  turn: 1.6,  // the seats turn from their bloc's colour to their party's, left to right
  party: 2.4,  // one party lit, with its card
  fade: 0.35,  // the lit seats changing
  swap: 0.4,  // one card giving way to the next
  out: 0.6,  // the half circle giving way to the tables
  tables: 7,  // the tables, held to be read
};
const FAINT = 0.2;  // a seat that is not lit
const PARTIES = 10;  // the largest parties get a card each; the tables give every party

// Where the parts go in each shape, between the title's foot (`top`) and the source's top (`footer`).
const LAYOUTS = {
  // The half circle under the title, the card under it, the two together in the middle of the room.
  reel: (F, top, footer) => {
    const room = footer - 28 - top;
    const card = { h: 260 };
    const well = { h: Math.min(room - 28 - card.h, Math.round((F.width - 2 * F.pad) * 0.62)), w: F.width, pad: F.pad };
    well.top = top + Math.max(0, (room - well.h - 28 - card.h) / 2);
    Object.assign(card, { x: F.pad, y: well.top + well.h + 28, w: F.width - 2 * F.pad });
    return { well, card, tables: { x: F.pad, y: top, w: F.width - 2 * F.pad, h: room }, columns: 'stacked' };
  },
  // The half circle on the left; the card on the right, level with its middle.
  wide: (F, top, footer) => {
    const h = footer - 28 - top;
    const w = Math.round(F.width * 0.6);
    const card = { x: w + 24, w: F.width - w - 24 - F.pad, h: 280 };
    card.y = top + (h - card.h) / 2;
    return { well: { top, h, w, pad: F.pad }, card, tables: { x: F.pad, y: top, w: F.width - 2 * F.pad, h }, columns: 'side' };
  },
};

/**
 * Builds the video for one house in one term.
 * `term` is { parties, members, period } and `blocs` the blocs, as politics/congress.py gives them; `logos` maps a logo's
 * address to its loaded image.
 * Resolves to { canvas, frames, draw(n) }: draw(n) paints frame n on the canvas.
 */
export async function createCongressReel({ format = 'reel', title, unit, subtitle, explanation, flag, sources, term, blocs, logos }) {
  const F = FORMATS[format];
  await frameReady();
  const { parties, members } = term;
  const owners = seatOwners(parties);
  const blocOf = new Map(blocs.map((bloc) => [bloc.key, bloc]));
  const seatsIn = (key) => parties.filter((p) => p.bloc === key).reduce((sum, p) => sum + p.seats, 0);
  const share = new Intl.NumberFormat(document.documentElement.lang, { style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const score = new Intl.NumberFormat(document.documentElement.lang, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const ratio = (seats) => share.format(seats / members);

  // The parts that never move: ground, title, source, the brand band.
  const base = canvasOf(F);
  const baseCtx = base.getContext('2d');
  paintGround(baseCtx, F.width, F.height);
  const top = paintHeader(baseCtx, F, { title, flag: await loadImage(flag), unit, subtitle, explanation }) + 30;
  const footer = paintFooter(baseCtx, F, sources, F.safe.bottom);
  const layout = LAYOUTS[format](F, top, footer);

  // The well on a layer of its own, so it can fade out before the tables.
  const wellLayer = canvasOf(F);
  const { inner } = imageWell(wellLayer.getContext('2d'), layout.well.top, layout.well.h, { width: layout.well.w, pad: layout.well.pad });
  const seats = hemicycleLayout(members, { x: inner.x + 24, y: inner.y + 16, w: inner.w - 48, h: inner.h - 32 });
  const k = seats.radius / 300;

  // The story: each step lights some parties (null: all) and may show a card.
  const tour = blocs.filter((bloc) => bloc.key !== 'none' && seatsIn(bloc.key));
  // The largest parties get a card, the smallest of them first, so the largest comes last; a tie goes left to right.
  const ascending = parties.map((party, index) => ({ party, index })).sort((a, b) => b.party.seats - a.party.seats || a.index - b.index)
    .slice(0, PARTIES).sort((a, b) => a.party.seats - b.party.seats || a.index - b.index);
  const steps = [];
  let t = TIME.intro + TIME.fill;
  for (const bloc of tour) {
    steps.push({ from: t, lit: (owner) => parties[owner].bloc === bloc.key, card: { bloc }, caption: { value: seatsIn(bloc.key), text: bloc.name } });
    t += TIME.bloc;
  }
  const turn = t;
  steps.push({ from: t, lit: null, card: { byParty: true }, caption: { value: members, text: gettext('Seats') } });
  t += TIME.turn;
  for (const { party, index } of ascending) {
    steps.push({ from: t, lit: (owner) => owner === index, card: { party }, caption: { value: party.seats, text: party.abbreviation } });
    t += TIME.party;
  }
  const out = t;
  const frames = Math.ceil((out + TIME.out + TIME.tables) * 30) + 1;
  const stepAt = (time) => steps.findLastIndex((step) => step.from <= time);

  // A seat's brightness: what the current step asks, eased from what the step before asked.
  const brightness = (step, owner) => (!step?.lit || step.lit(owner) ? 1 : FAINT);
  function alphaOf(owner, time, index) {
    const now = brightness(steps[index], owner);
    if (index < 0) return 1;
    const before = brightness(steps[index - 1], owner);
    return before + (now - before) * easeOut(clamp((time - steps[index].from) / TIME.fade));
  }

  const canvas = canvasOf(F);
  const ctx = canvas.getContext('2d');

  function draw(n) {
    const time = n / 30;
    ctx.drawImage(base, 0, 0);
    const index = stepAt(time);
    const away = easeOut(clamp((time - out) / TIME.out));  // 1 once the tables have the room
    if (away < 1) {
      ctx.save();
      ctx.globalAlpha = 1 - away;
      ctx.drawImage(wellLayer, 0, 0);
      paintSeats(time, index);
      paintCards(time);
      ctx.restore();
    }
    if (time >= out) paintTables(time - out - TIME.out * 0.5);
  }

  function paintSeats(time, index) {
    const filling = (time - TIME.intro) / (TIME.fill - TIME.pop);
    const fade = ctx.globalAlpha;  // the whole half circle's, as it gives way to the tables
    seats.points.forEach((point, i) => {
      const owner = owners[i];
      const party = parties[owner];
      // Seats pop in left to right; a seat's colour turns from its bloc's to its party's in a sweep the same way.
      const grow = popScale(clamp((time - TIME.intro - (i / members) * (TIME.fill - TIME.pop)) / TIME.pop));
      if (grow <= 0) return;
      const turning = easeInOut(clamp((time - turn - (i / members) * TIME.turn * 0.5) / (TIME.turn * 0.5)));
      ctx.globalAlpha = fade * alphaOf(owner, time, index);
      ctx.beginPath();
      ctx.arc(point.x, point.y, seats.dot * grow, 0, 2 * Math.PI);
      ctx.fillStyle = mix(blocOf.get(party.bloc).color, party.color, turning);
      ctx.fill();
    });
    ctx.globalAlpha = fade;
    // The count runs up while the seats fill; then the lit bloc's or party's seats.
    const caption = index >= 0 ? steps[index].caption : { value: Math.round(members * clamp(filling)), text: gettext('Seats') };
    if (time >= TIME.intro) paintCaption(ctx, seats, caption, k * 1.6);
  }

  // One card at a time: the old one sinks away just before the next step, and the new one rises in with it.
  function paintCards(time) {
    const half = TIME.swap / 2;
    steps.forEach((step, i) => {
      const until = steps[i + 1]?.from ?? out + half;
      const enter = easeOut(clamp((time - step.from) / half));
      const leave = 1 - easeOut(clamp((time - (until - half)) / half));
      const shown = Math.min(enter, leave);
      if (shown <= 0) return;
      ctx.save();
      ctx.globalAlpha *= shown;
      ctx.translate(0, (1 - enter) * 18 - (1 - leave) * 18);
      if (step.card.bloc) paintBlocCard(ctx, layout.card, step.card.bloc);
      else if (step.card.party) paintPartyCard(ctx, layout.card, step.card.party);
      else paintTurnCard(ctx, layout.card);
      ctx.restore();
    });
  }

  // A bloc's card: its seats and share, large, beside its name, the bands it joins, and its parties with their seats.
  function paintBlocCard(c, box, bloc) {
    panel(c, box, bloc.color);
    const pad = 32;
    const seatsWidth = paintBigSeats(c, box, pad, seatsIn(bloc.key));
    const x = box.x + pad + seatsWidth + 36;
    const width = box.x + box.w - pad - x;
    c.textBaseline = 'top';
    c.fillStyle = INK;
    c.font = `800 48px ${FONT}`;
    c.fillText(bloc.name, x, box.y + pad);
    c.fillStyle = INK_3;
    c.font = `500 24px ${FONT}`;
    c.fillText(bloc.bands, x, box.y + pad + 62);
    const inBloc = parties.filter((p) => p.bloc === bloc.key).sort((a, b) => b.seats - a.seats);
    c.fillStyle = INK_2;
    c.font = `500 26px ${FONT}`;
    let y = box.y + pad + 112;
    for (const line of wrap(c, inBloc.map((p) => `${p.abbreviation} ${p.seats}`).join(' · '), width, 4)) {
      c.fillText(line, x, y);
      y += 36;
    }
  }

  // A party's card: its seats and share, large, beside its logo, names and where the survey puts it.
  function paintPartyCard(c, box, party) {
    panel(c, box, party.color);
    const pad = 32;
    const seatsWidth = paintBigSeats(c, box, pad, party.seats);
    const x = box.x + pad + seatsWidth + 36;
    const width = box.x + box.w - pad - x;
    const logo = darkLogo(party, logos);
    let y = box.y + pad;
    if (party.logo) {
      // The logo starts where the lines under it start.
      const width = tileWidth(logo, 80);
      const drawn = paintTile(c, x - 8 + width / 2, y + 40, 80, party, logo, { width, fill: '#17191b', k: 1.4 });
      c.textBaseline = 'middle';
      c.fillStyle = INK;
      c.font = `800 44px ${FONT}`;
      c.fillText(party.abbreviation, drawn.x + drawn.width + 22, y + 40);
    } else {
      c.textBaseline = 'middle';
      c.fillStyle = INK;
      c.font = `800 44px ${FONT}`;
      c.fillText(party.abbreviation, x, y + 40);
    }
    y += 96;
    c.textBaseline = 'top';
    if (party.name !== party.abbreviation) {
      c.fillStyle = INK_2;
      c.font = `500 24px ${FONT}`;
      c.fillText(wrap(c, party.name, width, 1)[0], x, y);
      y += 40;
    }
    // Its bloc, in the bloc's colour, then its band and score.
    const bloc = blocOf.get(party.bloc);
    c.fillStyle = bloc.color;
    c.beginPath();
    c.arc(x + 9, y + 13, 9, 0, 2 * Math.PI);
    c.fill();
    c.fillStyle = INK;
    c.font = `700 24px ${FONT}`;
    c.fillText(bloc.name, x + 28, y);
    const place = party.score === null ? '' : ` · ${party.band} · ${score.format(party.score)}`;
    const offset = c.measureText(bloc.name).width;
    c.fillStyle = INK_3;
    c.font = `500 24px ${FONT}`;
    c.fillText(place, x + 28 + offset, y);
  }

  // Between the blocs and the parties: the same seats, now by party.
  function paintTurnCard(c, box) {
    panel(c, box, '#ffd700');
    const pad = 34;
    c.textBaseline = 'top';
    c.fillStyle = INK;
    c.font = `800 48px ${FONT}`;
    c.fillText(gettext('By party'), box.x + pad, box.y + pad);
    c.fillStyle = INK_2;
    c.font = `500 26px ${FONT}`;
    let y = box.y + pad + 70;
    const text = interpolate(gettext('The same %(seats)s seats, coloured by party. Next, the %(count)s largest parties, from the fewest seats to the most.'),
      { seats: members, count: ascending.length }, true);
    for (const line of wrap(c, text, box.w - 2 * pad, 3)) {
      c.fillText(line, box.x + pad, y);
      y += 36;
    }
  }

  // The seats, large, with their share under them; returns the width they take.
  function paintBigSeats(c, box, pad, count) {
    c.textBaseline = 'top';
    c.fillStyle = INK;
    c.font = `700 104px ${MONO}`;
    const width = Math.max(c.measureText(String(count)).width, 150);
    c.fillText(String(count), box.x + pad, box.y + pad - 6);
    c.fillStyle = INK_3;
    c.font = `500 24px ${FONT}`;
    c.fillText(`${gettext('Seats')} · ${ratio(count)}`, box.x + pad, box.y + pad + 112);
    return Math.max(width, c.measureText(`${gettext('Seats')} · ${ratio(count)}`).width);
  }

  // ---------- The tables: the blocs, then every party ----------
  // Each row slides in a moment after the one before it.
  function paintTables(time) {
    const box = layout.tables;
    const appear = (row) => easeOut(clamp((time - row * 0.06) / 0.4));
    const rowsOfBlocs = blocs.filter((bloc) => seatsIn(bloc.key));
    const ranked = [...parties].sort((a, b) => b.seats - a.seats);
    const half = Math.ceil(ranked.length / 2);
    let blocBox;
    let partyBox;
    if (layout.columns === 'side') {
      blocBox = { x: box.x, y: box.y, w: box.w * 0.34, h: box.h };
      partyBox = { x: box.x + box.w * 0.34 + 48, y: box.y, w: box.w * 0.66 - 48, h: box.h };
    } else {
      const blocHeight = 56 + rowsOfBlocs.length * 84;
      blocBox = { x: box.x, y: box.y, w: box.w, h: blocHeight };
      partyBox = { x: box.x, y: box.y + blocHeight + 28, w: box.w, h: box.h - blocHeight - 28 };
    }
    paintHeading(ctx, blocBox, gettext('Left, centre and right'), appear(0));
    rowsOfBlocs.forEach((bloc, i) => {
      ctx.save();
      ctx.globalAlpha = appear(i + 1);
      ctx.translate((1 - appear(i + 1)) * 24, 0);
      paintBlocRow(ctx, bloc, seatsIn(bloc.key), { x: blocBox.x, y: blocBox.y + 56 + i * 84, w: blocBox.w, h: 84 });
      ctx.restore();
    });
    paintHeading(ctx, partyBox, gettext('By party'), appear(rowsOfBlocs.length + 1));
    const rowHeight = Math.min(64, (partyBox.h - 56) / half);
    const width = (partyBox.w - 40) / 2;
    ranked.forEach((party, i) => {
      const column = Math.floor(i / half);
      const row = i % half;
      ctx.save();
      ctx.globalAlpha = appear(rowsOfBlocs.length + 2 + i * 0.5);
      paintPartyRow(ctx, party, { x: partyBox.x + column * (width + 40), y: partyBox.y + 56 + row * rowHeight, w: width, h: rowHeight });
      ctx.restore();
    });
  }

  function paintHeading(c, box, text, alpha) {
    c.save();
    c.globalAlpha = alpha;
    c.textBaseline = 'top';
    c.fillStyle = INK_3;
    c.font = `600 22px ${MONO}`;
    c.fillText(text.toUpperCase(), box.x, box.y + 8);
    c.fillStyle = RULE;
    c.fillRect(box.x, box.y + 42, box.w, 1.5);
    c.restore();
  }

  function paintBlocRow(c, bloc, count, row) {
    const middle = row.y + row.h / 2;
    c.fillStyle = bloc.color;
    c.beginPath();
    c.roundRect(row.x, middle - 26, 8, 52, 4);
    c.fill();
    c.textBaseline = 'alphabetic';
    c.fillStyle = INK;
    c.font = `800 36px ${FONT}`;
    c.fillText(bloc.name, row.x + 26, middle + 2);
    c.fillStyle = INK_3;
    c.font = `500 20px ${FONT}`;
    c.fillText(bloc.bands, row.x + 26, middle + 30);
    c.textAlign = 'right';
    c.fillStyle = INK;
    c.font = `700 40px ${MONO}`;
    c.fillText(String(count), row.x + row.w - 130, middle + 14);
    c.fillStyle = INK_3;
    c.font = `500 22px ${MONO}`;
    c.fillText(ratio(count), row.x + row.w, middle + 12);
    c.textAlign = 'left';
  }

  function paintPartyRow(c, party, row) {
    const middle = row.y + row.h / 2;
    const size = Math.min(44, row.h - 14);
    c.fillStyle = party.color;
    c.beginPath();
    c.roundRect(row.x, middle - size / 2, 6, size, 3);
    c.fill();
    if (party.logo) paintTile(c, row.x + 20 + size * 0.8, middle, size, party, darkLogo(party, logos), { width: size * 1.6, fill: '#17191b', k: 1.4 });
    c.textBaseline = 'middle';
    c.fillStyle = INK;
    c.font = `700 26px ${FONT}`;
    c.fillText(party.abbreviation, row.x + 32 + size * 1.6, middle);
    c.textAlign = 'right';
    c.font = `700 28px ${MONO}`;
    c.fillText(String(party.seats), row.x + row.w - 100, middle);
    c.fillStyle = INK_3;
    c.font = `500 20px ${MONO}`;
    c.fillText(ratio(party.seats), row.x + row.w, middle);
    c.textAlign = 'left';
  }

  return { canvas, frames, draw };
}

// How large a seat is as it appears: it grows from nothing and overshoots a little before it settles.
function popScale(t) {
  if (t <= 0) return 0;
  if (t >= 1) return 1;
  return 1 + 2.2 * (t - 1) ** 3 + 1.2 * (t - 1) ** 2;
}

// The colour `f` of the way from hex colour `a` to hex colour `b`.
function mix(a, b, f) {
  if (f <= 0) return a;
  if (f >= 1) return b;
  const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  const [from, to] = [rgb(a), rgb(b)];
  return `rgb(${from.map((v, i) => Math.round(v + (to[i] - v) * f)).join(', ')})`;
}
