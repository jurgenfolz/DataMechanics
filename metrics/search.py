"""Finds metrics by words in their title, summary, tags, series and keywords."""

from .catalog import METRICS


def find(query='', category=''):
    """Metrics that match every word of the query, in catalog order."""
    words = query.lower().split()
    return [
        metric for metric in METRICS
        if (not category or metric.tags.category == category)
        and all(word in metric.search_text() for word in words)
    ]


def index():
    """The data the header search box filters in the browser."""
    return [
        {
            'title': metric.title,
            'summary': metric.summary,
            'category': metric.tags.category,
            'url': f'/metrics/{metric.slug}/',
            'text': metric.search_text(),
        }
        for metric in METRICS
    ]
