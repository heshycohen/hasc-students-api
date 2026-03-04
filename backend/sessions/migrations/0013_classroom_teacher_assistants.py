# Add teacher, assistant1, assistant2 to Classroom for roster report

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic_sessions', '0012_medical_due_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='classroom',
            name='teacher',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='classroom',
            name='assistant1',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='classroom',
            name='assistant2',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
