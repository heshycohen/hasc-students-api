# Classroom model for Classes table data (CLASSNUM / CLASSSIZE)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic_sessions', '0006_remove_employee_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='Classroom',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('class_num', models.CharField(max_length=50)),
                ('class_size', models.CharField(blank=True, max_length=50, null=True)),
                ('session', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='classrooms', to='academic_sessions.academicsession')),
            ],
            options={
                'db_table': 'classrooms',
                'ordering': ['class_num'],
                'unique_together': {('session', 'class_num')},
            },
        ),
    ]
