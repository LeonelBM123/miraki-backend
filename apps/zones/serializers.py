from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers

from .models import ZonaSegura


class ZonaSeguraReadSerializer(serializers.ModelSerializer):
    # El polígono se expone como GeoJSON para que Leaflet lo consuma directamente
    poligono = serializers.JSONField()

    class Meta:
        model = ZonaSegura
        fields = [
            'id_zona',
            'nombre',
            'poligono',
            'activo',
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
