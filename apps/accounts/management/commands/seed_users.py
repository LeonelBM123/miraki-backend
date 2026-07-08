from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Polygon

from apps.accounts.models import Rol, Tutor
from apps.institutions.models import CentroEducativo, AdminCentro
from apps.children.models import Nino
from apps.zones.models import ZonaSegura, HorarioZona

Usuario = get_user_model()


class Command(BaseCommand):
    help = 'Crea usuarios de prueba para todos los roles del sistema (SuperAdmin, AdminCentro, Tutor) y datos de ejemplo.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Iniciando población de base de datos (Seeder)...")

        # 1. Asegurar roles
        rol_super, _ = Rol.objects.get_or_create(
            nombre_rol='SuperAdmin',
            defaults={'descripcion': 'Administrador general del sistema'}
        )
        rol_centro, _ = Rol.objects.get_or_create(
            nombre_rol='AdminCentro',
            defaults={'descripcion': 'Administrador de un centro educativo'}
        )
        rol_tutor, _ = Rol.objects.get_or_create(
            nombre_rol='Tutor',
            defaults={'descripcion': 'Padre o tutor que monitorea a uno o más niños'}
        )

        # 2. SuperAdmin
        super_email = 'admin0@miraki.com'
        if not Usuario.objects.filter(correo=super_email).exists():
            super_user = Usuario.objects.create_superuser(
                correo=super_email,
                password='pass123',
                id_rol=rol_super
            )
            self.stdout.write(self.style.SUCCESS(f'[OK] SuperAdmin creado: {super_email} / Password123!'))
        else:
            super_user = Usuario.objects.get(correo=super_email)
            self.stdout.write(f'[INFO] SuperAdmin ya existía: {super_email}')

        # 3. Centros Educativos
        centro, _ = CentroEducativo.objects.get_or_create(
            nombre='Colegio San Ignacio',
            defaults={'direccion': 'Av. Principal #100, Zona Central', 'activo': True}
        )
        CentroEducativo.objects.get_or_create(
            nombre='Instituto Don Bosco',
            defaults={'direccion': 'Av. Las Américas #250', 'activo': True}
        )
        CentroEducativo.objects.get_or_create(
            nombre='Colegio Nacional y Comercial',
            defaults={'direccion': 'Calle Bolívar #45', 'activo': True}
        )

        # 4. AdminCentro
        centro_email = 'admin1@miraki.com'
        if not Usuario.objects.filter(correo=centro_email).exists():
            user_centro = Usuario.objects.create_user(
                correo=centro_email,
                password='pass123',
                id_rol=rol_centro
            )
            AdminCentro.objects.create(
                id_usuario=user_centro,
                id_centro=centro,
                nombre='Director San Ignacio',
                telefono='77712345',
                activo=True
            )
            self.stdout.write(self.style.SUCCESS(f'[OK] AdminCentro creado: {centro_email} / Password123!'))
        else:
            user_centro = Usuario.objects.get(correo=centro_email)
            self.stdout.write(f'[INFO] AdminCentro ya existía: {centro_email}')

        # 5. Tutor
        tutor_email = 'tutor@miraki.com'
        if not Usuario.objects.filter(correo=tutor_email).exists():
            user_tutor = Usuario.objects.create_user(
                correo=tutor_email,
                password='pass123',
                id_rol=rol_tutor
            )
            tutor = Tutor.objects.create(
                id_usuario=user_tutor,
                nombre='Carlos Pérez (Tutor)',
                telefono='77754321',
                activo=True
            )
            self.stdout.write(self.style.SUCCESS(f'[OK] Tutor creado: {tutor_email} / Password123!'))
        else:
            user_tutor = Usuario.objects.get(correo=tutor_email)
            tutor = user_tutor.tutor
            self.stdout.write(f'[INFO] Tutor ya existía: {tutor_email}')

        # 6. Niños para el Tutor
        nino1, _ = Nino.objects.get_or_create(
            nombre='Lucas Pérez',
            id_tutor=tutor,
            defaults={
                'fecha_nacimiento': '2016-05-15',
                'centro': centro,
                'activo': True
            }
        )
        nino2, _ = Nino.objects.get_or_create(
            nombre='Sofía Pérez',
            id_tutor=tutor,
            defaults={
                'fecha_nacimiento': '2018-09-20',
                'centro': centro,
                'activo': True
            }
        )
        self.stdout.write(self.style.SUCCESS('[OK] Niños creados/verificados: Lucas y Sofía'))

        # 7. Zonas Seguras de Ejemplo
        poly_tutor = Polygon((
            (-64.7310, -21.5320),
            (-64.7310, -21.5300),
            (-64.7280, -21.5300),
            (-64.7280, -21.5320),
            (-64.7310, -21.5320),
        ))
        zona_tutor, zt_created = ZonaSegura.objects.get_or_create(
            nombre='Zona Segura Casa - Parque',
            id_tutor_propietario=tutor,
            defaults={
                'poligono': poly_tutor,
                'activo': True,
                'id_centro': None,
                'creado_por': user_tutor,
                'modificado_por': user_tutor
            }
        )
        if zt_created:
            HorarioZona.objects.create(
                id_zona=zona_tutor,
                dia_semana=1,
                hora_inicio='08:00',
                hora_fin='13:00',
                activo=True,
                creado_por=user_tutor,
                modificado_por=user_tutor
            )
            self.stdout.write(self.style.SUCCESS('[OK] Zona Segura de Tutor creada con horario.'))

        poly_centro = Polygon((
            (-64.7350, -21.5350),
            (-64.7350, -21.5330),
            (-64.7320, -21.5330),
            (-64.7320, -21.5350),
            (-64.7350, -21.5350),
        ))
        ZonaSegura.objects.get_or_create(
            nombre='Perímetro Institucional San Ignacio',
            id_centro=centro,
            defaults={
                'poligono': poly_centro,
                'activo': True,
                'id_tutor_propietario': None,
                'creado_por': user_centro,
                'modificado_por': user_centro
            }
        )
        self.stdout.write(self.style.SUCCESS('[OK] Zona Segura Institucional creada.'))

        self.stdout.write(self.style.SUCCESS("\n¡Seeder completado con éxito! Credenciales de acceso:"))
        self.stdout.write("---------------------------------------------------------")
        self.stdout.write("SuperAdmin : admin@miraki.com / Password123!")
        self.stdout.write("AdminCentro: admincentro@miraki.com / Password123!")
        self.stdout.write("Tutor      : tutor@miraki.com / Password123!")
        self.stdout.write("---------------------------------------------------------")
