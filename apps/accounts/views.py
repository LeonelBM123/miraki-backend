from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .permissions import IsSuperAdmin
from .models import BitacoraAcceso, Rol
from .serializers import (
    BitacoraAccesoSerializer,
    BitacoraTokenObtainPairSerializer,
    ChangePasswordSerializer,
    LogoutRequestSerializer,
    RegisterAccountRequestSerializer,
    RegisterResponseSerializer,
    RegisterSerializer,
    RolSerializer,
    UsuarioSerializer,
)
from .services.auth import record_logout
from .services.registration import register_account

Usuario = get_user_model()


class RolViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    permission_classes = [IsSuperAdmin]


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsSuperAdmin]


class BitacoraAccesoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BitacoraAcceso.objects.all().order_by('-fecha_evento')
    serializer_class = BitacoraAccesoSerializer
    permission_classes = [IsSuperAdmin]


class LoginView(TokenObtainPairView):
    serializer_class = BitacoraTokenObtainPairSerializer


@extend_schema(
    request=RegisterAccountRequestSerializer,
    responses={201: RegisterResponseSerializer},
)
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterAccountRequestSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = register_account(data=serializer.validated_data, request=request)
        return Response(RegisterResponseSerializer(result).data, status=status.HTTP_201_CREATED)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=ChangePasswordSerializer, responses={200: None})
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Contraseña actualizada correctamente.'})


class LogoutView(APIView):
    """Invalida el refresh token (blacklist) y registra el evento en BitacoraAcceso."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=LogoutRequestSerializer, responses={200: None})
    def post(self, request):
        serializer = LogoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh = serializer.validated_data['refresh']
        try:
            RefreshToken(refresh).blacklist()
        except TokenError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        record_logout(usuario=request.user, request=request)
        return Response({'detail': 'Sesión cerrada correctamente.'}, status=status.HTTP_200_OK)
