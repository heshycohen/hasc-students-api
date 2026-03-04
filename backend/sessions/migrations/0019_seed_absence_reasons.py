# Seed default absence reason codes for attendance

from django.db import migrations


def seed_absence_reasons(apps, schema_editor):
    AbsenceReason = apps.get_model('academic_sessions', 'AbsenceReason')
    reasons = [
        ('SICK', 'Sick', False),
        ('APPT', 'Appointment', False),
        ('TRANSPORTATION', 'Transportation', False),
        ('FAMILY', 'Family', False),
        ('UNKNOWN', 'Unknown', False),
        ('OTHER', 'Other', False),
    ]
    for code, label, billable in reasons:
        AbsenceReason.objects.get_or_create(
            reason_code=code,
            defaults={'reason_label': label, 'billable_flag': billable},
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('academic_sessions', '0018_roster_medical_incident_attendance'),
    ]

    operations = [
        migrations.RunPython(seed_absence_reasons, noop),
    ]
