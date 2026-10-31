"""Reads a sheet of an .xlsx file with Python's standard library, for the tools that build data/ from spreadsheets."""

import re
import xml.etree.ElementTree as ET
import zipfile

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
RELATIONSHIP = '{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'


def rows(path, sheet=None):
    """A sheet's rows (the first, or the one named `sheet`), as lists of cell texts: None for an empty cell, numbers as the
    file writes them.
    """
    book = zipfile.ZipFile(path)
    names = book.namelist()
    strings = []
    if 'xl/sharedStrings.xml' in names:
        strings = [''.join(t.text or '' for t in item.iter(f'{{{NS["m"]}}}t'))
                   for item in ET.fromstring(book.read('xl/sharedStrings.xml')).findall('m:si', NS)]
    result = []
    for row in ET.fromstring(book.read(_sheet(book, sheet))).iter(f'{{{NS["m"]}}}row'):
        cells = {}
        for cell in row.findall('m:c', NS):
            if cell.get('t') == 'inlineStr':
                value = ''.join(t.text or '' for t in cell.iter(f'{{{NS["m"]}}}t'))
            else:
                found = cell.find('m:v', NS)
                value = None if found is None else (strings[int(found.text)] if cell.get('t') == 's' else found.text)
            cells[_column(cell.get('r'))] = value
        result.append([cells.get(i) for i in range(max(cells) + 1)] if cells else [])
    return result


def _sheet(book, name):
    """The file inside the book that holds the sheet called `name` (or the first sheet), through the workbook's relationships."""
    workbook = ET.fromstring(book.read('xl/workbook.xml'))
    targets = {rel.get('Id'): rel.get('Target')
               for rel in ET.fromstring(book.read('xl/_rels/workbook.xml.rels')).iter(RELATIONSHIP)}
    sheets = list(workbook.iter(f'{{{NS["m"]}}}sheet'))
    sheet = sheets[0] if name is None else next(sheet for sheet in sheets if sheet.get('name') == name)
    target = targets[sheet.get(f'{{{NS["r"]}}}id')].lstrip('/')
    return target if target.startswith('xl/') else f'xl/{target}'


def _column(reference):
    """A cell reference's column, from 0: A1 is 0, AB7 is 27."""
    letters = re.match(r'[A-Z]+', reference).group(0)
    return sum((ord(letter) - 64) * 26 ** i for i, letter in enumerate(reversed(letters))) - 1
