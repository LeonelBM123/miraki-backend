import math

from django.contrib.gis.geos import Point, Polygon
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.alerts.models import Posicion
from apps.children.models import Nino
from apps.zones.models import NinoZonaSegura, ZonaSegura


def _box_around(lng, lat, radio_m):
    """Devuelve un polígono cuadrado (SRID 4326) centrado en (lng, lat).

    `radio_m` es el medio lado del cuadrado en metros. La conversión a grados es
    aproximada pero suficiente para zonas de unos cientos de metros: ~111320 m por
    grado de latitud, y el mismo valor escalado por cos(lat) para la longitud.
    """
    d_lat = radio_m / 111_320.0
    cos_lat = math.cos(math.radians(lat)) or 1e-9
    d_lng = radio_m / (111_320.0 * cos_lat)
    anillo = (
        (lng - d_lng, lat - d_lat),
        (lng + d_lng, lat - d_lat),
        (lng + d_lng, lat + d_lat),
        (lng - d_lng, lat + d_lat),
        (lng - d_lng, lat - d_lat),
    )
    return Polygon(anillo, srid=4326)


class Command(BaseCommand):
    help = (
        'Crea una zona segura cuadrada alrededor de la última ubicación reportada '
        'por un niño y la vincula a ese niño, de modo que su posición actual quede '
        'dentro de la zona.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--nino', required=True, help='id_nino o nombre exacto del niño.')
        parser.add_argument(
            '--nombre',
            default='Zona alrededor de mi ubicación',
            help='Nombre de la zona segura a crear.',
        )
        parser.add_argument(
            '--radio',
            type=float,
            default=300.0,
            help='Medio lado del cuadrado en metros (default 300 => zona de ~600 m de lado).',
        )

    def _resolver_nino(self, valor):
        if valor.isdigit():
            try:
                return Nino.objects.select_related('id_tutor__id_usuario').get(pk=int(valor))
            except Nino.DoesNotExist as exc:
                raise CommandError(f'No existe un niño con id={valor}.') from exc

        qs = Nino.objects.select_related('id_tutor__id_usuario').filter(nombre=valor)
        total = qs.count()
        if total == 0:
            raise CommandError(f'No existe un niño con nombre {valor!r}.')
        if total > 1:
            ids = ', '.join(str(n.id_nino) for n in qs)
            raise CommandError(
                f'Hay varios niños con nombre {valor!r} (ids: {ids}). Usá --nino <id>.'
            )
        return qs.first()

    @transaction.atomic
    def handle(self, *args, **options):
        nino = self._resolver_nino(options['nino'])

        pos = (
            Posicion.objects.filter(id_dispositivo__id_nino=nino)
            .order_by('-fecha_posicion')
            .first()
        )
        if pos is None:
            raise CommandError(
                f'{nino.nombre} (id={nino.id_nino}) todavía no tiene posiciones reportadas.'
            )

        lat = float(pos.latitud)
        lng = float(pos.longitud)
        radio = options['radio']
        poligono = _box_around(lng, lat, radio)

        tutor = nino.id_tutor
        usuario = getattr(tutor, 'id_usuario', None)

        zona = ZonaSegura.objects.create(
            nombre=options['nombre'],
            poligono=poligono,
            activo=True,
            id_tutor_propietario=tutor,
            id_centro=None,
            creado_por=usuario,
            modificado_por=usuario,
        )

        asoc, creada = NinoZonaSegura.objects.get_or_create(
            id_nino=nino,
            id_zona=zona,
            defaults={'activa': True, 'creado_por': usuario, 'modificado_por': usuario},
        )
        if not creada and not asoc.activa:
            asoc.activa = True
            asoc.modificado_por = usuario
            asoc.save(update_fields=['activa', 'modificado_por'])

        punto = pos.ubicacion if pos.ubicacion is not None else Point(lng, lat, srid=4326)
        cubre = ZonaSegura.objects.filter(pk=zona.pk, poligono__covers=punto).exists()

        self.stdout.write(
            self.style.SUCCESS(
                f'Zona "{zona.nombre}" (id={zona.id_zona}) creada alrededor de '
                f'({lat:.6f}, {lng:.6f}) con medio lado {radio:.0f} m.'
            )
        )
        self.stdout.write(
            f'Vinculada al niño {nino.nombre} (id={nino.id_nino}), asociación activa={asoc.activa}.'
        )
        self.stdout.write(
            'La última posición del niño queda '
            + ('DENTRO' if cubre else 'FUERA')
            + ' del polígono.'
        )
        if not cubre:
            raise CommandError(
                'La posición no quedó dentro del polígono; revisá el radio o la ubicación.'
            )
