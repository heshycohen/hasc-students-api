# Add school_district to Student for School district filter

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic_sessions', '0009_fundingcode'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='school_district',
            field=models.CharField(blank=True, help_text='School district from Access', max_length=100, null=True),
        ),
    ]
