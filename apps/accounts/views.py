from django.conf import settings
from django.contrib.auth import get_user_model
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common.mixins import AuditViewSetMixin

from .cookies import clear_auth_cookies, set_auth_cookies
from .models import BitacoraAcceso, Rol
from .permissions import IsSuperAdmin
from .serializers import (
    BitacoraAccesoSerializer,
    BitacoraTokenObtainPairSerializer,
    ChangePasswordSerializer,
    DetailResponseSerializer,
    LoginResponseSerializer,
    LogoutRequestSerializer,
    RegisterAccountRequestSerializer,
    RegisterResponseSerializer,
    RolSerializer,
    UsuarioAuthResponseSerializer,
    UsuarioSerializer,
)
from .services.auth import record_logout
from .services.registration import register_account

Usuario = get_user_model()


class RolViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    permission_classes = [IsSuperAdmin]


class UsuarioViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsSuperAdmin]


class BitacoraAccesoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BitacoraAcceso.objects.all().order_by('-fecha_evento')
    serializer_class = BitacoraAccesoSerializer
    permission_classes = [IsSuperAdmin]


class LoginView(TokenObtainPairView):
    serializer_class = BitacoraTokenObtainPairSerializer
    throttle_scope = 'auth'

    @extend_schema(request=BitacoraTokenObtainPairSerializer, responses={200: LoginResponseSerializer})
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = serializer.validated_data
        response = Response({
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'usuario': tokens['usuario'],
        }, status=status.HTTP_200_OK)
        set_auth_cookies(response, access=tokens['access'], refresh=tokens['refresh'])
        return response


@extend_schema(request=RegisterAccountRequestSerializer, responses={201: RegisterResponseSerializer})
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterAccountRequestSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'auth'

    @method_decorator(csrf_protect)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = register_account(data=serializer.validated_data, request=request)
        return Response(RegisterResponseSerializer(result).data, status=status.HTTP_201_CREATED)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=ChangePasswordSerializer, responses={200: DetailResponseSerializer})
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Contraseña actualizada correctamente.'})


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: UsuarioAuthResponseSerializer})
    def get(self, request):
        return Response(UsuarioAuthResponseSerializer(request.user).data)


class CookieRefreshView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=None, responses={200: DetailResponseSerializer})
    def post(self, request):
        refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME) or request.data.get('refresh')
        if not refresh:
            raise InvalidToken('Refresh token no encontrado.')

        serializer = TokenRefreshSerializer(data={'refresh': refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(str(exc)) from exc

        validated_data = serializer.validated_data
        response = Response({
            'access': validated_data.get('access'),
            'refresh': validated_data.get('refresh'),
            'detail': 'Token renovado correctamente.',
        }, status=status.HTTP_200_OK)
        set_auth_cookies(
            response,
            access=validated_data.get('access'),
            refresh=validated_data.get('refresh'),
        )
        return response


class CsrfView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @method_decorator(ensure_csrf_cookie)
    @extend_schema(responses={200: DetailResponseSerializer})
    def get(self, request):
        get_token(request)
        return Response({'detail': 'CSRF cookie initialized.'})


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=LogoutRequestSerializer, responses={200: DetailResponseSerializer})
    def post(self, request):
        serializer = LogoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME) or serializer.validated_data.get('refresh')
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass

        record_logout(usuario=request.user, request=request)
        response = Response({'detail': 'Sesión cerrada correctamente.'}, status=status.HTTP_200_OK)
        clear_auth_cookies(response)
        return response
