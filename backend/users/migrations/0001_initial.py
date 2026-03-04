# Generated manually for custom User model

import django.contrib.auth.models
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, verbose_name='superuser status')),
                ('username', models.CharField(max_length=150, verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('oauth_provider', models.CharField(blank=True, max_length=50, null=True)),
                ('oauth_id', models.CharField(blank=True, max_length=255, null=True)),
                ('role', models.CharField(choices=[('admin', 'Administrator'), ('editor', 'Editor'), ('viewer', 'Viewer')], default='viewer', max_length=20)),
                ('mfa_enabled', models.BooleanField(default=False)),
                ('last_login_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('failed_login_attempts', models.IntegerField(default=0)),
                ('account_locked_until', models.DateTimeField(blank=True, null=True)),
                ('password_changed_at', models.DateTimeField(blank=True, null=True)),
                ('security_clearance_level', models.IntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('groups', models.ManyToManyField(blank=True, related_name='users_user_set', to='auth.group')),
                ('user_permissions', models.ManyToManyField(blank=True, related_name='users_user_set', to='auth.permission')),
            ],
            options={
                'db_table': 'users',
                'verbose_name': 'User',
                'verbose_name_plural': 'Users',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
