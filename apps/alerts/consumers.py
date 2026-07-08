from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

Usuario = get_user_model()


class TrackingConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.group_name = None
        self.tutor_id = None
        self.nino_id = None

        query_params = parse_qs(self.scope.get('query_string', b'').decode())
        token = query_params.get('token', [None])[0]
        if not token:
            await self.close(code=4401)
            return

        if await self._connect_with_tutor_jwt(token):
            return

        if await self._connect_with_pairing_token(token):
            return

        await self.close(code=4401)

    async def _connect_with_tutor_jwt(self, token):
        try:
            access = AccessToken(token)
            user_id = access['user_id']
            user = await database_sync_to_async(Usuario.objects.select_related('id_rol').get)(id_usuario=user_id)
        except Exception:
            return False

        if user.id_rol.nombre_rol != 'Tutor':
            return False

        self.tutor_id = user.id_usuario
        self.group_name = f'tracking-{self.tutor_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        return True

    async def _connect_with_pairing_token(self, token):
        try:
            access = AccessToken(token)
            if access.get('scope') != 'kid_device':
                return False

            nino_id = access.get('nino_id')
            if not nino_id:
                return False
        except Exception:
            return False

        self.nino_id = int(nino_id)
        self.group_name = f'tracking-{self.nino_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        return True

    async def disconnect(self, close_code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        if content.get('type') != 'posicion_update' or not self.group_name:
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'posicion.update',
                'child_id': content.get('child_id'),
                'nombre': content.get('nombre'),
                'latitud': content.get('latitud'),
                'longitud': content.get('longitud'),
                'velocidad': content.get('velocidad'),
                'bateria': content.get('bateria'),
                'fecha_posicion': content.get('fecha_posicion'),
            },
        )

    async def posicion_update(self, event):
        await self.send_json(
            {
                'type': 'position',
                'child_id': event['child_id'],
                'nombre': event.get('nombre'),
                'latitud': event['latitud'],
                'longitud': event['longitud'],
                'velocidad': event.get('velocidad'),
                'bateria': event.get('bateria'),
                'fecha_posicion': event.get('fecha_posicion'),
            }
        )
