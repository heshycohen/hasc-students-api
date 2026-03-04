# FundingCode model from Access "Funding Codes" table

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic_sessions', '0008_student_funding_code'),
    ]

    operations = [
        migrations.CreateModel(
            name='FundingCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50)),
                ('session', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='funding_codes', to='academic_sessions.academicsession')),
            ],
            options={
                'db_table': 'funding_codes',
                'ordering': ['code'],
                'unique_together': {('session', 'code')},
            },
        ),
    ]
