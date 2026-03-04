"""
Ensures the student detail API contract includes all required fields for the child detail view.
See docs/student_detail_contract.json and docs/student_data_field_map.md.
"""
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from sessions.models import AcademicSession, Site, Student
from sessions.serializers import StudentDetailContractSerializer


class StudentDetailContractTest(TestCase):
    """Verify StudentDetailContractSerializer output shape."""

    @classmethod
    def setUpTestData(cls):
        site = Site.objects.create(name='Test Site', slug='test')
        cls.session = AcademicSession.objects.create(
            site=site,
            session_type='SY',
            name='SY2025-26',
            start_date='2025-09-01',
            end_date='2026-06-30',
        )
        cls.student = Student.objects.create(
            session=cls.session,
            first_name='Jane',
            last_name='Doe',
            date_of_birth='2018-05-15',
            enrollment_date='2024-09-01',
            status='active',
            is_active=True,
            service_type='center_based',
        )

    def test_detail_serializer_includes_core_fields(self):
        """Contract must include all core fields needed for UI groups."""
        req = APIRequestFactory().get('/')
        serializer = StudentDetailContractSerializer(
            self.student,
            context={'request': req},
        )
        data = serializer.data
        required = [
            'id', 'session', 'session_name', 'first_name', 'last_name',
            'date_of_birth', 'district_display', 'home_phone', 'mother_cell', 'father_cell',
            'email', 'parent_email', 'parent_phone', 'discharge_date', 'discharge_notes',
            'address', 'vaccines_status', 'vaccines_last_reviewed', 'vaccines_notes',
            'medical_start_date', 'medical_end_date', 'medical_due_date',
            'sped_indiv_code', 'notes',
            'incidents', 'services', 'meetings', 'reports', 'duplicate_warning',
        ]
        for key in required:
            self.assertIn(key, data, f'Contract must include "{key}"')

    def test_services_meetings_reports_are_structures(self):
        """Placeholders must be list/dict for UI."""
        req = APIRequestFactory().get('/')
        serializer = StudentDetailContractSerializer(
            self.student,
            context={'request': req},
        )
        data = serializer.data
        self.assertIsInstance(data.get('incidents'), list)
        self.assertIsInstance(data.get('services'), list)
        self.assertIsInstance(data.get('meetings'), list)
        self.assertIsInstance(data.get('reports'), dict)
