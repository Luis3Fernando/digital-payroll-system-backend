from rest_framework.routers import DefaultRouter
from .views import PayslipUploadViewSet

router = DefaultRouter()
router.register(r'', PayslipUploadViewSet, basename='payslips')

urlpatterns = router.urls
