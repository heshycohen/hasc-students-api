# Add aide_1to1 for roster 1:1AIDE column

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic_sessions', '0014_student_uploaded_pdf'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='aide_1to1',
            field=models.CharField(blank=True, help_text='1:1 aide name for roster report', max_length=100, null=True),
        ),
    ]
