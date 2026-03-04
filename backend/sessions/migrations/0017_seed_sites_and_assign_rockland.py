# Data migration: create 5 sites, assign all existing sessions to Rockland, set site non-null

from django.db import migrations, models
import django.db.models.deletion


def seed_sites_and_assign_rockland(apps, schema_editor):
    Site = apps.get_model('academic_sessions', 'Site')
    AcademicSession = apps.get_model('academic_sessions', 'AcademicSession')

    sites_data = [
        {'name': 'Rockland', 'slug': 'rockland', 'display_order': 1},
        {'name': 'Woodmere', 'slug': 'woodmere', 'display_order': 2},
        {'name': '55th Street', 'slug': '55th-street', 'display_order': 3},
        {'name': '14th Ave.', 'slug': '14th-ave', 'display_order': 4},
        {'name': 'SEIT', 'slug': 'seit', 'display_order': 5},
    ]
    for data in sites_data:
        Site.objects.get_or_create(slug=data['slug'], defaults=data)

    rockland = Site.objects.get(slug='rockland')
    AcademicSession.objects.filter(site__isnull=True).update(site=rockland)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('academic_sessions', '0016_add_site_and_scope_sessions'),
    ]

    operations = [
        migrations.RunPython(seed_sites_and_assign_rockland, noop),
        migrations.AlterField(
            model_name='academicsession',
            name='site',
            field=models.ForeignKey(
                help_text='Site this session belongs to; required for multi-site.',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='sessions',
                to='academic_sessions.site',
                null=False,
            ),
        ),
    ]
