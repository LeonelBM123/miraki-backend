from types import SimpleNamespace
from unittest import mock

from django.test import TestCase

from apps.alerts.services import send_push_notification
from firebase_admin.exceptions import FirebaseError


class SendPushNotificationTests(TestCase):
    def setUp(self):
        self.alerta = SimpleNamespace(
            id_alerta=7,
            id_nino_id=11,
            id_nino=SimpleNamespace(nombre='Sofía'),
            id_zona=SimpleNamespace(nombre='Zona Central'),
            tipo='salida_zona',
        )
        self.tokens = [
            SimpleNamespace(id=1, token='token-a'),
            SimpleNamespace(id=2, token='token-b'),
        ]

    @mock.patch('apps.alerts.services.messaging.send_each')
    def test_send_push_calls_firebase(self, mock_send_each):
        mock_send_each.return_value = SimpleNamespace(success_count=2, failure_count=0)

        success, failure = send_push_notification(alerta=self.alerta, tokens=self.tokens)

        self.assertEqual(success, 2)
        self.assertEqual(failure, 0)
        mock_send_each.assert_called_once()
        messages = mock_send_each.call_args.args[0]
        self.assertEqual(len(messages), 2)
        self.assertEqual([message.token for message in messages], ['token-a', 'token-b'])
        self.assertEqual(messages[0].notification.title, '🚨 Alerta de zona')

    @mock.patch('apps.alerts.services.messaging.send_each', side_effect=FirebaseError('firebase down'))
    def test_send_push_logs_failure_no_raise(self, mock_send_each):
        success, failure = send_push_notification(alerta=self.alerta, tokens=self.tokens)

        self.assertEqual(success, 0)
        self.assertEqual(failure, 2)
        mock_send_each.assert_called_once()
