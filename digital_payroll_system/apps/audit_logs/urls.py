from rest_framework.routers import DefaultRouter
from .views import AuditDashboardViewSet

router = DefaultRouter()
router.register(r'', AuditDashboardViewSet, basename='audit-logs')

urlpatterns = router.urls
