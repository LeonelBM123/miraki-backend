from rest_framework.permissions import BasePermission


def get_role_name(user):
    if not user or not user.is_authenticated:
        return None
    role = getattr(user, 'id_rol', None)
    return getattr(role, 'nombre_rol', None)


class IsSuperAdmin(BasePermission):
    message = 'Se requiere rol SuperAdmin.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return get_role_name(user) == 'SuperAdmin' or bool(getattr(user, 'is_superuser', False))


class IsTutor(BasePermission):
    message = 'Se requiere rol Tutor.'

    def has_permission(self, request, view):
        return get_role_name(request.user) == 'Tutor'


class IsAdminCentro(BasePermission):
    message = 'Se requiere rol AdminCentro.'

    def has_permission(self, request, view):
        return get_role_name(request.user) == 'AdminCentro'
