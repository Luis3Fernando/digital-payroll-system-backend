from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/profiles/', include('apps.profiles.urls')),
    path('api/payslips/', include('apps.payslips.urls')),
    #path('api/password-resets/', include('apps.password_resets.urls')),
    #path('api/audit-logs/', include('apps.audit_logs.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)