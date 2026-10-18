"""sitemap.xml: the home page, every metric page, every Politics country and every published post, in every language.

Each URL lists its other languages, so search engines show people the page in theirs.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from blog.models import Post
from metrics.catalog import METRICS
from politics.queries import countries


class LanguagesSitemap(Sitemap):
    i18n = True
    alternates = True
    x_default = True


class PageSitemap(LanguagesSitemap):
    def items(self):
        return ['home', 'metrics:list', 'politics:index', 'blog:list']

    def location(self, item):
        return reverse(item)


class MetricSitemap(LanguagesSitemap):
    def items(self):
        return list(METRICS)

    def location(self, metric):
        return reverse('metrics:detail', args=[metric.slug])


class PoliticsSitemap(LanguagesSitemap):
    def items(self):
        return [item['slug'] for item in countries()]

    def location(self, slug):
        return reverse('politics:country', args=[slug])


class PostSitemap(LanguagesSitemap):
    def items(self):
        return Post.published.all()

    def lastmod(self, post):
        return post.published_at


SITEMAPS = {'pages': PageSitemap, 'metrics': MetricSitemap, 'politics': PoliticsSitemap, 'posts': PostSitemap}
