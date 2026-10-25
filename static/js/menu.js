// The header's menus. On wide screens "Metrics" opens the list of categories under it; on phones the menu button opens
// the whole navigation as a panel. Each closes on Escape, on a press outside it, or when one of its links is followed.
function disclosure(button, root, openClass) {
  const isOpen = () => button.getAttribute('aria-expanded') === 'true';
  const set = (open) => {
    root.classList.toggle(openClass, open);
    button.setAttribute('aria-expanded', String(open));
  };
  button.addEventListener('click', () => set(!isOpen()));
  document.addEventListener('pointerdown', (event) => {
    if (isOpen() && !root.contains(event.target)) set(false);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || !isOpen()) return;
    set(false);
    button.focus();
  });
  // "About" jumps down this page, so the menu has to close behind it.
  root.addEventListener('click', (event) => {
    if (event.target.closest('a')) set(false);
  });
}

const header = document.querySelector('[data-site-header]');
disclosure(header.querySelector('[data-nav-toggle]'), header, 'is-nav-open');
const menu = header.querySelector('[data-menu]');
disclosure(menu.querySelector('[data-menu-button]'), menu, 'is-open');
