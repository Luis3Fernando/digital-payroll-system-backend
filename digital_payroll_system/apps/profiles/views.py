from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from datetime import datetime
from openpyxl import load_workbook
import unicodedata

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
