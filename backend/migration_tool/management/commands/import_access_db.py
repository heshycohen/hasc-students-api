"""
Django management command to import Access databases.
"""
import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Django management command to import Access databases."""
    help = 'Import data from Microsoft Access database files'
    
    def add_arguments(self, parser):
        parser.add_argument('db_file', type=str, help='Path to Access database file (.accdb)')
        parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without importing')
    
    def handle(self, *args, **options):
        try:
            import pyodbc  # noqa: F401
        except ImportError:
            self.stdout.write(self.style.ERROR(
                'pyodbc is required for Access import. Install with: pip install pyodbc\n'
                'On Windows with Python 3.14 you may need Microsoft C++ Build Tools, '
                'or use Python 3.11/3.12.'
            ))
            return
        
        from migration_tool.access_importer import AccessDatabaseImporter
        
        db_file = options['db_file']
        dry_run = options.get('dry_run', False)
        
        if not os.path.exists(db_file):
            self.stdout.write(self.style.ERROR(f'Database file not found: {db_file}'))
            return
        
        self.stdout.write(f'Importing from: {db_file}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be imported'))
        
        importer = AccessDatabaseImporter(db_file)
        
        try:
            result = importer.import_session(os.path.basename(db_file))
            if not dry_run:
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully imported session: {result['session'].name}\n"
                    f"  Students: {result['students_imported']}\n"
                    f"  Employees: {result['employees_imported']}"
                ))
            else:
                self.stdout.write(self.style.SUCCESS('Dry run completed successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing: {str(e)}'))
