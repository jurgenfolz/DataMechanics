from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from blog import wordpress
from blog.models import Category, Post

UPLOADS_MARKER = '/wp-content/uploads/'


class Command(BaseCommand):
    help = 'Import published posts from a WordPress export, downloading their images into MEDIA_ROOT/blog/.'

    def add_arguments(self, parser):
        parser.add_argument('export', help='Path to the WordPress export (.xml).')

    def handle(self, *args, export, **options):
        for exported in wordpress.read_posts(export):
            body = exported.html
            for url in wordpress.image_urls(body):
                body = body.replace(url, settings.MEDIA_URL + self._download(url))
            cover = self._download(exported.cover_url) if exported.cover_url else ''
            self._save(exported, body, cover)
            self.stdout.write(f'Imported "{exported.title}"')

    def _download(self, url):
        """Save an uploaded file under MEDIA_ROOT/blog/, keeping WordPress' year/month path. Returns its media path."""
        path = urlparse(url).path
        relative = 'blog/' + path.split(UPLOADS_MARKER, 1)[1] if UPLOADS_MARKER in path else 'blog/' + Path(path).name
        target = Path(settings.MEDIA_ROOT) / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            with urlopen(Request(url, headers={'User-Agent': 'DataMechanics importer'}), timeout=30) as response:
                target.write_bytes(response.read())
        return relative

    @transaction.atomic
    def _save(self, exported, body, cover):
        post, _ = Post.objects.update_or_create(
            slug=exported.slug,
            defaults={
                'title': exported.title,
                'body': body,
                'excerpt': exported.excerpt,
                'cover_image': cover,
                'published_at': exported.published_at,
            },
        )
        post.categories.set(
            Category.objects.get_or_create(slug=slugify(name), defaults={'name': name})[0]
            for name in exported.categories
        )
