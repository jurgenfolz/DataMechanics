"""Downloads shared by every provider."""

import json
from urllib.request import Request, urlopen

_HEADERS = {'User-Agent': 'DataMechanics ETL (+https://data-mechanics.com)'}


def get_bytes(url, timeout=180):
    with urlopen(Request(url, headers=_HEADERS), timeout=timeout) as response:
        return response.read()


def get_json(url, timeout=180):
    return json.loads(get_bytes(url, timeout))


def get_text(url, encoding='utf-8', timeout=180):
    return get_bytes(url, timeout).decode(encoding)
