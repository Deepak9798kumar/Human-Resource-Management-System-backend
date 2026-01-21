"""
URL configuration for hrms project.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

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

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', root_view),
    path('health/', health_check),
    path('api/', include('api.urls')),
]
