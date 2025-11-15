from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils.timezone import now
from django.db.models import Count, Q, Max, Avg, Value
from django.db.models.functions import ExtractHour
from datetime import date, timedelta
from apps.profiles.models import Profile
from apps.payslips.models import Payslip
from common.response_handler import APIResponse
from .models import AuditLog
from django.db.models.functions import Concat
from django.utils.dateparse import parse_datetime
from django.core.paginator import Paginator
from datetime import datetime
from django.db.models import F, ExpressionWrapper, DurationField

class AuditDashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated] 

    @action(detail=False, methods=['get'], url_path='dashboard-stats')
    def dashboard_stats(self, request):
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response(
                APIResponse.error("No tiene permisos para acceder a esta información.", code=status.HTTP_403_FORBIDDEN),
                status=status.HTTP_403_FORBIDDEN
            )

        today = date.today()

        total_users = Profile.objects.count()
        today_registered = Profile.objects.filter(created_at__date=today).count()

        users_never_seen = (
            Profile.objects
            .filter(resigned=False)
            .annotate(seen_count=Count('payslips', filter=Q(payslips__view_status='seen')))
            .filter(seen_count=0)
            .count()
        )

        inactive_users = Profile.objects.filter(
            last_login__lt=today - timedelta(days=15),
            resigned=False
        ).count()
        
        payslips_generated = Payslip.objects.filter(view_status='generated')
        total_generated = payslips_generated.count()
        last_generated = payslips_generated.aggregate(last=Max('created_at'))['last']

        total_unseen = Payslip.objects.filter(view_status='unseen').count()

        payslips_seen = Payslip.objects.filter(view_status='seen')
        total_seen = payslips_seen.count()
        last_seen = payslips_seen.aggregate(last=Max('updated_at'))['last']

        view_rate = (total_seen / max(total_generated + total_unseen, 1)) * 100

        avg_open_time = payslips_seen.annotate(
            time_to_open=ExpressionWrapper(
                F('updated_at') - F('created_at'),
                output_field=DurationField()
            )
        ).aggregate(avg=Avg('time_to_open'))['avg']

        logs_today = AuditLog.objects.filter(created_at__date=today).count()

        top_users = (
            AuditLog.objects
            .annotate(
                full_name=Concat(
                    'profile__user__first_name',
                    Value(' '),
                    'profile__user__last_name'
                )
            )
            .values('full_name')
            .annotate(total=Count('id'))
            .order_by('-total')[:5]
        )

        raw_activity = (
            AuditLog.objects
            .filter(created_at__date=today)
            .annotate(hour=ExtractHour('created_at'))
            .values('hour')
            .annotate(total=Count('id'))
        )

        activity_dict = {item['hour']: item['total'] for item in raw_activity}
        current_hour = datetime.now().hour
        hourly_activity = [
            {
                "hour": hour,
                "total": activity_dict.get(hour, 0)
            }
            for hour in range(0, current_hour + 1)
        ]

        data = {
            "users": {
                "total": total_users,
                "today_registered": today_registered,
                "never_seen_payslips": users_never_seen,
                "inactive_users": inactive_users
            },
            "payslips": {
                "generated": {
                    "total": total_generated,
                    "last_generated": last_generated
                },
                "unseen": {
                    "total": total_unseen
                },
                "seen": {
                    "total": total_seen,
                    "last_seen": last_seen,
                    "avg_open_time": avg_open_time
                },
                "view_rate": f"{view_rate:.2f}%"
            },
            "engagement": {
                "logs_today": logs_today,
                "top_users": list(top_users),
                "hourly_activity": list(hourly_activity),
            }
        }

        return Response(
            APIResponse.success(
                data=data,
                message="Dashboard unificado obtenido correctamente."
            ),
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='logs')
    def logs(self, request):
        """
        Endpoint para obtener los registros de auditoría:
        - Filtrado por rango de fechas
        - Filtrado por usuario
        - Filtrado por acción
        - Paginación
        """
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response(
                APIResponse.error("No tiene permisos para acceder a esta información.", 
                                  code=status.HTTP_403_FORBIDDEN),
                status=status.HTTP_403_FORBIDDEN
            )

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        user_id = request.query_params.get('user_id')
        action_filter = request.query_params.get('action')

        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 20))

        logs = AuditLog.objects.all().order_by('-created_at')

        if start_date:
            logs = logs.filter(created_at__gte=start_date)

        if end_date:
            logs = logs.filter(created_at__lte=end_date)

        if user_id:
            logs = logs.filter(profile__user__id=user_id)

        if action_filter:
            logs = logs.filter(action__icontains=action_filter)

        paginator = Paginator(logs, limit)
        page_obj = paginator.get_page(page)

        results = [
            {
                "id": log.id,
                "user": log.profile.user.username if log.profile and log.profile.user else None,
                "dni": log.profile.dni if log.profile else None,
                "action": log.action,
                "description": log.description,
                "created_at": log.created_at,
            }
            for log in page_obj.object_list
        ]

        data = {
            "total_logs": paginator.count,
            "total_pages": paginator.num_pages,
            "current_page": page_obj.number,
            "results": results
        }

        return Response(
            APIResponse.success(
                data=data,
                message="Registros de auditoría obtenidos correctamente."
            ),
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'], url_path='top-engagement')
    def top_engagement(self, request):
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response(
                APIResponse.error("No tiene permisos para acceder a esta información.", code=status.HTTP_403_FORBIDDEN),
                status=status.HTTP_403_FORBIDDEN
            )

        top_users_qs = (
            AuditLog.objects.values(
                'profile__dni',
                'profile__user__first_name',
                'profile__user__last_name'
            )
            .annotate(sessions=Count('id'))
            .order_by('-sessions')[:10]
        )

        most_active_users = []
        for u in top_users_qs:
            full_name = f"{u['profile__user__first_name']} {u['profile__user__last_name']}".strip()
            most_active_users.append({
                "dni": u['profile__dni'],
                "full_name": full_name if full_name.strip() else "Sin nombre",
                "sessions": u['sessions']
            })

        limit_days = 30
        limit_date = date.today() - timedelta(days=limit_days)

        inactive_profiles = Profile.objects.filter(
            is_active=True,
            last_login__lt=limit_date
        ).values(
            'dni',
            'user__first_name',
            'user__last_name',
            'last_login'
        )

        inactive_users = []
        for u in inactive_profiles:
            full_name = f"{u['user__first_name']} {u['user__last_name']}".strip()
            inactive_users.append({
                "dni": u['dni'],
                "full_name": full_name if full_name.strip() else "Sin nombre",
                "last_login": u['last_login']
            })

        response_data = {
            "most_active_users": most_active_users,
            "inactive_users": inactive_users
        }

        return Response(
            APIResponse.success(
                data=response_data,
                message="Engagement de usuarios obtenido correctamente."
            ),
            status=status.HTTP_200_OK
        )
            
    @action(detail=False, methods=['get'], url_path='security-audit')
    def security_audit(self, request):
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response(
                APIResponse.error("No tiene permisos para acceder a esta información.", code=status.HTTP_403_FORBIDDEN),
                status=status.HTTP_403_FORBIDDEN
            )

        today = date.today()
        limit_date = today - timedelta(days=30)

        admin_actions_last_30d = AuditLog.objects.filter(
            profile__role='admin',
            created_at__date__gte=limit_date
        ).count()

        recent_admin_actions_qs = (
            AuditLog.objects
            .filter(profile__role='admin')
            .order_by('-created_at')[:5]
            .values('action', 'profile__user__first_name', 'profile__user__last_name', 'created_at')
        )

        recent_admin_actions = []
        for a in recent_admin_actions_qs:
            full_name = f"{a['profile__user__first_name']} {a['profile__user__last_name']}".strip()
            recent_admin_actions.append({
                "action": a['action'],
                "user": full_name if full_name else "Admin",
                "date": a['created_at'].strftime("%Y-%m-%d %H:%M")
            })

        failed_login_attempts = AuditLog.objects.filter(
            action="LOGIN_FAILED"
        ).count()

        data = {
            "admin_actions_last_30d": admin_actions_last_30d,
            "recent_admin_actions": recent_admin_actions,
            "failed_login_attempts": failed_login_attempts
        }

        return Response(
            APIResponse.success(
                data=data,
                message="Auditoría de seguridad obtenida correctamente."
            ),
            status=status.HTTP_200_OK
        )
