"""Downloads the flags of Brazil's 26 states and the Federal District from Wikimedia Commons.

The files to fetch are in data/politics/brazil/state_flags.csv: one row per state, with the Commons file name,
its page, its licence and its author.
Each flag is saved as media/flags/states/<code>.svg, where the code is the state's ISO 3166-2 code (BR-SP).

Downloaded files are untrusted.
Each one lands in a temporary folder first and is checked: it must be an SVG and small.
Only then does it replace the file in media/.
Standard library only.

Usage:
    python tools/brazil_state_flags.py
"""

import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / 'data' / 'politics' / 'brazil' / 'state_flags.csv'
FLAGS = ROOT / 'media' / 'flags' / 'states'
API = 'https://commons.wikimedia.org/w/api.php'
# Commons refuses requests without a User-Agent that names the client.
HEADERS = {'User-Agent': 'DataMechanics/1.0 (https://data-mechanics.com)'}
# Rio de Janeiro's flag is 344 KB (its coat of arms is 265 paths); every other flag is under 300 KB.
MAX_BYTES = 400 * 1024


def fetch(url):
    """The bytes at `url`."""
    with urlopen(Request(url, headers=HEADERS)) as response:
        return response.read()


def file_urls(names):
    """The download address of each Commons file in `names`, by its name."""
    query = {'action': 'query', 'prop': 'imageinfo', 'iiprop': 'url', 'format': 'json',
             'titles': '|'.join(f'File:{name}' for name in names)}
    data = json.loads(fetch(f'{API}?{urlencode(query)}'))['query']
    # The API normalises titles (an underscore for a space), and answers by the normalised one.
    normalised = {entry['to']: entry['from'] for entry in data.get('normalized', [])}
    urls = {}
    for page in data['pages'].values():
        title = normalised.get(page['title'], page['title'])
        if 'imageinfo' not in page:
            sys.exit(f'Commons has no file named {title}')
        urls[title.removeprefix('File:')] = page['imageinfo'][0]['url']
    return urls


def kilobytes(path):
    """The size of the file at `path` in KB, rounded up."""
    return (path.stat().st_size + 1023) // 1024


def check(path):
    """Stops the script unless the file at `path` is a small SVG."""
    size = path.stat().st_size
    if size > MAX_BYTES:
        sys.exit(f'{path.name} is {size:,} bytes, over the limit of {MAX_BYTES:,}')
    head = path.read_bytes()[:64].lstrip(b'\xef\xbb\xbf').lstrip()
    if not head.startswith((b'<?xml', b'<svg')):
        sys.exit(f'{path.name} is not an SVG: it starts with {head[:20]!r}')


def main():
    with open(CSV, newline='', encoding='utf-8') as file:
        rows = [row for row in csv.DictReader(file) if row['file']]
    urls = file_urls([row['file'] for row in rows])
    FLAGS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        for row in rows:
            name = f"{row['code']}.svg"
            temporary = Path(folder) / name
            temporary.write_bytes(fetch(urls[row['file']]))
            check(temporary)
            shutil.move(temporary, FLAGS / name)
            print(f'{name}: {kilobytes(FLAGS / name)} KB')
    print(f'{len(rows)} flags in {FLAGS}')


if __name__ == '__main__':
    main()
