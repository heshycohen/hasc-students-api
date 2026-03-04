# Remove hire_date and department from Employee

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('academic_sessions', '0004_employee_mobile_phone'),
    ]

    operations = [
        migrations.RemoveField(model_name='employee', name='hire_date'),
        migrations.RemoveField(model_name='employee', name='department'),
    ]
