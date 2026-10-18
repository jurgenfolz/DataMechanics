"""Static files storage for production."""

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class HashedStaticFiles(ManifestStaticFilesStorage):
    """Hashed file names, also inside JavaScript module imports (the chart scripts import each other)."""

    support_js_module_import_aggregation = True
