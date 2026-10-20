// Saves a chart as a PNG the shape of an Instagram portrait post (1080 × 1350): title, chart, legend, source and a
// semi-transparent Data Mechanics watermark. The chart is drawn again off screen and enlarged SCALE times, so its text
// stays readable on a phone without crowding the image.
// gettext and interpolate are Django's, from the translation catalog base.html loads.

export const WIDTH = 1080;
export const HEIGHT = 1350;
export const SCALE = 1.6;

const PAD = 56;
const WELL_INSET = 12;
const STRIP = 44;  // the room at the foot of the well that holds the watermark, so it never covers the chart
const GROUND = '#121416';
const WELL = '#1d1f21';
const INK = '#f2f3f4';
const INK_2 = '#b6b9bd';
const INK_3 = '#8b8f94';
const GOLD = '#ffd700';
const FONT = 'Archivo, "Helvetica Neue", Arial, sans-serif';
export const MONO = '"JetBrains Mono", ui-monospace, Menlo, Consolas, monospace';

/**
 * Builds the image and hands it over: the share sheet on phones, so Instagram is one tap away, a download elsewhere.
 * `draw(element)` draws the chart in an off-screen element and resolves, once it has finished, to
 * { chart, dispose(), paint?(ctx, x, y, scale), below?(ctx, box) }: the ECharts instance and how to remove it,
 * painting for HTML parts over it, and a legend or list for the room under it.
 * The chart modules build `draw` with their *ImageParts helpers.
 * With `aspect` the chart keeps that width / height and `below` gets the rest; otherwise `below` gets `belowHeight`.
 */
export async function saveChartImage({ title, subtitle, sources, filename, draw, aspect, belowHeight = 0 }) {
  const { canvas, ctx, top, bottom } = await imageFrame({ title, subtitle, sources });
  const room = bottom - top;
  const height = aspect ? Math.min(room, Math.round((WIDTH - 2 * (PAD - 16) - 2 * WELL_INSET) / aspect) + WELL_INSET + STRIP)
    : room - belowHeight;
  const { well, inner } = imageWell(ctx, top, height);
  const footerTop = bottom + 32;
  const stage = createStage(inner.w / SCALE, inner.h / SCALE);
  try {
    const drawn = await draw(stage.element);
    ctx.drawImage(await chartImage(drawn.chart), inner.x, inner.y, inner.w, inner.h);
    await drawn.paint?.(ctx, inner.x, inner.y, SCALE);
    const below = { x: PAD, y: well.y + well.h + 28, w: WIDTH - 2 * PAD };
    below.h = footerTop - 24 - below.y;
    if (below.h > 0) await drawn.below?.(ctx, below);
    drawn.dispose();
  } finally {
    stage.remove();
  }
  await paintWatermark(ctx, well);
  await handOver([{ canvas, filename }], title);
}

/** A new image with its frame painted: ground, header and footer. The room between them runs from `top` to `bottom`. */
export async function imageFrame({ title, subtitle, sources }) {
  await fontsReady();
  const canvas = document.createElement('canvas');
  canvas.width = WIDTH;
  canvas.height = HEIGHT;
  const ctx = canvas.getContext('2d');
  paintGround(ctx);
  const headerBottom = paintHeader(ctx, title, subtitle);
  const footerTop = paintFooter(ctx, sources);
  return { canvas, ctx, top: headerBottom + 36, bottom: footerTop - 32 };
}

/** Paints the well at `top`, `height` tall. `inner` is the room inside it, above the watermark's strip. */
export function imageWell(ctx, top, height) {
  const well = { x: PAD - 16, y: top, w: WIDTH - 2 * (PAD - 16), h: height };
  paintWell(ctx, well);
  const inner = { x: well.x + WELL_INSET, y: well.y + WELL_INSET, w: well.w - 2 * WELL_INSET, h: well.h - WELL_INSET - STRIP };
  return { well, inner };
}

/** "2 / 3" at the left of the watermark's strip, when one subject takes several images. */
export function paintPageNumber(ctx, well, page, pages) {
  if (pages < 2) return;
  ctx.save();
  ctx.font = `500 17px ${MONO}`;
  ctx.fillStyle = INK_3;
  ctx.textBaseline = 'middle';
  ctx.fillText(`${page} / ${pages}`, well.x + 24, well.y + well.h - STRIP / 2 - 2);
  ctx.restore();
}
/** Resolves once a chart has finished drawing (or after two seconds, whichever comes first). Call before rendering. */
export function whenFinished(chart) {
  return new Promise((resolve) => {
    const done = () => {
      chart.off('finished', done);
      resolve();
    };
    chart.on('finished', done);
    setTimeout(done, 2000);
  });
}

/** A file name from its parts, e.g. data-mechanics-gdp-per-capita-2024.png. */
export function imageName(...parts) {
  const slug = parts.filter(Boolean).join('-').normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  return `data-mechanics-${slug}.png`;
}

// ---------- Painting ----------
function paintGround(ctx) {
  ctx.fillStyle = GROUND;
  ctx.fillRect(0, 0, WIDTH, HEIGHT);
  // The site's faint grid, printed on the ground.
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.025)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let x = 0.5; x < WIDTH; x += 40) { ctx.moveTo(x, 0); ctx.lineTo(x, HEIGHT); }
  for (let y = 0.5; y < HEIGHT; y += 40) { ctx.moveTo(0, y); ctx.lineTo(WIDTH, y); }
  ctx.stroke();
}

function paintHeader(ctx, title, subtitle) {
  let y = PAD;
  ctx.textBaseline = 'top';
  ctx.fillStyle = INK;
  ctx.font = `700 condensed 56px ${FONT}`;
  for (const line of wrap(ctx, title, WIDTH - 2 * PAD, 2)) {
    ctx.fillText(line, PAD, y);
    y += 60;
  }
  if (subtitle) {
    ctx.fillStyle = INK_2;
    ctx.font = `500 23px ${FONT}`;
    ctx.fillText(wrap(ctx, subtitle, WIDTH - 2 * PAD, 1)[0], PAD, y + 6);
    y += 36;
  }
  return y;
}

// Sources at the bottom left, the site's address at the bottom right. Returns the footer's top.
// Sources are never cut short: logo licences such as CC BY ask for their credit in full.
function paintFooter(ctx, sources) {
  const host = window.location.host;
  ctx.font = `700 15px ${FONT}`;
  const hostWidth = ctx.measureText(host).width;
  ctx.font = `400 15px ${FONT}`;
  const lines = sources.filter(Boolean).flatMap((text) => wrap(ctx, text, WIDTH - 2 * PAD - hostWidth - 32, 6));
  const top = HEIGHT - PAD - lines.length * 21 + 4;
  ctx.textBaseline = 'top';
  ctx.fillStyle = INK_3;
  lines.forEach((line, i) => ctx.fillText(line, PAD, top + i * 21));
  ctx.fillStyle = GOLD;
  ctx.font = `700 15px ${FONT}`;
  ctx.fillText(host, WIDTH - PAD - hostWidth, top + (lines.length - 1) * 21);
  return top;
}

// The chart well: the site's chart ground.
function paintWell(ctx, { x, y, w, h }) {
  ctx.fillStyle = WELL;
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, 18);
  ctx.fill();
}

// The gear and the name, half transparent, in the strip at the foot of the well.
export async function paintWatermark(ctx, well) {
  const logo = await loadImage(document.querySelector('link[rel="icon"]')?.href);
  ctx.save();
  ctx.globalAlpha = 0.45;
  ctx.font = `700 20px ${FONT}`;
  ctx.textBaseline = 'middle';
  const name = 'Data Mechanics';
  const width = ctx.measureText(name).width;
  const y = well.y + well.h - STRIP / 2 - 2;
  const x = well.x + well.w - 28 - width;
  if (logo) ctx.drawImage(logo, x - 40, y - 15, 30, 30);
  ctx.fillStyle = INK;
  ctx.fillText(name, x, y + 1);
  ctx.restore();
}

/** Lines of text that fit `width`, at most `max`; the last one ends in … when the text runs on. */
export function wrap(ctx, text, width, max) {
  const words = String(text).split(/\s+/).filter(Boolean);
  const lines = [];
  let line = '';
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (ctx.measureText(next).width <= width || !line) {
      line = next;
    } else {
      lines.push(line);
      line = word;
    }
  }
  if (line) lines.push(line);
  if (lines.length > max) {
    lines.length = max;
    let last = `${lines[max - 1]}…`;
    while (ctx.measureText(last).width > width && last.length > 1) last = `${last.slice(0, -2)}…`;
    lines[max - 1] = last;
  }
  return lines;
}

// ---------- Helpers ----------
async function fontsReady() {
  await Promise.all([`700 56px ${FONT}`, `500 23px ${FONT}`, `400 15px ${FONT}`, `700 18px ${MONO}`]
    .map((font) => document.fonts.load(font).catch(() => null)));
}

const images = new Map();
/** An image ready to draw, or null when it does not load. Same-origin only, so the canvas can still be saved. */
export function loadImage(src) {
  if (!src) return Promise.resolve(null);
  if (!images.has(src)) {
    images.set(src, new Promise((resolve) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => resolve(null);
      image.src = src;
    }));
  }
  return images.get(src);
}

/** Draws an image inside a box without stretching it. */
export function drawContained(ctx, image, x, y, w, h) {
  const ratio = image.naturalWidth && image.naturalHeight ? image.naturalWidth / image.naturalHeight : 1;
  const width = ratio >= w / h ? w : h * ratio;
  const height = ratio >= w / h ? w / ratio : h;
  ctx.drawImage(image, x + (w - width) / 2, y + (h - height) / 2, width, height);
}

// The chart is drawn again at twice its size, without the zoom slider.
function chartImage(chart) {
  const url = chart.getDataURL({ type: 'png', pixelRatio: SCALE, backgroundColor: 'rgba(0,0,0,0)', excludeComponents: ['dataZoom'] });
  return loadImage(url);
}

// An off-screen box the chart is drawn in: laid out like a chart well, so the chart's own HTML parts can sit in it.
function createStage(width, height) {
  const host = document.createElement('div');
  host.className = 'chart-image-stage';
  host.style.width = `${width}px`;
  host.style.height = `${height}px`;
  host.setAttribute('aria-hidden', 'true');
  const well = document.createElement('div');
  well.className = 'chart-image-stage__well';
  const element = document.createElement('div');
  element.className = 'map-canvas';
  well.append(element);
  host.append(well);
  document.body.append(host);
  return { element, remove: () => host.remove() };
}

/**
 * Hands images over: on phones the share sheet takes them all at once (several make an Instagram carousel);
 * elsewhere each one downloads, a moment apart.
 */
export async function handOver(images, title) {
  const files = await Promise.all(images.map(async ({ canvas, filename }) => {
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
    return new File([blob], filename, { type: 'image/png' });
  }));
  if (window.matchMedia('(pointer: coarse)').matches && navigator.canShare?.({ files })) {
    try {
      await navigator.share({ files, title });
      return;
    } catch (error) {
      if (error.name === 'AbortError') return;
      // The share sheet refused (it can, once the click is a few seconds old): fall back to downloads.
    }
  }
  for (const [i, file] of files.entries()) {
    if (i) await new Promise((resolve) => setTimeout(resolve, 400));
    const url = URL.createObjectURL(file);
    const link = document.createElement('a');
    link.href = url;
    link.download = file.name;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }
}

// ---------- The save buttons ----------
/** Wires a [data-save-image] button: it shows it is busy while the image is made, and never runs twice at once. */
export function bindSaveButton(button, save) {
  button?.addEventListener('click', async () => {
    if (button.disabled) return;
    button.disabled = true;
    button.classList.add('is-busy');
    try {
      await save();
    } catch (error) {
      console.error('The image could not be made.', error);
    } finally {
      button.disabled = false;
      button.classList.remove('is-busy');
    }
  });
}
