# Add medical_due_date to Student and Employee for medical due filtering

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic_sessions', '0011_schooldistrict'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='medical_due_date',
            field=models.DateField(blank=True, help_text='Next medical clearance / physical due date', null=True),
        ),
        migrations.AddField(
            model_name='employee',
            name='medical_due_date',
            field=models.DateField(blank=True, help_text='Next medical clearance / physical due date', null=True),
        ),
    ]
