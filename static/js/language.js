// The language links carry the page's current state (series, year, countries) along, which scripts keep in the URL.
for (const link of document.querySelectorAll('[data-language]')) {
  link.addEventListener('click', () => {
    link.search = window.location.search;
  });
}
