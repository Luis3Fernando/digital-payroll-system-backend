from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils.timezone import now
from django.db.models import Count, Q, Max
from datetime import date

from apps.profiles.models import Profile
from apps.payslips.models import Payslip
from common.response_handler import APIResponse
from .models import AuditLog

class AuditDashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='dashboard-stats')
    def dashboard_stats(self, request):
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response(
                APIResponse.error("No tiene permisos para acceder a esta información.", code=status.HTTP_403_FORBIDDEN),
                status=status.HTTP_403_FORBIDDEN
            )

        total_users = Profile.objects.count()
        today_registered = Profile.objects.filter(created_at__date=date.today()).count()

        payslips_generated = Payslip.objects.filter(view_status='generated')
        total_generated = payslips_generated.count()
        last_generated = payslips_generated.aggregate(last=Max('created_at'))['last']

        total_unseen = Payslip.objects.filter(view_status='unseen').count()

        payslips_seen = Payslip.objects.filter(view_status='seen')
        total_seen = payslips_seen.count()
        last_seen = payslips_seen.aggregate(last=Max('updated_at'))['last']

        data = {
            "users": {
                "total": total_users,
                "today_registered": today_registered
            },
            "payslips_generated": {
                "total": total_generated,
                "last_generated": last_generated
            },
            "payslips_unseen": {
                "total": total_unseen
            },
            "payslips_seen": {
                "total": total_seen,
                "last_seen": last_seen
            }
        }

        return Response(
            APIResponse.success(
                data=data,
                message="Estadísticas obtenidas correctamente."
            ),
            status=status.HTTP_200_OK
        )
