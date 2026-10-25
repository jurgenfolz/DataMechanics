"""Deaths by state in World War II, from Wikipedia's table "World War II casualties". Writes ww2.deaths_state.

The table gives each figure as one number or a range ("2,000,000 to 3,750,000"); both ends are kept.
A cell that says its deaths are counted with another state is left empty, so no death is shown twice.
"""

import re
from html.parser import HTMLParser

from conflicts.models import Deaths, State
from providers import http
from providers.load import Source, replace_rows

REVISION = 1381850968  # 2026-10-25
TITLE = 'World War II casualties'
URL = f'https://en.wikipedia.org/w/api.php?action=parse&oldid={REVISION}&prop=text&formatversion=2&format=json'
SOURCE = Source(
    name='Wikipedia, "World War II casualties"',
    url=f'https://en.wikipedia.org/w/index.php?title=World_War_II_casualties&oldid={REVISION}',
    updated='2026-10-25',
)

# The table's row names (in bold) -> codes in ww2.state. A row not listed here stops the load, so none is lost.
STATES = {
    'Albania': 'al', 'Australia': 'au', 'Belgium': 'be', 'Brazil': 'br', 'Bulgaria': 'bg', 'Burma': 'mm',
    'Canada': 'ca', 'China': 'cn', 'Cuba': 'cu', 'Czechoslovakia': 'cs', 'Denmark': 'dk', 'Dutch East Indies': 'id',
    'Egypt': 'eg', 'Estonia': 'ee', 'Ethiopia': 'et', 'Finland': 'fi', 'France': 'fr', 'French Indochina': 'vn',
    'Germany': 'de', 'Greece': 'gr', 'Guam': 'gu', 'Hungary': 'hu', 'Iceland': 'is', 'India': 'in', 'Iraq': 'iq',
    'Ireland': 'ie', 'Italy': 'it', 'Japan': 'jp', 'Korea': 'kr', 'Latvia': 'lv', 'Lithuania': 'lt',
    'Luxembourg': 'lu', 'Malaya & Singapore': 'my', 'Malta': 'mt', 'Mexico': 'mx', 'Mongolia': 'mn', 'Nauru': 'nr',
    'Nepal': 'np', 'Netherlands': 'nl', 'Newfoundland': 'nf', 'New Zealand': 'nz', 'Norway': 'no',
    'Papua and New Guinea': 'pg', 'Philippines': 'ph', 'Poland': 'pl', 'Portuguese Timor': 'tl', 'Romania': 'ro',
    'Ruanda-Urundi': 'rw', 'South Africa': 'za', 'South Seas Mandate': 'mp', 'Soviet Union': 'su', 'Spain': 'es',
    'Sweden': 'se', 'Switzerland': 'ch', 'Thailand': 'th', 'Turkey': 'tr', 'United Kingdom': 'gb',
    'United States': 'us', 'Yugoslavia': 'yu',
}
# Rows with no deaths of their own (Austria is counted with Germany) and the table's sums.
SKIPPED = {'Austria', 'Other states and territories', 'Approx. totals'}

# Column order of the table.
COLUMNS = ['label', 'population', 'military', 'civilian', 'famine', 'total', 'percent', 'average_percent', 'wounded']


def run():
    html = http.get_json(URL)['parse']['text']
    rows = parse_table(html)
    known = set(State.objects.values_list('code', flat=True))
    objects = []
    for row in rows:
        label = row['label']
        if label in SKIPPED:
            continue
        if label not in STATES:
            raise ValueError(f'Unknown row in the table: {label!r}. Add it to STATES or SKIPPED.')
        if STATES[label] not in known:
            raise ValueError(f'{STATES[label]!r} is not in ww2.state: run curated.ww2_states first.')
        fields = {}
        for column in ('military', 'civilian', 'famine', 'total'):
            fields[f'{column}_low'], fields[f'{column}_high'] = estimate(row[column])
        objects.append(Deaths(state_id=STATES[label], label=label, note=row['note'],
                              population=estimate(row['population'])[0], **fields))
    return replace_rows(Deaths, objects, SOURCE)


def estimate(text):
    """(low, high) from a cell: "30,000" -> (30000, 30000); "2,000,000 to 3,750,000+" -> both ends.

    Only the figure or range the cell starts with counts; what follows it is a remark.
    "319,200 to 341,000 Italian nationals and c. 20,000 Africans" gives (319200, 341000).
    A cell without a figure, or one that says its deaths are included elsewhere, gives (None, None).
    """
    if 'includ' in text.lower():
        return None, None
    match = re.match(r'(?:c\.|~)?\s*(\d[\d,]*)\+?(?:\s*(?:to|and|–)\s*(\d[\d,]*))?', text.strip())
    if not match:
        return None, None
    numbers = [int(n.replace(',', '')) for n in match.groups() if n]
    return min(numbers), max(numbers)


def parse_table(html):
    """The first sortable table of the page: one dict per country row, with each cell's text under COLUMNS."""
    parser = _TableParser()
    parser.feed(html)
    rows = []
    for cells in parser.rows:
        if len(cells) < 2 or not cells[0]['bold']:
            continue  # the header row
        texts = []
        for cell in cells:
            texts.extend([cell['text']] * cell['colspan'])
        texts += [''] * (len(COLUMNS) - len(texts))
        row = dict(zip(COLUMNS, texts))
        row['label'] = cells[0]['bold']
        row['note'] = _note(cells[0]['text'], cells[0]['bold'])
        rows.append(row)
    return rows


def _note(text, label):
    """What the first cell says after the row's name, e.g. "within 1939 borders"."""
    rest = text.replace(label, '', 1).strip()
    return rest.strip('()').strip() if rest.startswith('(') and rest.endswith(')') else rest


class _TableParser(HTMLParser):
    """Collects the cells of the first table whose class starts with "wikitable sortable".

    Footnote markers (<sup>), styles and hidden elements are left out; a line break becomes a space.
    """

    def __init__(self):
        super().__init__()
        self.rows, self._depth, self._done = [], 0, False
        self._cell = None
        self._skip_tag, self._skip_depth = None, 0
        self._bold = 0

    def handle_starttag(self, tag, attrs):
        if self._done:
            return
        attrs = dict(attrs)
        if self._skip_tag:
            self._skip_depth += tag == self._skip_tag
            return
        if tag == 'table':
            if self._depth or (attrs.get('class') or '').startswith('wikitable sortable'):
                self._depth += 1
            return
        if not self._depth:
            return
        if tag in ('sup', 'style') or 'display:none' in (attrs.get('style') or '').replace(' ', ''):
            self._skip_tag, self._skip_depth = tag, 1
        elif tag == 'tr':
            self.rows.append([])
        elif tag in ('td', 'th') and self.rows:
            self._cell = {'text': '', 'bold': '', 'colspan': int(attrs.get('colspan') or 1)}
            self.rows[-1].append(self._cell)
        elif tag == 'br' and self._cell:
            self._cell['text'] += ' '
        elif tag == 'b':
            self._bold += 1

    def handle_endtag(self, tag):
        if self._done or not self._depth:
            return
        if self._skip_tag:
            if tag == self._skip_tag:
                self._skip_depth -= 1
                if not self._skip_depth:
                    self._skip_tag = None
            return
        if tag == 'table':
            self._depth -= 1
            self._done = not self._depth
        elif tag in ('td', 'th') and self._cell:
            self._cell['text'] = ' '.join(self._cell['text'].split())
            self._cell['bold'] = ' '.join(self._cell['bold'].split())
            self._cell = None
        elif tag == 'b':
            self._bold -= 1

    def handle_data(self, data):
        if self._done or not self._depth or self._skip_tag or self._cell is None:
            return
        self._cell['text'] += data
        if self._bold:
            self._cell['bold'] += data
