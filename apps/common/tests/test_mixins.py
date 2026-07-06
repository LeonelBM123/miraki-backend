from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase
from rest_framework import viewsets

from apps.common.mixins import AuditViewSetMixin


class DummyAuditViewSet(AuditViewSetMixin, viewsets.GenericViewSet):
    pass


class AuditViewSetMixinTests(SimpleTestCase):
    def test_perform_create_populates_audit_fields(self):
        user = SimpleNamespace(is_authenticated=True)
        view = DummyAuditViewSet()
        view.request = SimpleNamespace(user=user)
        serializer = mock.Mock()

        view.perform_create(serializer)

        serializer.save.assert_called_once_with(creado_por=user, modificado_por=user)

    def test_perform_update_populates_modified_by_only(self):
        user = SimpleNamespace(is_authenticated=True)
        view = DummyAuditViewSet()
        view.request = SimpleNamespace(user=user)
        serializer = mock.Mock()

        view.perform_update(serializer)

        serializer.save.assert_called_once_with(modificado_por=user)


class AuditViewSetMixinAnonymousTests(SimpleTestCase):
    def test_anonymous_user_maps_to_none(self):
        view = DummyAuditViewSet()
        view.request = SimpleNamespace(user=SimpleNamespace(is_authenticated=False))
        serializer = mock.Mock()

        view.perform_create(serializer)

        serializer.save.assert_called_once_with(creado_por=None, modificado_por=None)
