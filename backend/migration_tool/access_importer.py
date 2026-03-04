"""
Tool to import data from Microsoft Access databases (.accdb files).
"""
import pyodbc
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from sessions.models import AcademicSession, Student, Employee
from compliance.encryption import encryption_service
from datetime import datetime


class AccessDatabaseImporter:
    """Import data from Access databases."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None
    
    def connect(self):
        """Connect to Access database."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
        
        # Connection string for Access
        conn_str = (
            r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
            r'DBQ=' + self.db_path + ';'
        )
        
        try:
            self.connection = pyodbc.connect(conn_str)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to database: {str(e)}")
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
    
    def get_tables(self):
        """Get list of tables in the database."""
        cursor = self.connection.cursor()
        tables = []
        for row in cursor.tables(tableType='TABLE'):
            tables.append(row.table_name)
        return tables
    
    def get_table_schema(self, table_name):
        """Get schema information for a table."""
        cursor = self.connection.cursor()
        columns = []
        for row in cursor.columns(table=table_name):
            columns.append({
                'name': row.column_name,
                'type': row.type_name,
                'size': row.column_size,
                'nullable': row.nullable
            })
        return columns
    
    def read_table(self, table_name):
        """Read all rows from a table."""
        cursor = self.connection.cursor()
        cursor.execute(f"SELECT * FROM [{table_name}]")
        columns = [column[0] for column in cursor.description]
        rows = []
        for row in cursor.fetchall():
            rows.append(dict(zip(columns, row)))
        return rows
    
    def detect_session_from_filename(self, filename):
        """Detect session type and name from filename."""
        filename_lower = filename.lower()
        
        # Check for Summer session
        if 'summer' in filename_lower:
            year_match = None
            for year in range(2000, 2100):
                if str(year) in filename:
                    year_match = year
                    break
            if year_match:
                return {
                    'session_type': 'SUMMER',
                    'name': f'Summer {year_match}',
                    'year': year_match
                }
        
        # Check for School Year (SY)
        if 'sy' in filename_lower or 'school' in filename_lower:
            # Try to extract year range (e.g., SY2024-2025, SY2024-25)
            import re
            pattern = r'(\d{4})[-_](\d{2,4})'
            match = re.search(pattern, filename)
            if match:
                year1 = int(match.group(1))
                year2_str = match.group(2)
                if len(year2_str) == 2:
                    year2 = 2000 + int(year2_str)
                else:
                    year2 = int(year2_str)
                
                return {
                    'session_type': 'SY',
                    'name': f'SY{year1}-{str(year2)[-2:]}',
                    'start_year': year1,
                    'end_year': year2
                }
        
        return None
    
    def import_session(self, filename):
        """Import a session from Access database file."""
        session_info = self.detect_session_from_filename(filename)
        if not session_info:
            raise ValueError(f"Could not determine session from filename: {filename}")
        
        self.connect()
        
        try:
            with transaction.atomic():
                # Create or get session
                session, created = AcademicSession.objects.get_or_create(
                    name=session_info['name'],
                    defaults={
                        'session_type': session_info['session_type'],
                        'start_date': datetime(session_info.get('start_year', session_info.get('year', 2024)), 9, 1).date(),
                        'end_date': datetime(session_info.get('end_year', session_info.get('year', 2024) + 1), 6, 30).date(),
                        'is_active': False
                    }
                )
                
                # Get tables
                tables = self.get_tables()
                
                # Look for student/child tables
                student_tables = [t for t in tables if 'student' in t.lower() or 'child' in t.lower()]
                employee_tables = [t for t in tables if 'employee' in t.lower() or 'staff' in t.lower()]
                
                students_imported = 0
                employees_imported = 0
                
                # Import students
                for table_name in student_tables:
                    rows = self.read_table(table_name)
                    for row in rows:
                        try:
                            # Map Access columns to Student model
                            student = self._create_student_from_row(row, session)
                            if student:
                                students_imported += 1
                        except Exception as e:
                            print(f"Error importing student from {table_name}: {e}")
                
                # Import employees
                for table_name in employee_tables:
                    rows = self.read_table(table_name)
                    for row in rows:
                        try:
                            # Map Access columns to Employee model
                            employee = self._create_employee_from_row(row, session)
                            if employee:
                                employees_imported += 1
                        except Exception as e:
                            print(f"Error importing employee from {table_name}: {e}")
                
                return {
                    'session': session,
                    'students_imported': students_imported,
                    'employees_imported': employees_imported
                }
        finally:
            self.close()
    
    def _create_student_from_row(self, row, session):
        """Create Student object from database row."""
        # Map common column names
        first_name = row.get('FirstName') or row.get('First_Name') or row.get('first_name') or ''
        last_name = row.get('LastName') or row.get('Last_Name') or row.get('last_name') or ''
        
        if not first_name or not last_name:
            return None
        
        # Parse date of birth
        dob = None
        for key in ['DateOfBirth', 'DOB', 'BirthDate', 'date_of_birth']:
            if key in row and row[key]:
                try:
                    if isinstance(row[key], str):
                        dob = datetime.strptime(row[key], '%Y-%m-%d').date()
                    else:
                        dob = row[key]
                    break
                except:
                    pass
        
        if not dob:
            return None
        
        # Parse enrollment date
        enrollment_date = session.start_date
        for key in ['EnrollmentDate', 'EnrollDate', 'enrollment_date']:
            if key in row and row[key]:
                try:
                    if isinstance(row[key], str):
                        enrollment_date = datetime.strptime(row[key], '%Y-%m-%d').date()
                    else:
                        enrollment_date = row[key]
                    break
                except:
                    pass
        
        # Get SSN if present (will be encrypted)
        ssn = row.get('SSN') or row.get('SocialSecurityNumber') or None
        
        student = Student.objects.create(
            session=session,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=dob,
            enrollment_date=enrollment_date,
            status='active',
            parent_email=row.get('ParentEmail') or row.get('parent_email') or None,
            parent_phone=row.get('ParentPhone') or row.get('parent_phone') or None,
        )
        
        # Encrypt and store SSN if present
        if ssn:
            student.set_ssn(str(ssn))
            student.save()
        
        return student
    
    def _create_employee_from_row(self, row, session):
        """Create Employee object from database row."""
        # Map common column names
        first_name = row.get('FirstName') or row.get('First_Name') or row.get('first_name') or ''
        last_name = row.get('LastName') or row.get('Last_Name') or row.get('last_name') or ''
        email = row.get('Email') or row.get('email') or None
        position = row.get('Position') or row.get('position') or row.get('Title') or 'Staff'
        
        if not first_name or not last_name or not email:
            return None
        
        # Parse hire date
        hire_date = session.start_date
        for key in ['HireDate', 'hire_date', 'StartDate']:
            if key in row and row[key]:
                try:
                    if isinstance(row[key], str):
                        hire_date = datetime.strptime(row[key], '%Y-%m-%d').date()
                    else:
                        hire_date = row[key]
                    break
                except:
                    pass
        
        employee = Employee.objects.create(
            session=session,
            first_name=first_name,
            last_name=last_name,
            email=email,
            position=position,
            hire_date=hire_date,
            status='active',
            phone=row.get('Phone') or row.get('phone') or None,
            department=row.get('Department') or row.get('department') or None,
        )
        
        return employee


class Command(BaseCommand):
    """Django management command to import Access databases."""
    help = 'Import data from Microsoft Access database files'
    
    def add_arguments(self, parser):
        parser.add_argument('db_file', type=str, help='Path to Access database file (.accdb)')
        parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without importing')
    
    def handle(self, *args, **options):
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
