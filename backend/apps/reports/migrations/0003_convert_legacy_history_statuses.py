from django.db import migrations

LEGACY_STATUS_MAP = {
    'em_execucao': 'em_andamento',
    'concluido': 'resolvido',
    'avaliado': 'resolvido',
}


def convert_history(apps, schema_editor):
    ReportHistory = apps.get_model('reports', 'ReportHistory')
    for legacy, current in LEGACY_STATUS_MAP.items():
        ReportHistory.objects.filter(old_status=legacy).update(old_status=current)
        ReportHistory.objects.filter(new_status=legacy).update(new_status=current)


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0002_remove_unused_fields'),
    ]

    operations = [
        migrations.RunPython(convert_history, migrations.RunPython.noop),
    ]
