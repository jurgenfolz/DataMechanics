"""The conflicts app keeps its tables in their own PostgreSQL database, named by settings.DATABASES['conflicts'].

Nothing there points at the site's other tables: the world of 1937–1945 had other states and other borders.
"""

DATABASE = 'conflicts'
APP = 'conflicts'


class ConflictsRouter:
    def db_for_read(self, model, **hints):
        return DATABASE if model._meta.app_label == APP else None

    db_for_write = db_for_read

    def allow_relation(self, obj1, obj2, **hints):
        if APP in (obj1._meta.app_label, obj2._meta.app_label):
            return obj1._meta.app_label == obj2._meta.app_label
        return None

    def allow_migrate(self, db, app_label, **hints):
        if app_label == APP:
            return db == DATABASE
        # The site's own apps never migrate into the conflicts database.
        return False if db == DATABASE else None
