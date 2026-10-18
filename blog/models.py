import math

from django.db import models
from django.urls import reverse
from django.utils.html import strip_tags

WORDS_PER_MINUTE = 200


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class PublishedPostManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)


class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    excerpt = models.TextField(blank=True)
    body = models.TextField(help_text='HTML.')
    cover_image = models.FileField(upload_to='blog/', blank=True)
    cover_on_page = models.BooleanField(
        default=True, help_text='Show the cover at the top of the post. Turn off when the body already opens with it.'
    )
    categories = models.ManyToManyField(Category, blank=True, related_name='posts')
    published_at = models.DateTimeField()
    is_published = models.BooleanField(default=True)

    objects = models.Manager()
    published = PublishedPostManager()

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog:detail', args=[self.slug])

    @property
    def reading_minutes(self):
        words = len(strip_tags(self.body).split())
        return max(1, math.ceil(words / WORDS_PER_MINUTE))
