import math
import random
import time

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.alerts.models import Posicion
from apps.children.models import Nino
from apps.dispositivos.models import Dispositivo


class Command(BaseCommand):
    help = (
        'Genera posiciones GPS frescas para un niño, simulando el teléfono/reloj. '
        'Sirve para mantener la "última ubicación" al día y ver el mapa del tutor en vivo '
        'sin depender del dispositivo físico. Sin --duracion inserta una sola posición.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--nino', required=True, help='id_nino o nombre exacto del niño.')
        parser.add_argument('--intervalo', type=float, default=10.0, help='Segundos entre posiciones (default 10).')
        parser.add_argument(
            '--duracion',
            type=float,
            default=0.0,
            help='Duración total en segundos. 0 (default) = una sola posición y termina.',
        )
        parser.add_argument(
            '--jitter',
            type=float,
            default=15.0,
            help='Desplazamiento aleatorio en metros alrededor del punto base (0 = fijo).',
        )
        parser.add_argument('--lat', type=float, default=None, help='Latitud base (si no, usa la última posición).')
        parser.add_argument('--lng', type=float, default=None, help='Longitud base (si no, usa la última posición).')

    def _resolver_nino(self, valor):
        if valor.isdigit():
            try:
                return Nino.objects.get(pk=int(valor))
            except Nino.DoesNotExist as exc:
                raise CommandError(f'No existe un niño con id={valor}.') from exc

        qs = Nino.objects.filter(nombre=valor)
        total = qs.count()
        if total == 0:
            raise CommandError(f'No existe un niño con nombre {valor!r}.')
        if total > 1:
            ids = ', '.join(str(n.id_nino) for n in qs)
            raise CommandError(f'Hay varios niños con nombre {valor!r} (ids: {ids}). Usá --nino <id>.')
        return qs.first()

    def _dispositivo(self, nino):
        dispositivo, _ = Dispositivo.objects.get_or_create(
            id_nino=nino,
            defaults={
                'imei': f'APP-{nino.id_nino}',
                'modelo': 'Miraki Sim',
                'estado': 'vinculado',
                'activo': True,
            },
        )
        if not dispositivo.activo:
            dispositivo.activo = True
            dispositivo.save(update_fields=['activo'])
        return dispositivo

    def _base_coords(self, nino, options):
        if options['lat'] is not None and options['lng'] is not None:
            return options['lat'], options['lng']
        last = Posicion.objects.filter(id_dispositivo__id_nino=nino).order_by('-fecha_posicion').first()
        if last is None:
            raise CommandError(
                f'{nino.nombre} no tiene posiciones previas; pasá --lat y --lng para fijar el punto base.'
            )
        return float(last.latitud), float(last.longitud)

    def _jittered(self, lat, lng, jitter_m):
        if jitter_m <= 0:
            return lat, lng
        d_lat = jitter_m / 111_320.0
        cos_lat = math.cos(math.radians(lat)) or 1e-9
        d_lng = jitter_m / (111_320.0 * cos_lat)
        return lat + random.uniform(-d_lat, d_lat), lng + random.uniform(-d_lng, d_lng)

    def handle(self, *args, **options):
        nino = self._resolver_nino(options['nino'])
        dispositivo = self._dispositivo(nino)
        base_lat, base_lng = self._base_coords(nino, options)
        jitter = options['jitter']
        intervalo = max(options['intervalo'], 0.0)
        duracion = options['duracion']

        generadas = 0
        inicio = time.monotonic()
        while True:
            lat, lng = self._jittered(base_lat, base_lng, jitter)
            ahora = timezone.now()
            Posicion.objects.create(
                id_dispositivo=dispositivo,
                latitud=round(lat, 6),
                longitud=round(lng, 6),
                ubicacion=Point(lng, lat, srid=4326),
                velocidad=round(random.uniform(0, 3), 2),
                bateria=random.randint(60, 100),
                fecha_posicion=ahora,
            )
            generadas += 1
            self.stdout.write(f'[{generadas}] {ahora.isoformat()} -> ({lat:.6f}, {lng:.6f})')

            if duracion <= 0 or (time.monotonic() - inicio) >= duracion:
                break
            time.sleep(intervalo)

        self.stdout.write(
            self.style.SUCCESS(f'Listo: {generadas} posición(es) generada(s) para {nino.nombre} (id={nino.id_nino}).')
        )
