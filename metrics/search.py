"""Finds metrics by words in their title, summary, tags, series and keywords."""

from .catalog import METRICS


def find(query='', category=''):
    """Metrics that match every word of the query. Those whose title holds every word come first."""
    words = query.lower().split()
    matches = [
        metric for metric in METRICS
        if (not category or metric.tags.category == category)
        and all(word in metric.search_text() for word in words)
    ]
    return sorted(matches, key=lambda metric: not all(word in metric.title.lower() for word in words))


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
