from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/v1/auth/', include('apps.accounts.auth_urls')),
    path('api/v1/accounts/', include('apps.accounts.urls')),
    path('api/v1/children/', include('apps.children.urls')),
    path('api/v1/institutions/', include('apps.institutions.urls')),
    path('api/v1/', include('apps.dispositivos.urls')),
    path('api/v1/', include('apps.alerts.urls')),
    path('api/v1/audit/', include('apps.audit.urls')),
    path('api/v1/zones/', include('apps.zones.urls')),

    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
