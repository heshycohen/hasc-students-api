# SchoolDistrict model from Access school district lookup table

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic_sessions', '0010_student_school_district'),
    ]

    operations = [
        migrations.CreateModel(
            name='SchoolDistrict',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('session', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='school_districts', to='academic_sessions.academicsession')),
            ],
            options={
                'db_table': 'school_districts',
                'ordering': ['name'],
                'unique_together': {('session', 'name')},
            },
        ),
    ]
