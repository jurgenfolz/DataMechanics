"""Reads a sheet of an .ods file with Python's standard library, for the tools that build data/ from spreadsheets.
Its `rows` works like tools/spreadsheet.rows, so a tool reads either kind of file the same way.
"""

import xml.etree.ElementTree as ET
import zipfile

TABLE = '{urn:oasis:names:tc:opendocument:xmlns:table:1.0}'
OFFICE = '{urn:oasis:names:tc:opendocument:xmlns:office:1.0}'
TEXT = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'


def rows(path, sheet=None):
    """A sheet's rows (the first, or the one named `sheet`), as lists of cell texts.
    None stands for an empty cell, and a number is as the file writes it in `office:value`.
    Trailing empty cells and rows are left out, and a repeated empty row stands once.
    """
    content = ET.fromstring(zipfile.ZipFile(path).read('content.xml'))
    tables = list(content.iter(f'{TABLE}table'))
    table = tables[0] if sheet is None else next(table for table in tables if table.get(f'{TABLE}name') == sheet)
    result = []
    for row in table.iter(f'{TABLE}table-row'):
        cells = []
        for cell in row:
            if cell.tag not in (f'{TABLE}table-cell', f'{TABLE}covered-table-cell'):
                continue
            cells.extend([_value(cell)] * int(cell.get(f'{TABLE}number-columns-repeated', 1)))
        while cells and cells[-1] is None:
            cells.pop()
        result.extend([cells] * (int(row.get(f'{TABLE}number-rows-repeated', 1)) if cells else 1))
    while result and not result[-1]:
        result.pop()
    return result


def _value(cell):
    """A cell's number as the file writes it, else its text, else None."""
    kind = cell.get(f'{OFFICE}value-type')
    if kind in ('float', 'percentage', 'currency'):
        return cell.get(f'{OFFICE}value')
    text = '\n'.join(''.join(paragraph.itertext()) for paragraph in cell.iter(f'{TEXT}p'))
    return text if text else None
