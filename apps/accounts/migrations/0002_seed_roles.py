from django.db import migrations

ROLES_BASE = [
    ('Tutor', 'Padre o tutor que monitorea a uno o más niños'),
    ('AdminCentro', 'Administrador de un centro educativo'),
    ('SuperAdmin', 'Administrador general del sistema'),
]


def seed_roles(apps, schema_editor):
    Rol = apps.get_model('accounts', 'Rol')
    for nombre_rol, descripcion in ROLES_BASE:
        Rol.objects.get_or_create(nombre_rol=nombre_rol, defaults={'descripcion': descripcion})


def unseed_roles(apps, schema_editor):
    Rol = apps.get_model('accounts', 'Rol')
    Rol.objects.filter(nombre_rol__in=[nombre for nombre, _ in ROLES_BASE]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_roles, unseed_roles),
    ]
