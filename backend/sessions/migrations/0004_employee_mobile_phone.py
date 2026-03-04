# Generated migration for Employee.mobile_phone

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic_sessions', '0003_add_student_class_num'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='mobile_phone',
            field=models.CharField(blank=True, help_text='Mobile phone', max_length=20, null=True),
        ),
    ]
