from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import ChangePasswordView, LoginView, LogoutView, RegisterView

urlpatterns = [
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
]
