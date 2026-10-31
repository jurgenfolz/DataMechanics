// Saves a chart as a PNG: title, the site's line under it, chart, legend and source.
// It comes in two shapes (SIZES): an Instagram portrait post, or a wide image for LinkedIn, X and slides.
// The save button's menu offers both, with their sizes.
// The chart is drawn again off screen and enlarged SCALE times, so its text stays readable on a phone without crowding the image.
// gettext and interpolate are Django's, from the translation catalog base.html loads.

export const SIZES = {
  portrait: { width: 1080, height: 1350 },
  wide: { width: 1920, height: 1080 },
};
export const SCALE = 1.6;

const PAD = 56;
const WELL_INSET = 12;
const STRIP = 44;  // the room at the foot of a well that numbers a series of images ("2 / 3"), so it never covers the chart
const GROUND = '#121416';
const WELL = '#1d1f21';
const INK = '#f2f3f4';
const INK_2 = '#b6b9bd';
const INK_3 = '#8b8f94';
const GOLD = '#ffd700';
export const FONT = 'Archivo, "Helvetica Neue", Arial, sans-serif';
export const MONO = '"JetBrains Mono", ui-monospace, Menlo, Consolas, monospace';

/**
 * Builds the image and hands it over: the share sheet on phones, so Instagram is one tap away, a download elsewhere.
 * `draw(element)` draws the chart in an off-screen element and resolves, once it has finished, to
 * { chart, dispose(), paint?(ctx, x, y, scale), below?(ctx, box) }: the ECharts instance and how to remove it,
 * painting for HTML parts over it, and a legend or list for the room under it.
 * The chart modules build `draw` with their *ImageParts helpers.
 * With `aspect` the chart keeps that width / height and `below` gets the rest; otherwise `below` gets `belowHeight`.
 */
export async function saveChartImage({ title, subtitle, sources, flag, filename, draw, aspect, belowHeight = 0, size = 'portrait' }) {
  const { canvas, ctx, top, bottom, width } = await imageFrame({ title, subtitle, sources, flag, size });
  const room = bottom - top;
  const height = aspect ? Math.min(room, Math.round((width - 2 * (PAD - 16) - 2 * WELL_INSET) / aspect) + 2 * WELL_INSET)
    : room - belowHeight;
  const { well, inner } = imageWell(ctx, top, height, { width });
  const footerTop = bottom + 32;
  const stage = createStage(inner.w / SCALE, inner.h / SCALE);
  try {
    const drawn = await draw(stage.element);
    ctx.drawImage(await chartImage(drawn.chart), inner.x, inner.y, inner.w, inner.h);
    await drawn.paint?.(ctx, inner.x, inner.y, SCALE);
    const below = { x: PAD, y: well.y + well.h + 28, w: width - 2 * PAD };
    below.h = footerTop - 24 - below.y;
    if (below.h > 0) await drawn.below?.(ctx, below);
    drawn.dispose();
  } finally {
    stage.remove();
  }
  await handOver([{ canvas, filename: sizedName(filename, size) }], title);
}

/** A file name for an image in shape `size`: a wide image's name ends in -wide. */
export function sizedName(filename, size) {
  return size === 'wide' ? filename.replace(/\.png$/, '-wide.png') : filename;
}

/**
 * A new image in shape `size` (SIZES) with its frame painted: ground, header and footer.
 * The room between them runs from `top` to `bottom`; `width` and `height` are the image's.
 * `flag`, a country's 1x1 flag, goes round before the title (Politics images; a metric's images span many countries).
 */
export async function imageFrame({ title, subtitle, sources, flag, size = 'portrait' }) {
  await fontsReady();
  const { width, height } = SIZES[size];
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  paintGround(ctx, width, height);
  const gear = await loadImage(document.querySelector('link[rel="icon"]')?.href);
  const headerBottom = paintHeader(ctx, width, title, subtitle, await loadImage(flag), gear);
  const footerTop = paintFooter(ctx, width, height, sources);
  return { canvas, ctx, top: headerBottom + 36, bottom: footerTop - 32, width, height };
}

/**
 * Paints the well at `top`, `height` tall. `inner` is the room inside it.
 * The well spans an image `width` wide (a portrait one by default); a reel passes its own `width` and `pad`.
 * With `strip`, the room ends above a strip at the foot, where a series of images numbers its pages.
 */
export function imageWell(ctx, top, height, { width = SIZES.portrait.width, pad = PAD, strip = false } = {}) {
  const well = { x: pad - 16, y: top, w: width - 2 * (pad - 16), h: height };
  paintWell(ctx, well);
  const foot = strip ? STRIP : WELL_INSET;
  const inner = { x: well.x + WELL_INSET, y: well.y + WELL_INSET, w: well.w - 2 * WELL_INSET, h: well.h - WELL_INSET - foot };
  return { well, inner };
}

/** "2 / 3" at the left of the well's strip, when one subject takes several images. */
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
/** The site's ground with its faint grid, over a canvas `width` × `height` (a portrait image by default). */
export function paintGround(ctx, width = SIZES.portrait.width, height = SIZES.portrait.height) {
  ctx.fillStyle = GROUND;
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.025)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let x = 0.5; x < width; x += 40) { ctx.moveTo(x, 0); ctx.lineTo(x, height); }
  for (let y = 0.5; y < height; y += 40) { ctx.moveTo(0, y); ctx.lineTo(width, y); }
  ctx.stroke();
}

const FLAG = 52;  // the flag's diameter, about the title's height

function paintHeader(ctx, width, title, subtitle, flag, gear) {
  let y = PAD;
  if (flag) paintRoundFlag(ctx, flag, PAD, y + 29, FLAG);
  // The title's lines start right of the flag; the subtitle starts at the edge again.
  const left = flag ? PAD + FLAG + 16 : PAD;
  ctx.textBaseline = 'top';
  ctx.fillStyle = INK;
  ctx.font = `700 condensed 56px ${FONT}`;
  for (const line of wrap(ctx, title, width - PAD - left, 2)) {
    ctx.fillText(line, left, y);
    y += 60;
  }
  if (subtitle) {
    ctx.fillStyle = INK_2;
    ctx.font = `500 23px ${FONT}`;
    // The subtitle takes as many lines as it needs: it is never cut short.
    for (const line of wrap(ctx, subtitle, width - 2 * PAD, Infinity)) {
      ctx.fillText(line, PAD, y + 6);
      y += 30;
    }
    y += 6;
  }
  // The address is in the footer already, so the line under the title leaves it out.
  return paintBrandLine(ctx, PAD, y + 10, 20, gear, { address: false }) + 4;
}

// The site's name and account, and its address: the only brand on images and videos, under the title, after the gear.
const BRAND = 'Data Mechanics - @datamechanics';
const ADDRESS = 'data-mechanics.com';

/**
 * Paints the site's line at `x`, `y` (its top), in regular type `size` px tall, a little faded, the gear before it.
 * Without `address`, it ends with the account. Returns the line's foot.
 */
export function paintBrandLine(ctx, x, y, size, gear, { address = true } = {}) {
  const icon = Math.round(size * 1.4);
  ctx.save();
  ctx.globalAlpha = 0.7;
  ctx.textBaseline = 'top';
  ctx.fillStyle = INK_3;
  ctx.font = `400 ${size}px ${FONT}`;
  if (gear) ctx.drawImage(gear, x, y + size / 2 - icon / 2, icon, icon);
  ctx.fillText(address ? `${BRAND} - ${ADDRESS}` : BRAND, x + (gear ? icon + 12 : 0), y);
  ctx.restore();
  return y + Math.max(icon, size);
}

// Sources at the bottom left, the site's address at the bottom right. Returns the footer's top.
// Sources are never cut short: logo licences such as CC BY ask for their credit in full.
function paintFooter(ctx, width, height, sources) {
  const host = window.location.host;
  ctx.font = `700 15px ${FONT}`;
  const hostWidth = ctx.measureText(host).width;
  ctx.font = `400 15px ${FONT}`;
  const lines = sources.filter(Boolean).flatMap((text) => wrap(ctx, text, width - 2 * PAD - hostWidth - 32, 6));
  const top = height - PAD - lines.length * 21 + 4;
  ctx.textBaseline = 'top';
  ctx.fillStyle = INK_3;
  lines.forEach((line, i) => ctx.fillText(line, PAD, top + i * 21));
  ctx.fillStyle = GOLD;
  ctx.font = `700 15px ${FONT}`;
  ctx.fillText(host, width - PAD - hostWidth, top + (lines.length - 1) * 21);
  return top;
}

// The chart well: the site's chart ground.
function paintWell(ctx, { x, y, w, h }) {
  ctx.fillStyle = WELL;
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, 18);
  ctx.fill();
}

/** A country's flag in a circle `size` across, its left edge at `x` and its middle at `y`, with the page's faint ring. */
export function paintRoundFlag(ctx, flag, x, y, size) {
  ctx.save();
  ctx.beginPath();
  ctx.arc(x + size / 2, y, size / 2, 0, 2 * Math.PI);
  ctx.clip();
  const scale = Math.max(size / flag.naturalWidth, size / flag.naturalHeight);
  const [w, h] = [flag.naturalWidth * scale, flag.naturalHeight * scale];
  ctx.drawImage(flag, x + (size - w) / 2, y - h / 2, w, h);
  ctx.restore();
  ctx.beginPath();
  ctx.arc(x + size / 2, y, size / 2 - 0.75, 0, 2 * Math.PI);
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
  ctx.lineWidth = 1.5;
  ctx.stroke();
}

/** Lines of text that fit `width`, at most `max`; the last one ends in … when the text runs on. `first` is the first line's width. */
export function wrap(ctx, text, width, max, first = width) {
  const words = String(text).split(/\s+/).filter(Boolean);
  const lines = [];
  let line = '';
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (ctx.measureText(next).width <= (lines.length ? width : first) || !line) {
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
    const room = max === 1 ? first : width;
    while (ctx.measureText(last).width > room && last.length > 1) last = `${last.slice(0, -2)}…`;
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
  const box = containedRect(image, x, y, w, h);
  ctx.drawImage(image, box.x, box.y, box.width, box.height);
  return box;
}

/** Where an image fitted inside (x, y, w, h), centred and keeping its shape, lands: { x, y, width, height }. */
export function containedRect(image, x, y, w, h) {
  const ratio = image.naturalWidth && image.naturalHeight ? image.naturalWidth / image.naturalHeight : 1;
  const width = ratio >= w / h ? w : h * ratio;
  const height = ratio >= w / h ? w / ratio : h;
  return { x: x + (w - width) / 2, y: y + (h - height) / 2, width, height };
}

// The chart is drawn again at twice its size, without the zoom slider.
function chartImage(chart) {
  const url = chart.getDataURL({ type: 'png', pixelRatio: SCALE, backgroundColor: 'rgba(0,0,0,0)', excludeComponents: ['dataZoom'] });
  return loadImage(url);
}

/** An off-screen box a chart is drawn in, laid out like a chart well so the chart's own HTML parts can sit in it. */
export function createStage(width, height) {
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
let openMenu = null;  // the save menu that is open: one at a time

/**
 * Wires a [data-save-image] button: it opens a menu of the image's shapes, each with its size.
 * `save(size)` makes the image in the chosen shape, a key of SIZES.
 * The button shows it is busy while the image is made, and never runs twice at once.
 */
export function bindSaveButton(button, save) {
  if (!button) return;
  const menu = document.createElement('div');
  menu.className = 'save-menu';
  menu.setAttribute('role', 'menu');
  menu.hidden = true;
  const uses = { portrait: [gettext('Portrait'), gettext('Instagram')], wide: [gettext('Wide'), gettext('LinkedIn, X and slides')] };
  const items = Object.entries(SIZES).map(([key, { width, height }]) => {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'save-menu__item';
    item.setAttribute('role', 'menuitem');
    item.dataset.size = key;
    const [name, use] = uses[key];
    for (const [part, text] of [['name', name], ['size', `${width} × ${height}`], ['use', use]]) {
      const span = document.createElement('span');
      span.className = `save-menu__${part}`;
      span.textContent = text;
      item.append(span);
    }
    return item;
  });
  menu.append(...items);
  document.body.append(menu);
  button.setAttribute('aria-haspopup', 'menu');
  button.setAttribute('aria-expanded', 'false');

  // The menu hangs under the button, right edges level; above it when the window has no room below.
  function place() {
    const box = button.getBoundingClientRect();
    menu.style.right = `${document.documentElement.clientWidth - box.right}px`;
    const below = box.bottom + 6 + menu.offsetHeight <= window.innerHeight;
    menu.style.top = `${below ? box.bottom + 6 : box.top - 6 - menu.offsetHeight}px`;
  }

  function open() {
    openMenu?.();
    menu.hidden = false;
    place();
    button.setAttribute('aria-expanded', 'true');
    items[0].focus({ preventScroll: true });
    openMenu = close;
    document.addEventListener('pointerdown', outside);
    // A page that is still laying itself out scrolls a little: the menu follows its button instead of closing.
    window.addEventListener('scroll', place, { passive: true, capture: true });
    window.addEventListener('resize', place);
  }

  function close() {
    menu.hidden = true;
    button.setAttribute('aria-expanded', 'false');
    if (openMenu === close) openMenu = null;
    document.removeEventListener('pointerdown', outside);
    window.removeEventListener('scroll', place, { capture: true });
    window.removeEventListener('resize', place);
  }

  function outside(event) {
    if (!menu.contains(event.target) && !button.contains(event.target)) close();
  }

  async function run(size) {
    if (button.disabled) return;
    button.disabled = true;
    button.classList.add('is-busy');
    try {
      await save(size);
    } catch (error) {
      console.error('The image could not be made.', error);
    } finally {
      button.disabled = false;
      button.classList.remove('is-busy');
    }
  }

  button.addEventListener('click', () => (menu.hidden ? open() : close()));
  menu.addEventListener('click', (event) => {
    const item = event.target.closest('[data-size]');
    if (!item) return;
    close();
    button.focus({ preventScroll: true });
    run(item.dataset.size);
  });
  menu.addEventListener('keydown', (event) => {
    const at = items.indexOf(document.activeElement);
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      items[(at + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length].focus();
    } else if (event.key === 'Escape' || event.key === 'Tab') {
      close();
      if (event.key === 'Escape') button.focus({ preventScroll: true });
    }
  });
}
