# Generated migration for optimistic locking fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('academic_sessions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='version',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='student',
            name='locked_by',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='locked_students',
                to='users.user'
            ),
        ),
        migrations.AddField(
            model_name='student',
            name='locked_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='employee',
            name='version',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='employee',
            name='locked_by',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='locked_employees',
                to='users.user'
            ),
        ),
        migrations.AddField(
            model_name='employee',
            name='locked_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
