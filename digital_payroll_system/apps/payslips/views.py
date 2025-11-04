from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from openpyxl import load_workbook
from apps.profiles.models import Profile
from .models import Payslip
import unicodedata
from common.response_handler import APIResponse
from apps.audit_logs.models import AuditLog
from datetime import datetime
from decimal import Decimal

REQUIRED_PAYSLIP_COLUMNS = {
    "dni": ["DNI"],
    "concept": ["Concepto"],
    "amount": ["Monto"],
    "data_source": ["OrigenDato"],
    "payroll_type": ["TipoPlanilla"],
    "data_type": ["TipoDato"],
    "position_order": ["Posicion"],
    "issue_date": ["Periodo"],
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

def parse_period(period_text):
    try:
        months = {
            "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4,
            "MAYO": 5, "JUNIO": 6, "JULIO": 7, "AGOSTO": 8,
            "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12
        }
        parts = period_text.upper().split()
        month = months.get(parts[0], 1)
        year = int(parts[1])
        return datetime(year, month, 1).date()
    except Exception:
        return None
     
class PayslipUploadViewSet(viewsets.ViewSet):
    """
    Upload payslips from Excel file.
    """
    permission_classes = []

    @action(detail=False, methods=['post'], url_path='upload-payslips')
    def upload_payslips(self, request):
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
            for field, variants in REQUIRED_PAYSLIP_COLUMNS.items():
                if nh in [normalize(v) for v in variants]:
                    column_map[idx] = field

        missing = [field for field in REQUIRED_PAYSLIP_COLUMNS.keys() if field not in column_map.values()]
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

            dni = str(row_data.get('dni')).strip() if row_data.get('dni') else None
            if not dni:
                messages.append(f"Fila {row_idx}: DNI no encontrado. Se saltó la fila.")
                continue

            try:
                profile = Profile.objects.get(dni=dni)
            except Profile.DoesNotExist:
                messages.append(f"Fila {row_idx}: Usuario con DNI {dni} no existe. Se saltó la fila.")
                continue

            period_text = str(row_data.get('issue_date'))
            issue_date = parse_period(period_text)
            if not issue_date:
                messages.append(f"Fila {row_idx}: Periodo '{period_text}' inválido. Se saltó la fila.")
                continue

            try:
                amount = Decimal(row_data.get('amount'))
            except Exception:
                messages.append(f"Fila {row_idx}: Monto inválido '{row_data.get('amount')}'. Se saltó la fila.")
                continue

            payslip = Payslip.objects.create(
                profile=profile,
                concept=str(row_data.get('concept')).upper(),
                amount=amount,
                data_source=str(row_data.get('data_source')).upper(),
                payroll_type=str(row_data.get('payroll_type')).upper(),
                data_type=str(row_data.get('data_type')).upper(),
                position_order=int(row_data.get('position_order')),
                issue_date=issue_date,
                pdf_file='',
                view_status='unseen'
            )
            messages.append(f"Fila {row_idx}: Boleta para DNI {dni} creada.")

        description_text = "\n".join(messages)
        AuditLog.objects.create(
            profile=request.user.profile,
            action="CARGA DE BOLETAS",
            description=description_text
        )

        return Response(
            APIResponse.success(
                message="Procesamiento finalizado.",
                data={'messages': messages}
            ),
            status=status.HTTP_200_OK
        )