import uuid

from django.db import migrations, models


def backfill_public_id(apps, schema_editor):
    Usuario = apps.get_model('accounts', 'Usuario')
    for usuario in Usuario.objects.filter(public_id__isnull=True).iterator():
        usuario.public_id = uuid.uuid4()
        usuario.save(update_fields=['public_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_seed_roles'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='public_id',
            field=models.UUIDField(blank=True, db_column='public_id', editable=False, null=True),
        ),
        migrations.RunPython(backfill_public_id, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='usuario',
            name='public_id',
            field=models.UUIDField(db_column='public_id', default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
