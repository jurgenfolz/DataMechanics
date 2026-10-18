"""The site's date formats per language, read through FORMAT_MODULE_PATH.

Brazilian Portuguese writes month names in lower case, and Django's own catalog capitalises them.
Marking the names here keeps them in locale/, whose translations come before Django's.
"""

from django.utils.translation import gettext_noop

MONTHS = [
    gettext_noop('January'), gettext_noop('February'), gettext_noop('March'), gettext_noop('April'),
    gettext_noop('May'), gettext_noop('June'), gettext_noop('July'), gettext_noop('August'),
    gettext_noop('September'), gettext_noop('October'), gettext_noop('November'), gettext_noop('December'),
]
