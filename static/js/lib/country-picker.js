// The country filter: a button that opens a searchable list with flags. World is listed first, like a country.
import { escapeHtml } from './format.js';

export function createCountryPicker(root, { max, onToggle }) {
  const button = root.querySelector('[data-picker-button]');
  const label = root.querySelector('[data-picker-label]');
  const panel = root.querySelector('[data-picker-panel]');
  const search = root.querySelector('[data-picker-search]');
  const list = root.querySelector('[data-picker-list]');
  const hint = root.querySelector('[data-picker-hint]');

  let options = [];  // [{iso3, name, flag, world}]
  let selected = new Set();
  let visible = [];
  let active = 0;

  function countrySelectedCount() {
    return [...selected].filter((iso3) => !options.find((o) => o.iso3 === iso3)?.world).length;
  }

  function renderList() {
    const query = search.value.trim().toLowerCase();
    visible = options.filter((o) => !query || o.name.toLowerCase().includes(query) || o.iso3.toLowerCase() === query);
    active = Math.min(active, Math.max(visible.length - 1, 0));
    const full = countrySelectedCount() >= max;
    list.innerHTML = visible.map((o, i) => {
      const isSelected = selected.has(o.iso3);
      const disabled = !isSelected && !o.world && full;
      return `<li id="picker-${o.iso3}" role="option" class="picker__option${o.world ? ' picker__option--world' : ''}${i === active ? ' is-active' : ''}"`
        + ` aria-selected="${isSelected}" aria-disabled="${disabled}" data-iso3="${o.iso3}">`
        + `<span class="picker__check" aria-hidden="true"></span>`
        + `<img class="flag" src="${escapeHtml(o.flag)}" alt="" loading="lazy">`
        + `<span>${escapeHtml(o.name)}</span></li>`;
    }).join('') || '<li class="picker__hint">No country matches.</li>';
    search.setAttribute('aria-activedescendant', visible[active] ? `picker-${visible[active].iso3}` : '');
    hint.textContent = full ? `${max} countries is the limit. Remove one to add another.` : `Pick up to ${max} countries.`;
  }

  function renderLabel() {
    const names = options.filter((o) => selected.has(o.iso3)).map((o) => (o.world ? 'World' : o.name));
    label.textContent = names.length ? (names.length > 2 ? `${names.slice(0, 2).join(', ')} +${names.length - 2}` : names.join(', ')) : 'Choose countries';
  }

  function toggle(iso3) {
    const option = options.find((o) => o.iso3 === iso3);
    if (!option) return;
    if (!selected.has(iso3) && !option.world && countrySelectedCount() >= max) return;
    onToggle(iso3);
  }

  function open() {
    panel.hidden = false;
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
      if (visible[active]) toggle(visible[active].iso3);
    } else if (event.key === 'Escape') {
      close();
    }
  });
  list.addEventListener('click', (event) => {
    const item = event.target.closest('[data-iso3]');
    if (item) toggle(item.dataset.iso3);
  });

  return {
    setOptions(next) { options = next; renderList(); renderLabel(); },
    setSelected(ids) { selected = new Set(ids); if (!panel.hidden) renderList(); renderLabel(); },
  };
}
