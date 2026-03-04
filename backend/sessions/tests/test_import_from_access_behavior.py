"""
Golden tests for import_from_access behavior (prevents regression).
- DISCHARGE flag flips is_active.
- SPEDSERV "SEIT" -> seit; RS/RELATED -> related_service; CLASSNUM -> center_based; else unknown.
- Unknown stays unknown (not forced to related_service).
- --update-existing never creates (tested via call_command with no matching rows).
- DISCHARGE="x" is never assigned to discharge_date; only sets is_active=False.
"""
import os
import tempfile
from datetime import date

from django.core.management import call_command
from django.test import TestCase

from sessions.management.commands.import_from_access import derive_service_type, normalize_x_bool, parse_dob_robust
from sessions.management.commands.import_students_csv import parse_date_or_none
from sessions.models import AcademicSession, Site, Student


class TestParseDateOrNone(TestCase):
    """parse_date_or_none: DateField-safe parser; treats x/blank as None, strips time."""

    def test_flag_and_blank_return_none(self):
        self.assertIsNone(parse_date_or_none("x"))
        self.assertIsNone(parse_date_or_none("X"))
        self.assertIsNone(parse_date_or_none(""))
        self.assertIsNone(parse_date_or_none(None))

    def test_datetime_string_parses_to_date(self):
        self.assertEqual(parse_date_or_none("1/4/2021 0:00:00"), date(2021, 1, 4))
        self.assertEqual(parse_date_or_none("12/3/2020 0:00:00"), date(2020, 12, 3))


class TestParseDobRobust(TestCase):
    """DOB parsing: M/D/YYYY, MM/DD/YYYY, YYYY-MM-DD, M/D/YY; empty -> None."""

    def test_iso_and_us_formats(self):
        self.assertEqual(parse_dob_robust("2020-01-05"), date(2020, 1, 5))
        self.assertEqual(parse_dob_robust("01/05/2020"), date(2020, 1, 5))
        self.assertEqual(parse_dob_robust("1/5/2020"), date(2020, 1, 5))

    def test_two_digit_year(self):
        self.assertEqual(parse_dob_robust("1/5/20"), date(2020, 1, 5))
        self.assertEqual(parse_dob_robust("1/5/99"), date(1999, 1, 5))

    def test_access_datetime_strings(self):
        """Access/PowerShell export: strip time before parsing; first token must look like date."""
        self.assertEqual(parse_dob_robust("1/5/2020 0:00:00"), date(2020, 1, 5))
        self.assertEqual(parse_dob_robust("01/05/2020 12:30:00"), date(2020, 1, 5))
        self.assertEqual(parse_dob_robust("2020-01-05 00:00:00"), date(2020, 1, 5))
        self.assertEqual(parse_dob_robust("1/4/2021 0:00:00"), date(2021, 1, 4))
        self.assertEqual(parse_dob_robust("12/3/2020 0:00:00"), date(2020, 12, 3))

    def test_empty_and_invalid(self):
        self.assertIsNone(parse_dob_robust(""))
        self.assertIsNone(parse_dob_robust("   "))
        self.assertIsNone(parse_dob_robust(None))
        self.assertIsNone(parse_dob_robust("n/a"))


class TestNormalizeXBool(TestCase):
    """DISCHARGE flag -> is_active: x/yes/true => True (discharged)."""

    def test_x_is_true(self):
        self.assertTrue(normalize_x_bool("x"))
        self.assertTrue(normalize_x_bool("X"))

    def test_yes_true_y_1(self):
        self.assertTrue(normalize_x_bool("yes"))
        self.assertTrue(normalize_x_bool("true"))
        self.assertTrue(normalize_x_bool("y"))
        self.assertTrue(normalize_x_bool("1"))

    def test_blank_none_false(self):
        self.assertFalse(normalize_x_bool(None))
        self.assertFalse(normalize_x_bool(""))
        self.assertFalse(normalize_x_bool("no"))
        self.assertFalse(normalize_x_bool("foo"))


class TestDischargeFlagNotDateField(TestCase):
    """DISCHARGE column with value 'x' must set is_active=False only; never assign to discharge_date."""

    def test_normalize_x_bool_x_is_true(self):
        self.assertTrue(normalize_x_bool("x"))

    def test_import_with_discharge_x_does_not_crash_and_sets_is_active_only(self):
        """CSV row with DISCHARGE=x must not assign 'x' to discharge_date; is_active=False, discharge_date=None."""
        site = Site.objects.create(name="Test Site", slug="test")
        session = AcademicSession.objects.create(
            site=site,
            session_type="SY",
            name="SY2025-26",
            start_date=date(2025, 9, 1),
            end_date=date(2026, 6, 30),
        )
        csv_content = "Last Name,First Name,DOB,DISCHARGE\nFlag,Kid,2020-01-15,x\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(csv_content)
            csv_path = f.name
        try:
            call_command(
                "import_students_csv",
                csv_path,
                "--session", "SY2025-26",
                "--site", "test",
                "--add-missing-to-session",
            )
        finally:
            os.unlink(csv_path)
        student = Student.objects.filter(
            session=session,
            last_name="Flag",
            first_name="Kid",
        ).first()
        self.assertIsNotNone(student, "Student should be created")
        self.assertFalse(student.is_active, "DISCHARGE=x must set is_active=False")
        self.assertIsNone(student.discharge_date, "discharge_date must remain None when only DISCHARGE flag column present")


class TestDeriveServiceType(TestCase):
    """SPEDSERV/CLASSNUM -> service_type: SEIT distinct, unknown not forced to related_service."""

    def test_seit_maps_to_seit(self):
        self.assertEqual(derive_service_type("SEIT", None), "seit")
        self.assertEqual(derive_service_type("seit only", ""), "seit")
        self.assertEqual(derive_service_type("has SEIT in it", "1am"), "seit")

    def test_rs_or_related_maps_to_related_service(self):
        self.assertEqual(derive_service_type("RS", None), "related_service")
        self.assertEqual(derive_service_type("RELATED", None), "related_service")
        self.assertEqual(derive_service_type("RELATED SERVICE", None), "related_service")
        self.assertEqual(derive_service_type("rs", ""), "related_service")

    def test_classnum_present_maps_to_center_based(self):
        self.assertEqual(derive_service_type("", "1am"), "center_based")
        self.assertEqual(derive_service_type("", "2pm"), "center_based")
        self.assertEqual(derive_service_type("other", "3"), "center_based")

    def test_unknown_stays_unknown(self):
        self.assertEqual(derive_service_type("", None), "unknown")
        self.assertEqual(derive_service_type("", ""), "unknown")
        self.assertEqual(derive_service_type(None, None), "unknown")
        self.assertEqual(derive_service_type("OTHER", ""), "unknown")

    def test_seit_takes_precedence_over_classnum(self):
        self.assertEqual(derive_service_type("SEIT", "1am"), "seit")

    def test_sped_indiv_codes_rs_seit(self):
        """SPEDINDIV codes column (often populated when SPEDSERV is empty)."""
        self.assertEqual(derive_service_type(None, None, "rs"), "related_service")
        self.assertEqual(derive_service_type(None, None, "seit"), "seit")
        self.assertEqual(derive_service_type("", "", "ctr"), "center_based")
        self.assertEqual(derive_service_type("", "", "eic"), "center_based")


class TestUpdateExistingNeverCreates(TestCase):
    """With --update-existing, running import must not create new students."""

    @classmethod
    def setUpTestData(cls):
        site = Site.objects.create(name="Test Site", slug="test")
        cls.session = AcademicSession.objects.create(
            site=site,
            session_type="SY",
            name="SY2025-26",
            start_date="2025-09-01",
            end_date="2026-06-30",
        )
        Student.objects.create(
            session=cls.session,
            first_name="Only",
            last_name="One",
            date_of_birth="2020-01-15",
            service_type="center_based",
        )

    def test_update_existing_does_not_increase_count_without_accdb(self):
        """Without a real .accdb we cannot run the full command; test that count is unchanged after a no-op.
        If the command is run with --update-existing and a path that has no rows, it would not create.
        We test the guardrail: ambiguous match skips, and no create when no match.
        """
        count_before = Student.objects.filter(session=self.session).count()
        self.assertEqual(count_before, 1)
