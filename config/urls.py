from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog
from django.views.decorators.cache import cache_control
from django.views.generic import RedirectView, TemplateView

from blog.views import legacy_post
from pages.views import home

from .sitemaps import SITEMAPS

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': SITEMAPS}, name='sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    # Links from the old WordPress site: its home page, and posts at /<slug>/.
    path('home/', RedirectView.as_view(pattern_name='home', permanent=True)),
]

# Every page in every language: English at the root, the others under their code (/de/, /pt/).
urlpatterns += i18n_patterns(
    path('', home, name='home'),
    path('posts/', include('blog.urls')),
    path('metrics/', include('metrics.urls')),
    path('politics/', include('politics.urls')),
    # The browser's translations of the strings in static/js.
    path('jsi18n/', cache_control(public=True, max_age=3600)(JavaScriptCatalog.as_view()), name='javascript-catalog'),
    prefix_default_language=False,
)

# Old WordPress posts lived at /<slug>/. This comes last so it never shadows a page.
urlpatterns += [path('<slug:slug>/', legacy_post, name='legacy-post')]

# Uploaded files are served by Django only in development; Caddy serves them on the VPS.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
