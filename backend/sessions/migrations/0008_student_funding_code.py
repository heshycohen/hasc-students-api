# Add funding_code to Student for Funding Codes filter

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic_sessions', '0007_classroom'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='funding_code',
            field=models.CharField(blank=True, help_text='Funding code from Access', max_length=20, null=True),
        ),
    ]
