from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from datetime import datetime
from openpyxl import load_workbook
import unicodedata
from django.db.models import Q

from .serializers import *
from .models import *
from apps.audit_logs.models import AuditLog
from common.response_handler import APIResponse

REQUIRED_COLUMNS = {
    'dni': ['dni'],
    'last_name': ['apellidos', 'apellido', 'last name'],
    'first_name': ['nombres', 'nombre', 'first name'],
    'start_date': ['fecha inicio', 'fechainicio'],
    'position': ['nombre de cargo', 'cargo', 'position', 'NombreCargo'],
    'description': ['descripcion', 'description'],
    'condition': ['condicion', 'condition'],
    'category': ['categoria', 'category'],
    'regimen': ['regimen', 'regime'],
    'identification_code': ['codigo de identificacion', 'codigo', 'identification code', 'CodigoIdentificacion'],
    'role': ['tipo', 'rol', 'role'],
    'descriptionSP': ['descripcionSP', 'descripcion sp', 'descripcionsistema'],
    'end_date': ['fecha fin', 'end date'],
    'resigned_date': ['fecha renuncia', 'fecha de renuncia', 'resigned date'],
    'resigned': ['con renuncia', 'resigned'],
    'establishment': ['establecimiento', 'establishment']
}

OPTIONAL_COLUMNS = {
    'email': ['email', 'correo', 'correo electronico']
}

WORK_DETAILS_COLUMNS = {
    "dni": ["DNI"],
    "worked_days": ["DiasTrabajados"],
    "non_worked_days": ["DiasNoTrabajados"],
    "worked_hours": ["HorasTrabajados"],
    "discount_academic_hours": ["DescuentoHorasAcademicas"],
    "discount_lateness": ["DescuentoTardanzas"],
    "personal_leave_hours": ["PermisoParticular"],
    "sunday_discount": ["DescuentoDominical"],
    "vacation_days": ["DiasVacaciones"],
    "vacation_hours": ["HorasVacaciones"]
}

def normalize(s):
    """Quita acentos, espacios y pasa a minúsculas"""
    if not s:
        return ''
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s.replace(' ', '').lower()

def to_upper(val):
    return str(val).upper() if val else None

def parse_date(val):
    if not val:
        return None
    if isinstance(val, datetime):
        return val.date() 
    try:
        return datetime.strptime(val, "%d/%m/%Y").date()
    except Exception:
        return None 
    
class ProfileViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='upload-users')
    def upload_users(self, request):
        if not request.user.profile.role == 'admin':
            return Response(
                APIResponse.error(
                    message="No tiene permisos para realizar esta acción.",
                    code=status.HTTP_403_FORBIDDEN
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        file = request.FILES.get('file')
        if not file:
            return Response(
                APIResponse.error(
                    message="No se ha enviado ningún archivo.",
                    code=status.HTTP_400_BAD_REQUEST
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        if not file.name.endswith('.xlsx'):
            return Response(
                APIResponse.error(
                    message="El archivo debe ser un Excel (.xlsx).",
                    code=status.HTTP_400_BAD_REQUEST
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            workbook = load_workbook(filename=file)
            ws = workbook.active
        except Exception as e:
            return Response(
                APIResponse.error(
                    message=f"Error al abrir el archivo: {str(e)}",
                    code=status.HTTP_400_BAD_REQUEST
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        headers = [str(cell.value).strip() if cell.value else '' for cell in ws[1]]
        normalized_headers = [normalize(h) for h in headers]

        column_map = {}

        for idx, nh in enumerate(normalized_headers):
            for field, variants in REQUIRED_COLUMNS.items():
                if nh in [normalize(v) for v in variants]:
                    column_map[idx] = field

        for idx, nh in enumerate(normalized_headers):
            for field, variants in OPTIONAL_COLUMNS.items():
                if nh in [normalize(v) for v in variants]:
                    column_map[idx] = field

        missing = [field for field in REQUIRED_COLUMNS.keys() if field not in column_map.values()]
        if missing:
            return Response(
                APIResponse.error(
                    message=f"Faltan columnas obligatorias en el Excel: {', '.join(missing)}",
                    code=status.HTTP_400_BAD_REQUEST
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        messages = []

        for row_idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
            row_data = {column_map[idx]: cell.value for idx, cell in enumerate(row) if idx in column_map}

            dni = to_upper(row_data.get('dni'))
            last_name = to_upper(row_data.get('last_name'))
            first_name = to_upper(row_data.get('first_name'))

            if not dni or not last_name or not first_name:
                messages.append(f"Fila {row_idx}: DNI, last_name y first_name son obligatorios. Se saltó la fila.")
                continue

            email = row_data.get('email')
            user_data = {
                'first_name': first_name,
                'last_name': last_name
            }
            if email:
                user_data['email'] = email

            user, created = User.objects.update_or_create(
                username=dni,
                defaults=user_data
            )

            if created:
                user.set_password(dni)
                user.save()
                messages.append(f"Fila {row_idx}: Usuario con DNI {dni} creado.")
            else:
                messages.append(f"Fila {row_idx}: Usuario con DNI {dni} actualizado.")

            resigned_value = row_data.get('resigned')
            if resigned_value in [1, "1", True, "TRUE", "True"]:
                resigned_bool = True
            else:
                resigned_bool = False

            profile_data = {
                'user': user,
                'dni': dni,
                'role': 'user',
                'position': to_upper(row_data.get('position')),
                'description': to_upper(row_data.get('description')),
                'descriptionSP': to_upper(row_data.get('descriptionSP')),
                'start_date': parse_date(row_data.get('start_date')),
                'end_date': parse_date(row_data.get('end_date')),
                'resigned_date': parse_date(row_data.get('resigned_date')),
                'resigned': resigned_bool,
                'regimen': to_upper(row_data.get('regimen')),
                'category': to_upper(row_data.get('category')),
                'condition': to_upper(row_data.get('condition')),
                'identification_code': to_upper(row_data.get('identification_code')),
                'establishment': to_upper(row_data.get('establishment')),
            }

            Profile.objects.update_or_create(
                user=user, 
                defaults=profile_data
            )

        description_text = "\n".join(messages)
        AuditLog.objects.create(
            profile=request.user.profile,
            action="CARGA DE USUARIOS",
            description=description_text
        )

        return Response(
            APIResponse.success(
                message="Procesamiento finalizado.",
                data={'messages': messages}
            ),
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'], url_path='upload-work-details')
    def upload_work_details(self, request):
        if not request.user.profile.role == 'admin':
            return Response(
                APIResponse.error(
                    message="No tiene permisos para realizar esta acción.",
                    code=status.HTTP_403_FORBIDDEN
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        file = request.FILES.get('file')
        if not file:
            return Response(
                APIResponse.error(
                    message="No se ha enviado ningún archivo.",
                    code=status.HTTP_400_BAD_REQUEST
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        if not file.name.endswith('.xlsx'):
            return Response(
                APIResponse.error(
                    message="El archivo debe ser un Excel (.xlsx).",
                    code=status.HTTP_400_BAD_REQUEST
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            workbook = load_workbook(filename=file)
            ws = workbook.active
        except Exception as e:
            return Response(
                APIResponse.error(
                    message=f"Error al abrir el archivo: {str(e)}",
                    code=status.HTTP_400_BAD_REQUEST
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        headers = [str(cell.value).strip() if cell.value else '' for cell in ws[1]]
        normalized_headers = [normalize(h) for h in headers]

        column_map = {}
        for idx, nh in enumerate(normalized_headers):
            for field, variants in WORK_DETAILS_COLUMNS.items():
                if nh in [normalize(v) for v in variants]:
                    column_map[idx] = field

        missing = [field for field in WORK_DETAILS_COLUMNS.keys() if field not in column_map.values()]
        if missing:
            return Response(
                APIResponse.error(
                    message=f"Faltan columnas obligatorias en el Excel: {', '.join(missing)}",
                    code=status.HTTP_400_BAD_REQUEST
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        messages = []

        for row_idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
            row_data = {column_map[idx]: cell.value for idx, cell in enumerate(row) if idx in column_map}

            dni = to_upper(row_data.get('dni'))

            if not dni:
                messages.append(f"Fila {row_idx}: DNI es obligatorio. Se saltó la fila.")
                continue

            try:
                profile = Profile.objects.get(dni=dni)
            except Profile.DoesNotExist:
                messages.append(f"Fila {row_idx}: No se encontró Profile con DNI {dni}. Se saltó la fila.")
                continue

            work_data = {
                'worked_days': int(row_data.get('worked_days') or 0),
                'non_worked_days': int(row_data.get('non_worked_days') or 0),
                'worked_hours': int(row_data.get('worked_hours') or 0),
                'discount_academic_hours': int(row_data.get('discount_academic_hours') or 0),
                'discount_lateness': int(row_data.get('discount_lateness') or 0),
                'personal_leave_hours': int(row_data.get('personal_leave_hours') or 0),
                'sunday_discount': int(row_data.get('sunday_discount') or 0),
                'vacation_days': int(row_data.get('vacation_days') or 0),
                'vacation_hours': int(row_data.get('vacation_hours') or 0),
            }

            work_details, created = ProfileWorkDetails.objects.update_or_create(
                profile=profile,
                defaults=work_data
            )

            if created:
                messages.append(f"Fila {row_idx}: WorkDetails para DNI {dni} creado.")
            else:
                messages.append(f"Fila {row_idx}: WorkDetails para DNI {dni} actualizado.")

        description_text = "\n".join(messages)
        AuditLog.objects.create(
            profile=request.user.profile,
            action="CARGA DE WORK DETAILS",
            description=description_text
        )

        return Response(
            APIResponse.success(
                message="Procesamiento de WorkDetails finalizado.",
                data={'messages': messages}
            ),
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='list-users')
    def list_users(self, request):
        if not request.user.profile.role == 'admin':
            return Response(
                APIResponse.error(
                    message="No tiene permisos para realizar esta acción.",
                    code=status.HTTP_403_FORBIDDEN
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        page = int(request.query_params.get('page', 1))
        page_size = 20
        search = request.query_params.get('search', '').strip()

        offset = (page - 1) * page_size
        limit = offset + page_size

        queryset = Profile.objects.select_related('user').filter(role='user').order_by('-created_at')

        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )

        total = queryset.count()
        profiles = queryset[offset:limit]

        results = []
        for p in profiles:
            results.append({
                "id": str(p.id),
                "dni": p.dni,
                "first_name": p.user.first_name if p.user else None,
                "last_name": p.user.last_name if p.user else None,
                "email": p.user.email if p.user else None,
                "role": p.role,
                "condition": p.condition,
                "position": p.position,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })

        pagination = {
            "current_page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size,
            "has_next": limit < total,
            "has_previous": page > 1
        }

        return Response(
            APIResponse.success(
                data=results,
                message=f"{len(results)} usuarios obtenidos.",
                meta={"pagination": pagination}
            ),
            status=status.HTTP_200_OK
        )
