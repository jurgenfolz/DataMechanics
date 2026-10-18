"""sitemap.xml: the home page, every metric page and every published post."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from blog.models import Post
from metrics.catalog import METRICS


class PageSitemap(Sitemap):
    def items(self):
        return ['home', 'metrics:list', 'blog:list']

    def location(self, item):
        return reverse(item)


class MetricSitemap(Sitemap):
    def items(self):
        return list(METRICS)

    def location(self, metric):
        return reverse('metrics:detail', args=[metric.slug])


class PostSitemap(Sitemap):
    def items(self):
        return Post.published.all()

    def lastmod(self, post):
        return post.published_at


SITEMAPS = {'pages': PageSitemap, 'metrics': MetricSitemap, 'posts': PostSitemap}
