"""Finds metrics by words in their title, summary, tags, series and keywords, in the active language and in English."""

from django.urls import reverse

from .catalog import METRICS


def find(query='', category=''):
    """Metrics that match every word of the query. Those whose title holds every word come first."""
    words = query.lower().split()
    matches = [
        metric for metric in METRICS
        if (not category or metric.tags.category == category)
        and all(word in metric.search_text() for word in words)
    ]
    return sorted(matches, key=lambda metric: not all(word in str(metric.title).lower() for word in words))


def index():
    """The data the header search box filters in the browser."""
    return [
        {
            'title': str(metric.title),
            'summary': str(metric.summary),
            'category': str(metric.tags.category_label),
            'url': reverse('metrics:detail', args=[metric.slug]),
            'text': metric.search_text(),
        }
        for metric in METRICS
    ]
