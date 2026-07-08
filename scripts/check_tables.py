import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.base'
import django; django.setup()
from django.db import connection
from apps.alerts.models import Posicion

# Check the DB table
c = connection.cursor()
c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'posicion' ORDER BY ordinal_position")
cols = [r[0] for r in c.fetchall()]
print("Columns in posicion table:", cols)

# Check model fields
print("Model fields in Posicion:")
for f in Posicion._meta.get_fields():
    print(f"  {f.name} ({f.get_internal_type()}) db_column={getattr(f, 'db_column', 'N/A')}")

# Check if created_by field exists
if 'creado_por' in cols:
    print("\n✅ creado_por column exists in DB")
else:
    print("\n❌ creado_por column MISSING in DB")
