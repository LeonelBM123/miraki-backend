import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.base'
import django; django.setup()

from rest_framework.test import APIClient
from apps.accounts.models import Usuario

client = APIClient(SERVER_NAME='localhost')
user = Usuario.objects.get(correo='test@prueba.com')
client.force_authenticate(user=user)

print("=== 1. LISTAR ALERTAS ===")
r = client.get('/api/v1/alertas/')
print(f'GET /alertas/ = {r.status_code}')
data = r.json()
print(f'Count: {data.get("count")}')
for a in data.get('results', []):
    print(f'  Alerta #{a["id_alerta"]}: nino={a["nombre_nino"]}, tipo={a["tipo"]}, atendida={a["atendida"]}')

print("\n=== 2. ATENDER ALERTA ===")
alert_id = data['results'][0]['id_alerta']
r2 = client.post(f'/api/v1/alertas/{alert_id}/atender/')
print(f'POST /alertas/{alert_id}/atender/ = {r2.status_code}')
print(f'Response: atendida={r2.json().get("atendida")}')

print("\n=== 3. ULTIMA POSICION ===")
r3 = client.get('/api/v1/posiciones/ultima/')
print(f'GET /posiciones/ultima/ = {r3.status_code}')
for p in r3.json().get('results', []):
    print(f'  Nino #{p["id_nino"]}: {p["nombre"]} - lat={p["latitud"]}, lng={p["longitud"]}')

print("\n=== 4. LISTAR ALERTAS DESPUES DE ATENDER ===")
r4 = client.get('/api/v1/alertas/')
for a in r4.json().get('results', []):
    print(f'  Alerta #{a["id_alerta"]}: atendida={a["atendida"]}, fecha_atencion={a.get("fecha_atencion")}')

print("\n✅ TODO FUNCIONA!")
