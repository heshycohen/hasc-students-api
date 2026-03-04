# Initial migration for academic sessions, students, employees
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AcademicSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_type', models.CharField(choices=[('SY', 'School Year'), ('SUMMER', 'Summer Session')], max_length=10)),
                ('name', models.CharField(max_length=50, unique=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('is_active', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source_session', models.ForeignKey(blank=True, help_text='Session from which data was inherited', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='derived_sessions', to='academic_sessions.academicsession')),
            ],
            options={
                'db_table': 'academic_sessions',
                'ordering': ['-start_date'],
            },
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('date_of_birth', models.DateField()),
                ('enrollment_date', models.DateField()),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('graduated', 'Graduated'), ('transferred', 'Transferred')], default='active', max_length=20)),
                ('directory_info_opt_out', models.BooleanField(default=False, help_text='Parent/student has opted out of directory information')),
                ('ssn_encrypted', models.TextField(blank=True, null=True)),
                ('medical_info_encrypted', models.TextField(blank=True, null=True)),
                ('phi_encrypted', models.BooleanField(default=False)),
                ('parent_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('parent_phone', models.CharField(blank=True, max_length=20, null=True)),
                ('emergency_contact', models.CharField(blank=True, max_length=200, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='students', to='academic_sessions.academicsession')),
            ],
            options={
                'db_table': 'students',
                'ordering': ['last_name', 'first_name'],
            },
        ),
        migrations.CreateModel(
            name='Employee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('position', models.CharField(max_length=100)),
                ('hire_date', models.DateField()),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('terminated', 'Terminated')], default='active', max_length=20)),
                ('phone', models.CharField(blank=True, max_length=20, null=True)),
                ('department', models.CharField(blank=True, max_length=100, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='employees', to='academic_sessions.academicsession')),
            ],
            options={
                'db_table': 'employees',
                'ordering': ['last_name', 'first_name'],
            },
        ),
        migrations.AddIndex(
            model_name='student',
            index=models.Index(fields=['session', 'status'], name='students_session_8b0f0d_idx'),
        ),
        migrations.AddIndex(
            model_name='student',
            index=models.Index(fields=['last_name', 'first_name'], name='students_last_na_2c2e2a_idx'),
        ),
        migrations.AddIndex(
            model_name='employee',
            index=models.Index(fields=['session', 'status'], name='employees_session_9a1b2c_idx'),
        ),
        migrations.AddIndex(
            model_name='employee',
            index=models.Index(fields=['email'], name='employees_email_3d4e5f_idx'),
        ),
    ]
