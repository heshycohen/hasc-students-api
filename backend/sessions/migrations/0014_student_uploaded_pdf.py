# Add uploaded_pdf to Student for PDF attachment

from django.db import migrations, models
import sessions.models


class Migration(migrations.Migration):

    dependencies = [
        ('academic_sessions', '0013_classroom_teacher_assistants'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='uploaded_pdf',
            field=models.FileField(
                blank=True,
                help_text="PDF file attached to this child's record",
                null=True,
                upload_to=sessions.models._student_pdf_upload_to,
            ),
        ),
    ]
