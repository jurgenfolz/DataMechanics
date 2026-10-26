"""The Austrian Parliament's open data at parlament.gv.at, under CC BY 4.0: the members in office of each house.

The Parliament's list API answers a POST with every member who matches a filter; the filter must name both genders,
or it matches nobody. Cells that name a club or party hold HTML, e.g. <span title="Freiheitlicher Parlamentsklub">FPÖ</span>.
"""

import html
import json
import re
import urllib.request

FILTER = 'https://www.parlament.gv.at/Filter/api/json/post?jsMode=EVAL&FBEZ={list}&listeId={id}&showAll=true'
HEADERS = {'User-Agent': 'DataMechanics/1.0 (https://data-mechanics.com)', 'Content-Type': 'application/json',
           'Accept': 'application/json'}
EVERYONE = {'M': ['M'], 'W': ['W']}


def members(name, number):
    """The rows of one of the Parliament's lists, e.g. ('WFW_002', '10002') for the Nationalrat's members in office."""
    url = FILTER.format(list=name, id=number)
    request = urllib.request.Request(url, data=json.dumps(EVERYONE).encode(), headers=HEADERS, method='POST')
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)['rows']


def text(cell):
    """A cell's text, without its HTML: '<span title="…">FPÖ</span>' -> 'FPÖ'."""
    return html.unescape(re.sub(r'<[^>]+>', '', cell or '')).strip()
