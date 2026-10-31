"""
Django settings for the Data Mechanics site.

Secrets and per-machine values come from environment variables, loaded from `.env` in the project root (see `.env.example`).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

DEBUG = os.environ.get('DJANGO_DEBUG', '0') == '1'

# The Crime tab of Politics mode (Germany's suspects by nationality). False hides it everywhere.
CRIME_TAB = True

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Full origins allowed to post forms, e.g. https://data-mechanics.com (needed behind HTTPS).
CSRF_TRUSTED_ORIGINS = [origin for origin in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if origin]

# Public repository of the site's code. The link is hidden until this is set.
GITHUB_URL = os.environ.get('GITHUB_URL') or 'https://github.com/jurgenfolz/DataMechanics'

# The author, shown in the About section on every page.
AUTHOR_LINKEDIN_URL = 'https://www.linkedin.com/in/klausjfolz/'
AUTHOR_GITHUB_URL = 'https://github.com/jurgenfolz'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.postgres',
    'blog',
    'geo',
    'metrics',
    'politics',
    'conflicts',
    'compare',
    'events',
    'pages',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'pages.context_processors.site',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# PostgreSQL, in Docker (docker-compose.yml).
# The conflicts (World War II for now) have a database of their own on the same server, with one schema per conflict.
# conflicts/routers.py sends the conflicts app there.
_POSTGRES = {
    'ENGINE': 'django.db.backends.postgresql',
    'USER': os.environ['POSTGRES_USER'],
    'PASSWORD': os.environ['POSTGRES_PASSWORD'],
    'HOST': os.environ.get('POSTGRES_HOST', '127.0.0.1'),
    'PORT': os.environ.get('POSTGRES_PORT', '5432'),
}
DATABASES = {
    'default': {**_POSTGRES, 'NAME': os.environ['POSTGRES_DB']},
    'conflicts': {**_POSTGRES, 'NAME': os.environ.get('POSTGRES_CONFLICTS_DB', 'conflicts')},
}
DATABASE_ROUTERS = ['conflicts.routers.ConflictsRouter']

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# English is the source language and lives at the root. German and Portuguese (Brazilian) live under /de/ and /pt/.
LANGUAGE_CODE = 'en'
LANGUAGES = [('en', 'English'), ('de', 'Deutsch'), ('pt', 'Português')]
LOCALE_PATHS = [BASE_DIR / 'locale']
# The site's own date formats per language (config/formats/<language>/formats.py).
FORMAT_MODULE_PATH = ['config.formats']

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# collectstatic gives every file a content hash in its name, so browsers can cache it for a year.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage' if DEBUG else 'config.storage.HashedStaticFiles',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# The site sends no email today. Production gets a real SMTP backend so nothing silently prints to a console.
MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend',
        'OPTIONS': {} if DEBUG else {
            'host': os.environ.get('EMAIL_HOST', 'localhost'),
            'port': int(os.environ.get('EMAIL_PORT', '25')),
        },
    },
}

# Errors and warnings go to stderr, which systemd keeps in the journal on the server.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}

if not DEBUG:
    # Caddy terminates HTTPS and tells Django so with this header.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Start low; raise to 31536000 (a year) once HTTPS has run without trouble for a while.
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', '3600'))
    # HSTS stays off for subdomains, because other services on the domain may not use HTTPS.
    # It also stays out of the browsers' preload list, which is hard to undo. Revisit both once the domain is settled.
    SILENCED_SYSTEM_CHECKS = ['security.W005', 'security.W021']
