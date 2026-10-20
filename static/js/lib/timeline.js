// The presidents with data for a measure, in three views: the timeline, newest first, and two rankings that add the
// changes up by party and by president. These are the rows of the country page and of its saved images.
// The images keep each row exactly as on the page, at SCALE times its size. Rows that do not fit go on the next image.
// gettext, ngettext and interpolate are Django's, from the translation catalog base.html loads.
import {
  handOver, imageFrame, imageName, imageWell, loadImage, MONO, paintPageNumber, paintWatermark, SCALE, wrap,
} from './chart-image.js';
import { paintLogoTile, paintTrend, toneOf } from './term-chart.js';

const ROW = 56;  // a row's height on the page in CSS pixels, as in .term-row
const NOTE_ROOM = 36;  // the band under the rows that holds the note about presidents left out
const HEAD = 30;  // the column labels over a ranking's rows
const SANS = 'Archivo, "Helvetica Neue", Arial, sans-serif';
const WELL = '#1d1f21';

/** One row per presidency with data, newest first, with what the timeline shows of it. */
export function timelineRows(data) {
  return data.presidencies.map((p, index) => ({ p, index })).filter(({ p }) => p.summary).reverse().map(({ p, index }) => {
    // The parties a presidency held, in order. Months without a party show as grey on the line, not as a logo here.
    const parties = [...new Map(p.spans.map((s) => [s.party.name, s.party])).values()].filter((party) => party.abbreviation);
    const logos = parties.length ? parties : [p.party];
    return {
      index,
      presidency: p,
      logos,
      color: logos.at(-1).color,
      years: `${p.start.slice(0, 4)}–${p.current ? gettext('now') : p.end.slice(0, 4)}`,
      partyNames: logos.map((party) => party.abbreviation || party.name).join(', '),
    };
  });
}

/**
 * The bars' shared axis, like Power BI's data bars: each row's change drawn from one zero line, rises to the right
 * and falls to the left. Positions are fractions of the bar column's width; `axis` is where zero sits.
 */
export function barScale(amounts) {
  const low = Math.min(0, ...amounts);
  const high = Math.max(0, ...amounts);
  const span = high - low || 1;
  const axis = -low / span;
  return {
    axis,
    bar: (amount) => ({ from: Math.min(axis, axis + amount / span), width: Math.abs(amount) / span }),
  };
}

/**
 * The rows of a ranking, best first as the server ranked them (politics/queries.py, grouped_changes).
 * `view` is 'party' or 'president'; each row has the logos, a name with a short aside, a second line, and the
 * change per year and in total.
 */
export function groupRows(data, view) {
  const party = view === 'party';
  return (party ? data.byParty : data.byPresident).map((group, i) => ({
    rank: i + 1,
    logos: party ? [group.party] : group.parties,
    name: party ? group.party.abbreviation || group.party.name : group.shortName,
    // The full name only adds something when the short one is an abbreviation (PT: Workers' Party, not Democratic).
    aside: party ? (group.party.name.startsWith(group.party.abbreviation) ? '' : group.party.name)
      : group.parties.map((p) => p.abbreviation || p.name).join(', '),
    sub: party ? group.presidents.join(', ') : '',
    title: party ? group.party.name : group.leader,
    perYear: group.perYear,
    total: group.total,
  }));
}

/** The value at the start and at the end of a presidency, e.g. "$2.86 k - $11.4 k". */
export function valueRange(summary) {
  return `${summary.startLabel} - ${summary.endLabel}`;
}

/** The line under the lists that counts the terms left out for lack of data in the window, or '' when none is. */
export function omittedNote(data) {
  const left = data.presidencies.filter((p) => p.inWindow !== false && !p.summary).length;
  return left ? interpolate(ngettext('%s term without enough data for this measure is not listed.',
    '%s terms without enough data for this measure are not listed.', left), [left]) : '';
}

/**
 * Saves a view (the timeline, or the ranking by party or by president) as 1080 × 1350 images: as many rows on each as
 * fit, and as many images as it takes. The footer names the data's source; a logo whose licence asks for credit adds it
 * on the image that shows it.
 */
export async function saveTimelineImages({ data, view = 'timeline', title, subtitle, source, nameParts }) {
  const timeline = view === 'timeline';
  const rows = timeline ? timelineRows(data) : groupRows(data, view);
  const note = omittedNote(data);
  const logoFiles = [...new Set(rows.flatMap((row) => row.logos.map((party) => party.logo)).filter(Boolean))];
  const logos = new Map(await Promise.all(logoFiles.map(async (src) => [src, await loadImage(src)])));
  const text = (shown) => ({ title, subtitle, sources: [source, logoCredits(shown)] });

  // Room is measured with every credit in the footer, so no image runs short when its own credits are fewer.
  const probe = await imageFrame(text(rows));
  const room = probe.bottom - probe.top;
  const head = timeline ? 0 : HEAD;
  // Every image keeps a band for the note, so the note always fits under the last row and never needs an image of its own.
  const perImage = Math.max(1, Math.floor((imageWellInnerHeight(room) / SCALE - head - (note ? NOTE_ROOM : 0)) / ROW));
  const pages = Math.ceil(rows.length / perImage);
  probe.ctx.font = `700 12px ${MONO}`;
  const changeWidth = (summary) => 20 + probe.ctx.measureText(summary.change).width;
  const layout = timeline
    ? { trendWidth: Math.max(...rows.map((row) => changeWidth(row.presidency.summary))),
      scale: barScale(rows.map((row) => row.presidency.summary.amount)) }
    : { perYearWidth: Math.max(...rows.map((row) => changeWidth(row.perYear)), labelWidth(probe.ctx, PER_YEAR())),
      totalWidth: Math.max(...rows.map((row) => changeWidth(row.total)), labelWidth(probe.ctx, gettext('Total'))),
      scale: barScale(rows.map((row) => row.perYear.amount)) };

  const images = [];
  for (let page = 0; page < pages; page += 1) {
    const shown = rows.slice(page * perImage, (page + 1) * perImage);
    const frame = await imageFrame(text(shown));
    const { well, inner } = imageWell(frame.ctx, probe.top, room);
    const ctx = frame.ctx;
    ctx.save();
    ctx.translate(inner.x, inner.y);
    ctx.scale(SCALE, SCALE);
    const width = inner.w / SCALE;
    if (timeline) {
      shown.forEach((row, i) => paintRow(ctx, row, i * ROW, { ...layout, width }, logos, { first: row === rows[0], last: row === rows.at(-1) }));
    } else {
      paintGroupHead(ctx, { ...layout, width });
      shown.forEach((row, i) => paintGroupRow(ctx, row, head + i * ROW, { ...layout, width }, logos, { first: i === 0, last: i === shown.length - 1 }));
    }
    if (note && page === pages - 1) {
      ctx.font = `400 12px ${SANS}`;
      ctx.fillStyle = '#8b8f94';
      ctx.textBaseline = 'middle';
      // Up to two lines, in the band under the last row.
      const x = timeline ? 106 : 32;
      const lines = wrap(ctx, note, width - x, 2);
      lines.forEach((line, i) => ctx.fillText(line, x, head + shown.length * ROW + NOTE_ROOM / 2 + (i - (lines.length - 1) / 2) * 16));
    }
    ctx.restore();
    paintPageNumber(ctx, well, page + 1, pages);
    await paintWatermark(ctx, well);
    images.push({ canvas: frame.canvas, filename: imageName(...nameParts, timeline ? '' : view, pages > 1 ? page + 1 : '') });
  }
  await handOver(images, title);
}

// The ranking's column labels, upper case in mono, on up to two lines no wider than LABEL_WIDTH.
const LABEL_WIDTH = 124;
const PER_YEAR = () => gettext('Per year');

function labelLines(ctx, text) {
  ctx.font = `500 10px ${MONO}`;
  return wrap(ctx, text.toUpperCase(), LABEL_WIDTH, 2);
}

function labelWidth(ctx, text) {
  return Math.max(...labelLines(ctx, text).map((line) => ctx.measureText(line).width));
}

/** The credits the logos on these rows ask for, in one line, or '' when none does. */
export function logoCredits(rows) {
  const credits = new Set(rows.flatMap((row) => row.logos.map((party) => party.credit)).filter(Boolean));
  return [...credits].join('; ');
}

function imageWellInnerHeight(room) {
  const probe = document.createElement('canvas').getContext('2d');
  return imageWell(probe, 0, room).inner.h;
}

const BAR_WIDTH = 48;  // the data bars' column, between the text and the change

// One row: years, the rail with its dot, the logo tiles, the name with its parties over the start and end values,
// the change's bar on the shared axis, and the change. Coordinates are CSS pixels; the caller scales them.
function paintRow(ctx, row, top, { width, trendWidth, scale }, logos, { first, last }) {
  const p = row.presidency;
  const s = p.summary;
  const middle = top + ROW / 2;
  ctx.textBaseline = 'middle';

  ctx.font = `400 11px ${MONO}`;
  ctx.fillStyle = '#8b8f94';
  ctx.textAlign = 'right';
  ctx.fillText(row.years, 62, middle);
  ctx.textAlign = 'left';

  // The rail runs through the row in the party's colour; it starts at the newest dot and ends at the oldest.
  const railX = 84;
  ctx.strokeStyle = row.color;
  ctx.globalAlpha = 0.6;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(railX, first ? middle : top);
  ctx.lineTo(railX, last ? middle : top + ROW);
  ctx.stroke();
  ctx.globalAlpha = 1;
  const dot = (radius, color) => {
    ctx.beginPath();
    ctx.arc(railX, middle, radius, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
  };
  if (p.current) dot(11, row.color);
  dot(9, WELL);
  dot(6, row.color);

  row.logos.forEach((party, i) => {
    const x = 106 + i * 24;
    if (i) {
      ctx.beginPath();
      ctx.roundRect(x - 2, middle - 18, 36, 36, 9);
      ctx.fillStyle = WELL;
      ctx.fill();
    }
    paintLogoTile(ctx, party, logos.get(party.logo), x, middle - 16, 32);
  });

  // The change, right-aligned in a column as wide as the widest change, and its bar just before it.
  ctx.font = `700 12px ${MONO}`;
  const changeWidth = 20 + ctx.measureText(s.change).width;
  paintTrend(ctx, s, width - changeWidth, middle);
  const barRight = width - trendWidth - 12;
  const barLeft = barRight - BAR_WIDTH;
  ctx.strokeStyle = '#3a3d41';
  ctx.lineWidth = 1;
  ctx.beginPath();
  const axisX = Math.round(barLeft + scale.axis * BAR_WIDTH) + 0.5;
  ctx.moveTo(axisX, first ? middle - 14 : top);
  ctx.lineTo(axisX, last ? middle + 14 : top + ROW);
  ctx.stroke();
  const bar = scale.bar(s.amount);
  ctx.globalAlpha = 0.8;
  ctx.fillStyle = TONES[toneOf(s)];
  ctx.beginPath();
  ctx.roundRect(barLeft + bar.from * BAR_WIDTH, middle - 5, Math.max(2, bar.width * BAR_WIDTH), 10, 3);
  ctx.fill();
  ctx.globalAlpha = 1;

  // The name with its parties on the first line, the values on the second.
  const textX = 106 + 32 + 24 * (row.logos.length - 1) + 12;
  const textWidth = barLeft - 12 - textX;
  ctx.font = `700 15px ${SANS}`;
  ctx.fillStyle = '#f2f3f4';
  const name = wrap(ctx, p.shortName, textWidth, 1)[0];
  ctx.fillText(name, textX, middle - 8);
  const nameWidth = ctx.measureText(name).width;
  const status = p.current ? ` · ${gettext('In office')}` : '';
  ctx.font = `400 11px ${MONO}`;
  ctx.fillStyle = '#8b8f94';
  const parties = wrap(ctx, `${row.partyNames}${status}`, textWidth - nameWidth - 8, 1)[0];
  if (textWidth - nameWidth - 8 > 24) ctx.fillText(parties, textX + nameWidth + 8, middle - 7);
  ctx.fillText(wrap(ctx, valueRange(s), textWidth, 1)[0], textX, middle + 10);
}

const TONES = { good: '#2bc892', bad: '#f2545b', neutral: '#8b8f94' };

// ---------- The rankings ----------
const RANK_X = 18;  // right edge of the rank
const LOGO_X = 30;

// The column labels over a ranking, aligned with the change per year and the total.
function paintGroupHead(ctx, { width, totalWidth }) {
  ctx.fillStyle = '#8b8f94';
  ctx.textBaseline = 'bottom';
  ctx.textAlign = 'right';
  const paint = (text, right) => {
    const lines = labelLines(ctx, text);
    lines.forEach((line, i) => ctx.fillText(line, right, HEAD - 6 - (lines.length - 1 - i) * 12));
  };
  paint(gettext('Total'), width);
  paint(PER_YEAR(), width - totalWidth - 16);
  ctx.textAlign = 'left';
}

// One ranking row: rank, logos, the name with its aside over a second line, the per-year change's bar on the shared
// axis, the change per year and the total. Coordinates are CSS pixels; the caller scales them.
function paintGroupRow(ctx, row, top, { width, perYearWidth, totalWidth, scale }, logos, { first, last }) {
  const middle = top + ROW / 2;
  ctx.textBaseline = 'middle';
  ctx.font = `400 11px ${MONO}`;
  ctx.fillStyle = '#8b8f94';
  ctx.textAlign = 'right';
  ctx.fillText(String(row.rank), RANK_X, middle);
  ctx.textAlign = 'left';

  row.logos.forEach((party, i) => {
    const x = LOGO_X + i * 24;
    if (i) {
      ctx.beginPath();
      ctx.roundRect(x - 2, middle - 18, 36, 36, 9);
      ctx.fillStyle = WELL;
      ctx.fill();
    }
    paintLogoTile(ctx, party, logos.get(party.logo), x, middle - 16, 32);
  });

  // The total at the right edge, the change per year before it, each right-aligned in its column.
  ctx.font = `700 12px ${MONO}`;
  paintTrend(ctx, row.total, width - (20 + ctx.measureText(row.total.change).width), middle);
  const perYearRight = width - totalWidth - 16;
  paintTrend(ctx, row.perYear, perYearRight - (20 + ctx.measureText(row.perYear.change).width), middle);

  const barRight = perYearRight - perYearWidth - 12;
  const barLeft = barRight - BAR_WIDTH;
  ctx.strokeStyle = '#3a3d41';
  ctx.lineWidth = 1;
  ctx.beginPath();
  const axisX = Math.round(barLeft + scale.axis * BAR_WIDTH) + 0.5;
  ctx.moveTo(axisX, first ? middle - 14 : top);
  ctx.lineTo(axisX, last ? middle + 14 : top + ROW);
  ctx.stroke();
  const bar = scale.bar(row.perYear.amount);
  ctx.globalAlpha = 0.8;
  ctx.fillStyle = TONES[toneOf(row.perYear)];
  ctx.beginPath();
  ctx.roundRect(barLeft + bar.from * BAR_WIDTH, middle - 5, Math.max(2, bar.width * BAR_WIDTH), 10, 3);
  ctx.fill();
  ctx.globalAlpha = 1;

  const textX = LOGO_X + 32 + 24 * (row.logos.length - 1) + 12;
  const textWidth = barLeft - 12 - textX;
  const nameY = row.sub ? middle - 8 : middle;
  ctx.font = `700 15px ${SANS}`;
  ctx.fillStyle = '#f2f3f4';
  const name = wrap(ctx, row.name, textWidth, 1)[0];
  ctx.fillText(name, textX, nameY);
  const nameWidth = ctx.measureText(name).width;
  ctx.font = `400 11px ${MONO}`;
  ctx.fillStyle = '#8b8f94';
  if (row.aside && textWidth - nameWidth - 8 > 24) {
    ctx.fillText(wrap(ctx, row.aside, textWidth - nameWidth - 8, 1)[0], textX + nameWidth + 8, nameY + 1);
  }
  if (row.sub) ctx.fillText(wrap(ctx, row.sub, textWidth, 1)[0], textX, middle + 10);
}

