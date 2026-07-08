# Handoff: Child-Facing App (Miraki Niño)

## Objective

Create a standalone Flutter application for the child's device (tablet/phone) that:
- Requires **no login** — the tutor provisions the device via a **pairing code**
- Shows the child's **current monitoring status**
- Provides an **SOS button** for emergencies
- Connects to the existing **Miraki backend** via WebSocket + REST

---

## Project Structure

```
miraki_mobile/          ← existing tutor app (parental)
miraki_kid/             ← NEW: child-facing app (this handoff)
miraki-backend/         ← existing backend (add pairing endpoints)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Flutter 3.x |
| State | Riverpod (same as parent app) |
| HTTP | Dio |
| WebSocket | web_socket_channel |
| Maps | flutter_map + OSM (same stack) |
| Local | shared_preferences (token storage) |
| Backend | Django 5.2 + DRF + PostGIS (existing) |

---

## Backend — Pairing System

### New Model: `CodigoPareo`

```python
class CodigoPareo(models.Model):
    codigo = models.CharField(max_length=8, unique=True)  # e.g. "A3K9M2"
    id_nino = models.ForeignKey(Nino, on_delete=models.CASCADE)
    id_tutor = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()  # 30 min from creation
    usado = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'codigo_pareo'
```

### New Endpoints

| Method | Endpoint | Purpose | Auth |
|--------|----------|---------|------|
| POST | `/api/v1/pareo/crear/` | Tutor generates pairing code | Tutor JWT |
| POST | `/api/v1/pareo/vincular/` | Child app links with code | None (public) |
| GET | `/api/v1/pareo/estado/{nino_id}/` | Child app gets status | Token from pairing |

### POST `/api/v1/pareo/crear/`
- **Auth**: Tutor JWT required
- **Request**: `{"id_nino": 1}`
- **Response**: `{"codigo": "A3K9M2", "expira_en": "2026-07-08T13:00:00Z"}`
- **Logic**: 
  - Validate the child belongs to this tutor
  - Generate 6-char alphanumeric random code
  - Set expiry to 30 minutes
  - Deactivate any previous unused codes for this child
  - Save and return code

### POST `/api/v1/pareo/vincular/`
- **Auth**: None (public — this is the pairing step)
- **Request**: `{"codigo": "A3K9M2"}`
- **Response**: `{"token": "pairing_jwt_token", "id_nino": 1, "nombre": "Ana", "tutor_nombre": "Tutor Prueba"}`
- **Logic**:
  - Find matching `CodigoPareo` where `usado=False` AND `expira_en > now()`
  - Mark as `usado=True`
  - Generate a short-lived JWT (7 days) with `kid_device` scope and `nino_id` claim
  - Return token + child info + tutor name

### GET `/api/v1/ninos/{id}/estado/`
- **Auth**: Pairing token (custom auth class: `PairingTokenAuthentication`)
- **Response**: 
```json
{
  "id_nino": 1,
  "nombre": "Ana",
  "tutor_nombre": "Tutor Prueba",
  "activo": true,
  "ultima_posicion": {"lat": -17.78, "lng": -63.18, "fecha": "2026-07-08T12:00:00Z"},
  "zona_actual": {"nombre": "Zona Prueba", "dentro": true},
  "alertas_recientes": 0
}
```

### Backend — New Auth Class

```python
# apps/accounts/authentication.py
class PairingTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        jwt_value = request.headers.get('X-Kid-Token')
        if not jwt_value:
            return None
        # Validate JWT with 'kid_device' scope
        # Extract nino_id, return (nino, None)
```

---

## Flutter App — "Miraki Niño"

### App Name & Identity
- App name: `Miraki Niño`
- Package: `com.miraki.kid`
- Icon: Child-friendly design
- Theme: Colorful, large buttons, high contrast (designed for children)

### Screens

#### 1. PairingScreen (first launch)
```
┌─────────────────────────────┐
│     ¡Hola! Soy Miraki       │
│                             │
│   [👶 Ilustración niño]    │
│                             │
│  Pedile a tu mamá o papá    │
│  que ingrese este código    │
│  en su teléfono             │
│                             │
│  ┌─────────────────────┐    │
│  │  _ _ _ _ _ _        │    │
│  └─────────────────────┘    │
│                             │
│  [  CONECTAR  ]            │
│                             │
│  Código de 6 caracteres     │
└─────────────────────────────┘
```

- State: `PairingCode(String code) | PairingLoading | Paired(childName, tutorName) | Error(String)`
- On submit: POST `/api/v1/pareo/vincular/` with code
- On success: save token to `shared_preferences`, navigate to HomeScreen
- On error: show error message

#### 2. HomeScreen (main screen)
```
┌─────────────────────────────┐
│  ←→  ¡Hola, [Nombre]!      │
│                             │
│    [🟢 Círculo grande]     │
│    "Estás en zona segura"   │
│         o                   │
│    [🔴 "Fuera de zona"]     │
│                             │
│  Monitoreado por:           │
│  [Tutor Nombre]             │
│                             │
│  Última ubicación:          │
│  hace 2 minutos             │
│                             │
│                             │
│  ┌─────────────────────┐    │
│  │     🆘 SOS          │    │
│  │  ¡Presiona si        │    │
│  │  necesitas ayuda!    │    │
│  └─────────────────────┘    │
│      (botón grande rojo)    │
└─────────────────────────────┘
```

- **WebSocket connection**: Connect to existing `ws/tracking/?token=<pairing_token>` (modify backend consumer to also accept pairing tokens with nino scope)
- **Status polling**: GET `/api/v1/ninos/{id}/estado/` every 30s as fallback
- **SOS button**: POST `/api/v1/alertas/sos/` creates alert with `tipo=sos`
- **Zona status**: Green if inside safe zone, red if outside
- **Backend change**: Allow `TrackingConsumer` to authenticate with pairing token too

#### 3. SettingsScreen (optional)
- Show pairing code again
- Disconnect device
- App info

### Flutter Architecture

```
lib/
├── main.dart                    # App entry, check stored token
├── app.dart                     # MaterialApp with GoRouter
├── core/
│   ├── api/
│   │   ├── api_config.dart      # Same base URL as parent app
│   │   └── pairing_client.dart  # Dio with X-Kid-Token header
│   ├── theme/
│   │   └── kid_theme.dart       # Child-friendly theme
│   └── storage/
│       └── kid_preferences.dart # shared_preferences wrapper
├── data/
│   ├── models/
│   │   ├── kid_status.dart      # EstadoNino freezed model
│   │   └── pairing_result.dart  # ResultadoPareo freezed model
│   └── services/
│       ├── pairing_service.dart # Dio calls for pareo
│       └── child_status_service.dart  # Polling + WS
├── domain/
│   └── providers/
│       ├── pairing_provider.dart
│       └── status_provider.dart
└── ui/
    ├── pairing/
    │   ├── view_models/pairing_view_model.dart
    │   └── views/pairing_screen.dart
    ├── home/
    │   ├── view_models/home_view_model.dart
    │   └── views/home_screen.dart
    └── widgets/
        ├── status_indicator.dart
        ├── sos_button.dart
        └── tutor_info_card.dart
```

### Dependencies (pubspec.yaml)

```yaml
dependencies:
  flutter:
    sdk: flutter
  dio: ^5.9.0
  riverpod: ^2.6.1
  flutter_riverpod: ^2.6.1
  riverpod_annotation: ^2.6.1
  go_router: ^16.2.0
  shared_preferences: ^2.3.0
  web_socket_channel: ^3.0.1
  json_annotation: ^4.9.0
  freezed_annotation: ^2.4.4

dev_dependencies:
  flutter_test:
    sdk: flutter
  build_runner: ^2.4.14
  freezed: ^2.5.7
  json_serializable: ^6.9.4
  mocktail: ^1.0.4
```

---

## Backend Changes Required

All changes go in the existing `miraki-backend/` repo:

### 1. New App or Extend Existing?

- Option A: New `apps/pareo/` app (cleaner separation) — **RECOMMENDED**
- Option B: Add to `apps/alerts/` (simpler, already has models)

**Recommendation**: Option A — new `apps/pareo/` app with `CodigoPareo` model + pairing views.

### 2. Files to Create

| File | Purpose |
|------|---------|
| `apps/pareo/__init__.py` | Package marker |
| `apps/pareo/apps.py` | AppConfig named `AppsPareoConfig` |
| `apps/pareo/models.py` | `CodigoPareo` model |
| `apps/pareo/serializers.py` | `CrearPareoSerializer`, `VincularPareoSerializer` |
| `apps/pareo/services.py` | `generar_codigo()`, `vincular_dispositivo()` |
| `apps/pareo/views.py` | `CrearCodigoView`, `VincularDispositivoView`, `EstadoNinoView` |
| `apps/pareo/urls.py` | 3 endpoints |
| `apps/pareo/tests/test_pareo_flows.py` | Tests for pairing flow |
| `apps/pareo/tests/__init__.py` | Package marker |
| `apps/pareo/migrations/0001_initial.py` | Initial migration |

### 3. Files to Modify

| File | Change |
|------|--------|
| `config/settings/base.py` | Add `apps.pareo` to INSTALLED_APPS |
| `config/urls.py` | Add `path('api/v1/', include('apps.pareo.urls'))` |
| `apps/alerts/consumers.py` | Modify `TrackingConsumer` to accept pairing tokens (check `kid_device` scope in JWT) |
| `apps/alerts/views.py` | Add `SOSView` or action to create SOS alert from child app |
| `apps/alerts/urls.py` | Add `alertas/sos/` endpoint |

### 4. Pairing Token JWT

Use `rest_framework_simplejwt` to generate pairing tokens:

```python
from rest_framework_simplejwt.tokens import AccessToken

def generar_token_pareo(nino):
    token = AccessToken()
    token['nino_id'] = nino.id_nino
    token['tutor_id'] = nino.id_tutor.id_usuario_id
    token['scope'] = 'kid_device'
    token.set_exp(lifetime=timezone.timedelta(days=7))
    return str(token)
```

### 5. Authentication Class

```python
# apps/accounts/authentication.py
from rest_framework.authentication import BaseAuthentication
from rest_framework_simplejwt.tokens import AccessToken

class PairingTokenAuthentication(BaseAuthentication):
    keyword = 'X-Kid-Token'
    
    def authenticate(self, request):
        token = request.headers.get(self.keyword)
        if not token:
            return None
        try:
            access = AccessToken(token)
            if access.get('scope') != 'kid_device':
                return None
            nino_id = access.get('nino_id')
            from apps.children.models import Nino
            nino = Nino.objects.get(pk=nino_id)
            return (nino, token)
        except Exception:
            return None
```

---

## WebSocket Changes

### Current: `ws/tracking/?token=<jwt>` (tutor JWT)
### New: `ws/tracking/?token=<pairing_token>` (kid device pairing token)

Modify `TrackingConsumer.connect()` to:
1. Try tutor JWT first (existing)
2. If that fails, try pairing token (check `kid_device` scope)
3. If pairing token, subscribe to `tracking-{nino_id}` group (not tutor group)

---

## SOS Alert Endpoint

Add to `apps/alerts/views.py`:

```python
@action(detail=False, methods=['post'])
def sos(self, request):
    # Create SOS alert for this child (authenticated via pairing token)
    nino = request.user  # PairingTokenAuthentication returns Nino instance
    alerta = Alerta.objects.create(
        id_nino=nino,
        tipo=Alerta.TipoAlerta.SOS,
    )
    return Response(AlertaReadSerializer(alerta).data, status=201)
```

---

## Implementation Order

### Phase A: Backend Pairing (Day 1)
1. Create `apps/pareo/` with model + migration
2. Implement `POST /pareo/crear/` and `POST /pareo/vincular/`
3. Add `PairingTokenAuthentication` class
4. Modify `config/settings/base.py` and `config/urls.py`
5. Tests

### Phase B: Backend Status + SOS (Day 1-2)
1. Add `GET /ninos/{id}/estado/` endpoint
2. Add SOS endpoint to alerts
3. Modify `TrackingConsumer` to accept pairing tokens
4. Tests

### Phase C: Flutter App (Day 2-4)
1. Create new Flutter project `miraki_kid`
2. Implement `PairingScreen` with code input
3. Implement `HomeScreen` with status display
4. Implement SOS button
5. Implement WebSocket connection for live updates
6. Implement settings/disconnect
7. Tests

### Phase D: Integration (Day 4-5)
1. End-to-end test: tutor creates code → kid pairs → see status
2. Test SOS flow
3. Test WebSocket reconnect
4. Polish UI

---

## Existing Code to Reference

### Must-read files:
- `miraki_mobile/lib/data/services/alerts_service.dart` — Dio pattern
- `miraki_mobile/lib/domain/providers/auth_provider.dart` — token storage pattern
- `miraki_mobile/lib/ui/features/map/views/map_screen.dart` — flutter_map usage
- `miraki-backend/apps/alerts/consumers.py` — WebSocket consumer (modify for pairing)
- `miraki-backend/apps/alerts/views.py` — AlertViewSet pattern
- `miraki-backend/apps/alerts/urls.py` — URL routing
- `miraki-backend/apps/accounts/authentication.py` — Auth classes (create if not exists)
- `miraki-backend/apps/alerts/models.py` — Alerta model (for SOS)
- `miraki-backend/apps/children/models.py` — Nino model
- `miraki-backend/config/urls.py` — Root URL config

### CLAUDE.md:
- `miraki-backend/CLAUDE.md` — Project conventions (db_table, db_column naming, etc.)

---

## Testing

### Backend (pytest)
- `test_crear_codigo`: tutor creates code, returns valid 6-char code
- `test_vincular_codigo_valido`: use code, get pairing token
- `test_vincular_codigo_expirado`: expired code returns 400
- `test_vincular_codigo_usado`: already used code returns 400
- `test_vincular_sin_codigo`: missing code returns 400
- `test_estado_nino`: get status with pairing token
- `test_estado_nino_sin_token`: 401
- `test_sos_alert`: create SOS via pairing token

### Flutter (flutter test)
- `pairing_screen_test`: input code, submit, loading, error states
- `home_screen_test`: shows child name, tutor name, status indicator
- `sos_button_test`: tap SOS, confirm dialog, success snackbar
- `status_provider_test`: state transitions Loading→Loaded→Error

---

## Verification Checklist

- [ ] Tutor can generate pairing code from API
- [ ] Child app can pair with 6-char code
- [ ] Child app receives valid JWT
- [ ] Child app shows correct status (inside/outside zone)
- [ ] WebSocket connects and receives real-time updates
- [ ] SOS button creates alert visible in tutor's app
- [ ] Disconnect removes token from device
- [ ] Expired code returns error
- [ ] Code can only be used once
- [ ] Non-existent code returns error

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Auth for child app | JWT via pairing code | No user/pass required, simple, secure |
| Pairing code length | 6 chars alphanumeric | Easy to type, 2.1B combinations |
| Code expiry | 30 minutes | Short enough to be secure, long enough to use |
| Child app token lifetime | 7 days | Usable for a school week, re-pair if expired |
| WebSocket group | `tracking-{nino_id}` | Existing infrastructure, extend consumer |
| SOS auth | Pairing token | Only paired device can send SOS |
| UI style | Colorful, large, simple | Designed for children (pre-literate OK) |
| Status updates | WebSocket + REST fallback | Same pattern as parent app |

---

## Open Questions (Discuss with Team)

1. Should the child app show a map or just a status indicator? (Map = more complex)
2. Should SOS require confirmation? (Yes, prevent accidental triggers)
3. Should we support multiple children on one device? (Not initially)
4. Should the child app work offline? (Show last known status, queue SOS)
5. Battery optimization: how often should the child app poll?

---

## Notes

- The Flutter project should be created with `flutter create --org com.miraki miraki_kid`
- Do NOT copy the parent app's code — this is a separate app with different UX
- The child app should be visually distinct from the parent app (child-friendly)
- All text should be in Spanish (the children are Bolivian)
- Use large fonts (minimum 16sp) and big touch targets (minimum 48px)
