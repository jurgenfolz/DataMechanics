from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from pages.views import home

urlpatterns = [
    path('', home, name='home'),
    path('posts/', include('blog.urls')),
    path('metrics/', include('metrics.urls')),
    path('admin/', admin.site.urls),
]

# Uploaded files are served by Django only in development; the VPS web server serves them in production.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
