from django.contrib import admin

from .models import Category, Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'published_at', 'is_published', 'cover_on_page']
    list_filter = ['is_published', 'categories']
    prepopulated_fields = {'slug': ['title']}
    search_fields = ['title', 'body']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ['name']}
