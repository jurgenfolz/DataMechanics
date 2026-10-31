// A filter like lib/picker.js, for a tree: a searchable list where each item has a box.
// A parent's box checks or clears every item inside it; it shows a tick when all of them are checked, a dash when some are.
// A node is { key, name, children }. The selection is the set of leaves' keys: a parent is chosen through its leaves.
// The Crime tab picks kinds of offence with it.
// gettext is Django's, from the translation catalog base.html loads.
import { escapeHtml } from './format.js';

/** The keys of the leaves inside `node`, or its own key when it has none. */
export function leaves(node) {
  return node.children.length ? node.children.flatMap(leaves) : [node.key];
}

/** The fewest nodes that make up the chosen leaves: a node all of whose leaves are chosen stands for them. */
export function cover(node, chosen) {
  const inside = leaves(node);
  if (inside.every((key) => chosen.has(key))) return [node];
  return node.children.flatMap((child) => cover(child, chosen));
}

/**
 * Wires the picker inside `root` to `tree`. `onChange(leaves)` gets the new set of chosen leaves.
 * `describe(leaves)` names the choice on the button.
 */
export function createTreePicker(root, { tree, onChange, describe, noMatch = gettext('Nothing matches.') }) {
  const button = root.querySelector('[data-picker-button]');
  const label = root.querySelector('[data-picker-label]');
  const panel = root.querySelector('[data-picker-panel]');
  const search = root.querySelector('[data-picker-search]');
  const list = root.querySelector('[data-picker-list]');
  const id = list.id;

  // Every node in the order the list shows them, with its depth and the nodes above it.
  const rows = [];
  (function walk(node, depth, above) {
    rows.push({ node, depth, above, inside: leaves(node) });
    for (const child of node.children) walk(child, depth + 1, [...above, node]);
  }(tree, 0, []));
  const byKey = new Map(rows.map((row) => [row.node.key, row]));

  let chosen = new Set();
  let visible = rows;
  let active = 0;

  const checked = (row) => {
    const count = row.inside.filter((key) => chosen.has(key)).length;
    return count === row.inside.length ? 'true' : count ? 'mixed' : 'false';
  };

  function renderList() {
    const query = search.value.trim().toLowerCase();
    // A search keeps the nodes it matches and the nodes above them, so each match is seen in its place.
    const matches = new Set();
    for (const row of rows) {
      if (query && !row.node.name.toLowerCase().includes(query)) continue;
      matches.add(row);
      for (const node of row.above) matches.add(byKey.get(node.key));
    }
    visible = rows.filter((row) => matches.has(row));
    active = Math.min(active, Math.max(visible.length - 1, 0));
    list.innerHTML = visible.map((row, i) => `<li id="${id}-${i}" role="treeitem" class="picker__option picker__option--tree${i === active ? ' is-active' : ''}"`
      + ` style="--depth:${row.depth}" aria-level="${row.depth + 1}" aria-checked="${checked(row)}" data-key="${escapeHtml(row.node.key)}">`
      + `<span class="picker__check" aria-hidden="true"></span><span>${escapeHtml(row.node.name)}</span></li>`).join('')
      || `<li class="picker__hint">${escapeHtml(noMatch)}</li>`;
    search.setAttribute('aria-activedescendant', visible[active] ? `${id}-${active}` : '');
  }

  // A node whose leaves are all chosen clears them; any other node chooses them all.
  function toggle(key) {
    const row = byKey.get(key);
    const next = new Set(chosen);
    const all = checked(row) === 'true';
    for (const leaf of row.inside) {
      if (all) next.delete(leaf);
      else next.add(leaf);
    }
    onChange(next);
  }

  function open() {
    panel.hidden = false;
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
      if (visible[active]) toggle(visible[active].node.key);
    } else if (event.key === 'Escape') {
      close();
    }
  });
  list.addEventListener('click', (event) => {
    const item = event.target.closest('[data-key]');
    if (item) toggle(item.dataset.key);
  });

  return {
    setSelected(keys) {
      chosen = new Set(keys);
      if (!panel.hidden) renderList();
      label.textContent = describe(chosen);
    },
  };
}
