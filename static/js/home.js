// Home page: the spotlight carousel (its map recolours for each metric) and the "Latest data" strip.
import { createWorldMap } from './lib/world-map.js';

const units = JSON.parse(document.getElementById('units').textContent);
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

// ---------- Spotlight ----------
const spotlight = document.querySelector('[data-spotlight]');
if (spotlight) {
  const slides = [...spotlight.querySelectorAll('[data-slide]')];
  const icon = spotlight.querySelector('[data-spotlight-icon]');
  const index = spotlight.querySelector('[data-index]');
  const caption = spotlight.querySelector('[data-spotlight-caption]');
  const source = spotlight.querySelector('[data-spotlight-source]');
  const prev = spotlight.querySelector('[data-prev]');
  const next = spotlight.querySelector('[data-next]');
  // One map for all slides: it moves into the slide on show.
  const mapBox = spotlight.querySelector('[data-spotlight-map-box]');
  const map = createWorldMap(spotlight.querySelector('[data-spotlight-map]'), { units });
  const cache = new Map();
  let current = 0;

  const load = (slug) => {
    if (!cache.has(slug)) cache.set(slug, fetch(`/metrics/${slug}/data.json`).then((response) => response.json()));
    return cache.get(slug);
  };

  async function drawMap(slug) {
    const data = await load(slug);
    if (slides[current].dataset.slug !== slug) return;  // the visitor moved on while it loaded
    await map.render(data, data.mapYear);
    caption.textContent = data.better
      ? `${data.label}, ${data.mapYear}. Red is worse, blue is better; grey is the median country.`
      : `${data.label}, ${data.mapYear}. Brighter blue is higher.`;
  }

  function show(i) {
    current = (i + slides.length) % slides.length;
    slides.forEach((slide, n) => { slide.hidden = n !== current; });
    const slide = slides[current];
    if (!reduceMotion.matches) {
      slide.classList.remove('is-entering');
      void slide.offsetWidth;
      slide.classList.add('is-entering');
    }
    slide.querySelector('[data-map-slot]').append(mapBox);
    source.textContent = slide.dataset.source;
    source.href = slide.dataset.sourceUrl;
    icon.innerHTML = slide.querySelector('template[data-icon]').innerHTML;
    index.textContent = current + 1;
    drawMap(slide.dataset.slug);
  }

  prev.addEventListener('click', () => show(current - 1));
  next.addEventListener('click', () => show(current + 1));
  spotlight.addEventListener('keydown', (event) => {
    if (event.target.closest('a, button') && !event.target.closest('[data-prev], [data-next]')) return;
    if (event.key === 'ArrowLeft') show(current - 1);
    if (event.key === 'ArrowRight') show(current + 1);
  });
  slides[0].querySelector('[data-map-slot]').append(mapBox);
  drawMap(slides[0].dataset.slug);
  // Warm the next slide's data so the first click recolours at once.
  if (slides[1]) load(slides[1].dataset.slug);
}

// ---------- Latest data strip ----------
const strip = document.querySelector('[data-strip]');
if (strip) {
  const prev = document.querySelector('[data-strip-prev]');
  const next = document.querySelector('[data-strip-next]');
  const step = () => strip.clientWidth * 0.8;
  const behavior = () => (reduceMotion.matches ? 'auto' : 'smooth');
  const update = () => {
    prev.disabled = strip.scrollLeft <= 2;
    next.disabled = strip.scrollLeft + strip.clientWidth >= strip.scrollWidth - 2;
  };
  prev.addEventListener('click', () => strip.scrollBy({ left: -step(), behavior: behavior() }));
  next.addEventListener('click', () => strip.scrollBy({ left: step(), behavior: behavior() }));
  strip.addEventListener('scroll', update, { passive: true });
  new ResizeObserver(update).observe(strip);
}
