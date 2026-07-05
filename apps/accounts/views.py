from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import BitacoraAcceso, Rol
from .serializers import (
    BitacoraAccesoSerializer,
    BitacoraTokenObtainPairSerializer,
    ChangePasswordSerializer,
    RegisterSerializer,
    RolSerializer,
    UsuarioSerializer,
)
from .utils import get_client_ip, get_user_agent

Usuario = get_user_model()


class RolViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer


class BitacoraAccesoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BitacoraAcceso.objects.all().order_by('-fecha_evento')
    serializer_class = BitacoraAccesoSerializer


class LoginView(TokenObtainPairView):
    serializer_class = BitacoraTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        return Response(UsuarioSerializer(usuario).data, status=status.HTTP_201_CREATED)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Contraseña actualizada correctamente.'})


class LogoutView(APIView):
    """Invalida el refresh token (blacklist) y registra el evento en BitacoraAcceso."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh = request.data.get('refresh')
        if not refresh:
            return Response({'detail': 'El campo "refresh" es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(refresh).blacklist()
        except TokenError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        BitacoraAcceso.objects.create(
            id_usuario=request.user,
            correo_intento=request.user.correo,
            tipo_evento='logout',
            direccion_ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        return Response(status=status.HTTP_205_RESET_CONTENT)
