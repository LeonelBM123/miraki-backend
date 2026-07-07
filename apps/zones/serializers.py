from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers

from .models import ZonaSegura, HorarioZona, NinoZonaSegura


class HorarioZonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = HorarioZona
        fields = [
            'id_horario',
            'dia_semana',
            'hora_inicio',
            'hora_fin',
            'activo',
        ]

    def validate(self, data):
        hora_inicio = data.get('hora_inicio')
        hora_fin = data.get('hora_fin')
        if hora_inicio and hora_fin and hora_inicio >= hora_fin:
            raise serializers.ValidationError('La hora de inicio debe ser anterior a la hora de fin.')
        return data


class NinoAsociadoSerializer(serializers.ModelSerializer):
    id_nino = serializers.IntegerField(source='id_nino.pk', read_only=True)
    nombre = serializers.CharField(source='id_nino.nombre', read_only=True)
    foto_url = serializers.CharField(source='id_nino.foto_url', read_only=True)

    class Meta:
        model = NinoZonaSegura
        fields = ['id', 'id_nino', 'nombre', 'foto_url', 'activa']


class ZonaSeguraReadSerializer(serializers.ModelSerializer):
    # El polígono se expone como GeoJSON para que Leaflet lo consuma directamente
    poligono = serializers.JSONField()
    horarios = HorarioZonaSerializer(many=True, read_only=True)
    ninos_asociados = NinoAsociadoSerializer(many=True, read_only=True)

    class Meta:
        model = ZonaSegura
        fields = [
            'id_zona',
            'nombre',
            'poligono',
            'activo',
            'horarios',
            'ninos_asociados',
            'fecha_creacion',
            'fecha_modificacion',
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Convertir el objeto GEOS a un dict GeoJSON serializable
        if instance.poligono:
            import json
            ret['poligono'] = json.loads(instance.poligono.geojson)
        return ret


class ZonaSeguraWriteSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150)
    # El frontend envía el polígono como un objeto GeoJSON Polygon
    poligono = serializers.JSONField()

    def validate_poligono(self, value):
        from django.contrib.gis.geos import GEOSGeometry
        import json

        if not isinstance(value, dict):
            raise serializers.ValidationError('El polígono debe ser un objeto GeoJSON.')

        if value.get('type') != 'Polygon':
            raise serializers.ValidationError('El tipo de geometría debe ser Polygon.')

        coords = value.get('coordinates', [])
        if not coords or len(coords[0]) < 4:
            raise serializers.ValidationError(
                'Un polígono debe tener al menos 3 vértices (4 coordenadas, el primero y último coinciden).'
            )

        try:
            geom = GEOSGeometry(json.dumps(value), srid=4326)
        except Exception as exc:
            raise serializers.ValidationError(f'Geometría GeoJSON inválida: {exc}') from exc

        return geom


class ZonaSeguraUpdateSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150, required=False)
    poligono = serializers.JSONField(required=False)

    def validate_poligono(self, value):
        from django.contrib.gis.geos import GEOSGeometry
        import json

        if not isinstance(value, dict):
            raise serializers.ValidationError('El polígono debe ser un objeto GeoJSON.')

        if value.get('type') != 'Polygon':
            raise serializers.ValidationError('El tipo de geometría debe ser Polygon.')

        coords = value.get('coordinates', [])
        if not coords or len(coords[0]) < 4:
            raise serializers.ValidationError(
                'Un polígono debe tener al menos 3 vértices (4 coordenadas, el primero y último coinciden).'
            )

        try:
            geom = GEOSGeometry(json.dumps(value), srid=4326)
        except Exception as exc:
            raise serializers.ValidationError(f'Geometría GeoJSON inválida: {exc}') from exc

        return geom
