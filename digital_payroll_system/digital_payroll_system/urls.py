from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/profiles/', include('apps.profiles.urls')),
    path('api/payslips/', include('apps.payslips.urls')),
    #path('api/password-resets/', include('apps.password_resets.urls')),
    #path('api/audit-logs/', include('apps.audit_logs.urls')),
]