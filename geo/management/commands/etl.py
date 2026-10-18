import time
from importlib import import_module

from django.core.management.base import BaseCommand, CommandError

from providers import MODULES


class Command(BaseCommand):
    help = 'Run ETL modules from providers/: download each source and replace its table.'

    def add_arguments(self, parser):
        parser.add_argument('modules', nargs='*', help='Modules to run, e.g. worldbank.gdp. Default: all, in order.')

    def handle(self, *args, modules, **options):
        unknown = set(modules) - set(MODULES)
        if unknown:
            raise CommandError(f'Unknown modules: {", ".join(sorted(unknown))}. Known: {", ".join(MODULES)}')

        for name in modules or MODULES:
            started = time.monotonic()
            result = import_module(f'providers.{name}').run()
            seconds = time.monotonic() - started
            if isinstance(result, int):
                self.stdout.write(f'{name}: {result} rows ({seconds:.1f}s)')
                continue
            self.stdout.write(f'{name}: {result.rows} rows ({seconds:.1f}s)')
            if result.skipped_codes:
                self.stdout.write(f'  skipped {len(result.skipped_codes)} codes not in geo_country: '
                                  f'{", ".join(result.skipped_codes[:12])}{" ..." if len(result.skipped_codes) > 12 else ""}')
