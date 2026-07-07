from django.urls import path
from .views import ChangePasswordView, CookieRefreshView, CsrfView, LoginView, LogoutView, MeView, RegisterView

urlpatterns = [
    path('csrf/', CsrfView.as_view(), name='auth-csrf'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', CookieRefreshView.as_view(), name='auth-refresh'),
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
]
