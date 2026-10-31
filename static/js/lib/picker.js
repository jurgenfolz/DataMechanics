// A filter: a button that opens a searchable list, each item with its image and a check.
// The metric pages and the WW2 page pick countries with it, by flag; the party compass picks parties, by logo.
// An option is { id, name, image, label?, world?, meta?, svg?, color? }: `label` is how the button names it, the name
// by default. An option with `svg` shows that icon in `color` instead of its image (the world events), and `meta`
// (an event's year) follows its name in grey; the search matches it too.
// A `world` option (World on a metric page) is listed like the others but does not count towards `max`.
// With `allLabel`, the button says it ("All parties") while every option is picked.
// With `single`, picking an option closes the list: the page keeps one choice (the Compare page's country).
// gettext, ngettext and interpolate are Django's, from the translation catalog base.html loads.
import { escapeHtml } from './format.js';

export function createPicker(root, {
  onToggle, max = Infinity, imageClass = 'flag', emptyLabel = gettext('Choose countries'), noMatch = gettext('No country matches.'),
  allLabel = '', single = false,
}) {
  const button = root.querySelector('[data-picker-button]');
  const label = root.querySelector('[data-picker-label]');
  const panel = root.querySelector('[data-picker-panel]');
  const search = root.querySelector('[data-picker-search]');
  const list = root.querySelector('[data-picker-list]');
  const hint = root.querySelector('[data-picker-hint]');

  let options = [];  // [{id, name, image, label, world}]
  let selected = new Set();
  let visible = [];
  let active = 0;

  function countedSelected() {
    return [...selected].filter((id) => !options.find((o) => o.id === id)?.world).length;
  }

  function renderList() {
    const query = search.value.trim().toLowerCase();
    visible = options.filter((o) => !query || o.name.toLowerCase().includes(query) || o.id.toLowerCase() === query
      || (o.meta && o.meta.toLowerCase().includes(query)));
    active = Math.min(active, Math.max(visible.length - 1, 0));
    const full = countedSelected() >= max;
    list.innerHTML = visible.map((o, i) => {
      const isSelected = selected.has(o.id);
      const disabled = !isSelected && !o.world && full;
      return `<li id="picker-${o.id}" role="option" class="picker__option${o.world ? ' picker__option--world' : ''}${i === active ? ' is-active' : ''}"`
        + ` aria-selected="${isSelected}" aria-disabled="${disabled}" data-id="${o.id}">`
        + `<span class="picker__check" aria-hidden="true"></span>`
        + (o.svg ? `<span class="picker__icon" style="color:${escapeHtml(o.color)}">${o.svg}</span>`
          : `<img class="${imageClass}" src="${escapeHtml(o.image)}" alt="" loading="lazy">`)
        + `<span class="picker__name">${escapeHtml(o.name)}${o.meta ? `<em class="picker__meta">${escapeHtml(o.meta)}</em>` : ''}</span></li>`;
    }).join('') || `<li class="picker__hint">${escapeHtml(noMatch)}</li>`;
    search.setAttribute('aria-activedescendant', visible[active] ? `picker-${visible[active].id}` : '');
    // Without a limit there is nothing to say.
    hint.hidden = max === Infinity;
    if (hint.hidden) return;
    hint.textContent = interpolate(full
      ? ngettext('%s country is the limit. Remove one to add another.', '%s countries is the limit. Remove one to add another.', max)
      : ngettext('Pick up to %s country.', 'Pick up to %s countries.', max), [max]);
  }

  function renderLabel() {
    const names = options.filter((o) => selected.has(o.id)).map((o) => (o.label ?? o.name));
    if (allLabel && names.length > 2 && names.length === options.length) {
      label.textContent = allLabel;
      return;
    }
    label.textContent = names.length ? (names.length > 2 ? `${names.slice(0, 2).join(', ')} +${names.length - 2}` : names.join(', ')) : emptyLabel;
  }

  function toggle(id) {
    const option = options.find((o) => o.id === id);
    if (!option) return;
    if (!selected.has(id) && !option.world && countedSelected() >= max) return;
    onToggle(id);
    if (single) close();
  }

  function open() {
    panel.hidden = false;
    // The panel hangs from the button's right edge, unless that would push it off the screen's left edge.
    panel.classList.remove('is-left');
    if (panel.getBoundingClientRect().left < 8) panel.classList.add('is-left');
    button.setAttribute('aria-expanded', 'true');
    search.value = '';
    active = 0;
    renderList();
    search.focus();
    document.addEventListener('pointerdown', outside);
  }

  function close({ focusButton = true } = {}) {
    panel.hidden = true;
    button.setAttribute('aria-expanded', 'false');
    document.removeEventListener('pointerdown', outside);
    if (focusButton) button.focus();
  }

  function outside(event) {
    if (!root.contains(event.target)) close({ focusButton: false });
  }

  button.addEventListener('click', () => (panel.hidden ? open() : close()));
  search.addEventListener('input', () => { active = 0; renderList(); });
  search.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      active = (active + (event.key === 'ArrowDown' ? 1 : -1) + visible.length) % Math.max(visible.length, 1);
      renderList();
      list.querySelector('.is-active')?.scrollIntoView({ block: 'nearest' });
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (visible[active]) toggle(visible[active].id);
    } else if (event.key === 'Escape') {
      close();
    }
  });
  list.addEventListener('click', (event) => {
    const item = event.target.closest('[data-id]');
    if (item) toggle(item.dataset.id);
  });

  return {
    root,
    setOptions(next) { options = next; renderList(); renderLabel(); },
    setSelected(ids) { selected = new Set(ids); if (!panel.hidden) renderList(); renderLabel(); },
  };
}
