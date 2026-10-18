// Header search: suggests metrics as you type. Without JavaScript the form still submits to /metrics/?q=.
const form = document.querySelector('[data-search]');
const input = form?.querySelector('input');
const list = form?.querySelector('[role="listbox"]');
const index = JSON.parse(document.getElementById('search-index')?.textContent || '[]');
const MAX_RESULTS = 6;

let matches = [];
let active = -1;

function find(query) {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return [];
  return index.filter((metric) => words.every((word) => metric.text.includes(word))).slice(0, MAX_RESULTS);
}

function option(metric, i) {
  const item = document.createElement('li');
  item.id = `site-search-option-${i}`;
  item.setAttribute('role', 'option');
  item.setAttribute('aria-selected', String(i === active));
  item.className = 'search__option';
  const title = document.createElement('strong');
  const summary = document.createElement('span');
  const category = document.createElement('em');
  title.textContent = metric.title;
  summary.textContent = metric.summary;
  category.textContent = metric.category;
  item.append(title, category, summary);
  item.addEventListener('mousedown', (event) => {
    event.preventDefault();
    window.location.href = metric.url;
  });
  return item;
}

function render() {
  const query = input.value.trim();
  matches = find(query);
  if (!query) {
    close();
    return;
  }
  if (!matches.length) {
    const empty = document.createElement('li');
    empty.className = 'search__empty';
    empty.textContent = `No metric matches "${query}". Press Enter to search all.`;
    list.replaceChildren(empty);
  } else {
    list.replaceChildren(...matches.map(option));
  }
  list.hidden = false;
  input.setAttribute('aria-expanded', 'true');
  input.setAttribute('aria-activedescendant', active >= 0 ? `site-search-option-${active}` : '');
}

function close() {
  active = -1;
  list.hidden = true;
  input.setAttribute('aria-expanded', 'false');
  input.removeAttribute('aria-activedescendant');
}

if (form && input && list) {
  input.addEventListener('input', () => {
    active = -1;
    render();
  });
  input.addEventListener('focus', () => input.value.trim() && render());
  input.addEventListener('blur', close);
  input.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      if (!matches.length) return;
      event.preventDefault();
      const step = event.key === 'ArrowDown' ? 1 : -1;
      active = (active + step + matches.length) % matches.length;
      render();
    } else if (event.key === 'Enter' && active >= 0) {
      event.preventDefault();
      window.location.href = matches[active].url;
    } else if (event.key === 'Escape') {
      close();
    }
  });
  // "/" focuses the search from anywhere, as on most data sites.
  document.addEventListener('keydown', (event) => {
    if (event.key === '/' && !event.target.closest('input, textarea, select')) {
      event.preventDefault();
      input.focus();
    }
  });
}
