"""
Services for session data inheritance.
"""
from django.db import transaction
from .models import AcademicSession, Student, Employee
from compliance.utils import log_access, log_security_event


class SessionInheritanceService:
    """Service for copying data between sessions."""
    
    def copy_session_data(self, source_session, target_session, user):
        """
        Copy all active students and employees from source to target session.
        
        Args:
            source_session: AcademicSession to copy from
            target_session: AcademicSession to copy to
            user: User performing the operation
        
        Returns:
            dict: Summary of copied data
        """
        with transaction.atomic():
            # Copy students
            source_students = Student.objects.filter(
                session=source_session,
                status='active'
            )
            
            students_copied = 0
            for student in source_students:
                # Check if student already exists in target session
                existing = Student.objects.filter(
                    session=target_session,
                    first_name=student.first_name,
                    last_name=student.last_name,
                    date_of_birth=student.date_of_birth
                ).first()
                
                if not existing:
                    # Copy student
                    new_student = Student.objects.create(
                        session=target_session,
                        first_name=student.first_name,
                        last_name=student.last_name,
                        date_of_birth=student.date_of_birth,
                        enrollment_date=target_session.start_date,
                        status='active',
                        directory_info_opt_out=student.directory_info_opt_out,
                        ssn_encrypted=student.ssn_encrypted,
                        medical_info_encrypted=student.medical_info_encrypted,
                        phi_encrypted=student.phi_encrypted,
                        parent_email=student.parent_email,
                        parent_phone=student.parent_phone,
                        emergency_contact=student.emergency_contact,
                        notes=student.notes
                    )
                    students_copied += 1
                    
                    # Log access
                    log_access(user, 'student', new_student.id, 'create', 
                             changes={'inherited_from': source_session.name})
            
            # Copy employees
            source_employees = Employee.objects.filter(session=source_session)
            
            employees_copied = 0
            for employee in source_employees:
                # Check if employee already exists in target session
                existing = Employee.objects.filter(
                    session=target_session,
                    email=employee.email
                ).first()
                
                if not existing:
                    # Copy employee
                    new_employee = Employee.objects.create(
                        session=target_session,
                        first_name=employee.first_name,
                        last_name=employee.last_name,
                        email=employee.email,
                        position=employee.position,
                        phone=employee.phone,
                        mobile_phone=employee.mobile_phone,
                        notes=employee.notes
                    )
                    employees_copied += 1
                    
                    # Log access
                    log_access(user, 'employee', new_employee.id, 'create',
                             changes={'inherited_from': source_session.name})
            
            # Update target session source reference
            target_session.source_session = source_session
            target_session.save()
            
            # Log security event
            log_security_event(
                'configuration_change',
                user=user,
                details={
                    'action': 'session_data_copy',
                    'source_session': source_session.name,
                    'target_session': target_session.name,
                    'students_copied': students_copied,
                    'employees_copied': employees_copied
                },
                severity='low'
            )
            
            return {
                'success': True,
                'source_session': source_session.name,
                'target_session': target_session.name,
                'students_copied': students_copied,
                'employees_copied': employees_copied,
                'message': f'Copied {students_copied} students and {employees_copied} employees'
            }
