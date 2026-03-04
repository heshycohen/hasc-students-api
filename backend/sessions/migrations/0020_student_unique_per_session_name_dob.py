# Unique constraint on (session, last_name, first_name, date_of_birth) was skipped
# because the DB has duplicate rows. Apply the constraint manually after deduping:
#   ALTER TABLE students ADD CONSTRAINT students_session_name_dob_uniq
#   UNIQUE (session_id, last_name, first_name, date_of_birth);

from django.db import migrations


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('academic_sessions', '0019_seed_absence_reasons'),
    ]

    operations = [
        migrations.RunPython(noop, noop),
    ]
