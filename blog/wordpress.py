"""Reads posts out of a WordPress export (WXR) file and cleans their HTML for this site."""

import html
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser

_NS = {
    'wp': 'http://wordpress.org/export/1.2/',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'excerpt': 'http://wordpress.org/export/1.2/excerpt/',
}

# Tag -> attributes kept. Other tags are unwrapped (their text stays); comments are dropped.
_ALLOWED = {
    'p': [], 'h2': [], 'h3': [], 'h4': [], 'strong': [], 'em': [], 'b': [], 'i': [], 'br': [], 'hr': [],
    'code': [], 'pre': [], 'blockquote': [], 'ul': [], 'ol': [], 'li': [], 'sub': [], 'sup': [],
    'figure': [], 'figcaption': [], 'img': ['src', 'alt'], 'a': ['href', 'title'],
    'table': [], 'thead': [], 'tbody': [], 'tr': [], 'th': [], 'td': [],
}
_VOID = {'br', 'hr', 'img'}
_DROP_WITH_CONTENT = {'script', 'style'}

_CODE_BLOCK = re.compile(
    r'<!-- wp:kevinbatdorf/code-block-pro (\{.*?\}) -->.*?<!-- /wp:kevinbatdorf/code-block-pro -->',
    re.DOTALL,
)


@dataclass
class ExportedPost:
    title: str
    slug: str
    published_at: datetime
    categories: list[str]
    html: str
    excerpt: str
    cover_url: str


def read_posts(path):
    """Every published post in the export, with cleaned HTML."""
    channel = ET.parse(path).getroot().find('channel')
    items = channel.findall('item')
    attachments = {
        item.findtext('wp:post_id', namespaces=_NS): item.findtext('wp:attachment_url', namespaces=_NS)
        for item in items
        if item.findtext('wp:post_type', namespaces=_NS) == 'attachment'
    }

    posts = []
    for item in items:
        if item.findtext('wp:post_type', namespaces=_NS) != 'post':
            continue
        if item.findtext('wp:status', namespaces=_NS) != 'publish':
            continue
        body = clean_html(item.findtext('content:encoded', namespaces=_NS) or '')
        posts.append(ExportedPost(
            title=html.unescape(item.findtext('title')),
            slug=item.findtext('wp:post_name', namespaces=_NS),
            published_at=datetime.strptime(
                item.findtext('wp:post_date_gmt', namespaces=_NS), '%Y-%m-%d %H:%M:%S'
            ).replace(tzinfo=timezone.utc),
            categories=[c.text for c in item.findall('category') if c.get('domain') == 'category'],
            html=body,
            excerpt=(item.findtext('excerpt:encoded', namespaces=_NS) or '').strip() or first_paragraph(body),
            cover_url=attachments.get(_meta(item, '_thumbnail_id'), ''),
        ))
    return posts


def clean_html(raw):
    raw = _CODE_BLOCK.sub(_code_block_to_pre, raw)
    cleaner = _Cleaner()
    cleaner.feed(raw)
    cleaner.close()
    return re.sub(r'\n{3,}', '\n\n', ''.join(cleaner.parts)).strip()


def image_urls(body):
    return re.findall(r'<img src="([^"]+)"', body)


def first_paragraph(body, limit=220):
    match = re.search(r'<p>(.*?)</p>', body, re.DOTALL)
    text = html.unescape(re.sub(r'<[^>]+>', '', match.group(1))).strip() if match else ''
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(' ', 1)[0] + '…'


def _meta(item, key):
    for meta in item.findall('wp:postmeta', namespaces=_NS):
        if meta.findtext('wp:meta_key', namespaces=_NS) == key:
            return meta.findtext('wp:meta_value', namespaces=_NS)
    return None


def _code_block_to_pre(match):
    code = html.unescape(json.loads(match.group(1))['code'])
    return f'<pre><code>{html.escape(code, quote=False)}</code></pre>'


class _Cleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._dropping = 0

    def handle_starttag(self, tag, attrs):
        if tag in _DROP_WITH_CONTENT:
            self._dropping += 1
        if self._dropping or tag not in _ALLOWED:
            return
        kept = ''.join(
            f' {name}="{html.escape(value or "", quote=True)}"' for name, value in attrs if name in _ALLOWED[tag]
        )
        self.parts.append(f'<{tag}{kept}>')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in _DROP_WITH_CONTENT:
            self._dropping -= 1
            return
        if self._dropping or tag not in _ALLOWED or tag in _VOID:
            return
        self.parts.append(f'</{tag}>')

    def handle_data(self, data):
        if not self._dropping:
            self.parts.append(html.escape(data, quote=False))
