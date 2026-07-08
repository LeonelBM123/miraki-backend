from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0002_fix_audit_columns'),
    ]

    operations = [
        migrations.AddField(
            model_name='posicion',
            name='bateria',
            field=models.SmallIntegerField(
                blank=True,
                db_column='bateria',
                help_text='Nivel de batería del dispositivo (0-100) al reportar la posición.',
                null=True,
            ),
        ),
    ]
