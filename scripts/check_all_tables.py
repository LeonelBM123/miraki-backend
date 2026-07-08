import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.base'
import django; django.setup()
from django.db import connection

tables = ['posicion', 'alerta', 'dispositivo_token']
for table in tables:
    c = connection.cursor()
    c.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' ORDER BY ordinal_position")
    print(f"\n=== {table} ===")
    for r in c.fetchall():
        print(f"  {r[0]}")
