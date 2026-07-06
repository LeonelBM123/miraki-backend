from django.contrib.auth.models import AnonymousUser

from .models import PublicIdMixin


class AuditViewSetMixin:
    def _current_audit_user(self):
        user = getattr(self.request, 'user', None)
        if user is None or isinstance(user, AnonymousUser) or not getattr(user, 'is_authenticated', False):
            return None
        return user

    def perform_create(self, serializer):
        user = self._current_audit_user()
        serializer.save(creado_por=user, modificado_por=user)

    def perform_update(self, serializer):
        serializer.save(modificado_por=self._current_audit_user())
