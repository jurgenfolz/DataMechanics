from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView

from blog.views import legacy_post
from pages.views import home

from .sitemaps import SITEMAPS

urlpatterns = [
    path('', home, name='home'),
    path('posts/', include('blog.urls')),
    path('metrics/', include('metrics.urls')),
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': SITEMAPS}, name='sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    # Links from the old WordPress site: its home page, and posts at /<slug>/.
    path('home/', RedirectView.as_view(pattern_name='home', permanent=True)),
    path('<slug:slug>/', legacy_post, name='legacy-post'),
]

# Uploaded files are served by Django only in development; Caddy serves them on the VPS.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
