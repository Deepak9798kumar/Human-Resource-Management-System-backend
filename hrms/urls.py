"""
URL configuration for hrms project.
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.http import JsonResponse

# drf-yasg imports for Swagger/OpenAPI
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

def root_view(request):
    return JsonResponse({
        "message": "HRMS Lite API",
        "version": "1.0.0",
        "status": "running"
    })

def health_check(request):
    return JsonResponse({
        "status": "healthy"
    })


# Swagger/OpenAPI schema view
schema_view = get_schema_view(
    openapi.Info(
        title="HRMS Lite API",
        default_version='v1',
        description="API documentation for HRMS Lite",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', root_view),
    path('health/', health_check),
    path('api/', include('api.urls')),
    re_path(r'^docs/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
