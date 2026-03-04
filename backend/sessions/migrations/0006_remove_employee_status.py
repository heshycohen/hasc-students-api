# Remove status from Employee (employees are always active)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic_sessions', '0005_remove_employee_hire_date_and_department'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='employee',
            name='employees_session_683e73_idx',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='status',
        ),
        migrations.AddIndex(
            model_name='employee',
            index=models.Index(fields=['session'], name='employees_session_idx'),
        ),
    ]
