from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from uuid import UUID
from openpyxl import load_workbook
from apps.profiles.models import Profile
from .models import Payslip
import unicodedata
from common.response_handler import APIResponse
from apps.audit_logs.models import AuditLog
from datetime import datetime
from decimal import Decimal
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from xhtml2pdf import pisa
from io import BytesIO
from django.utils import timezone
from django.shortcuts import get_object_or_404
from apps.notifications.services.email_service import send_payslip_email
from apps.notifications.services.qr_service import generate_qr_code
from django.db.models import Q, F, Value, CharField
from django.db.models.functions import Concat

MONTHS_ES = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
]

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

            concept = str(row_data.get('concept')).upper()

            if Payslip.objects.filter(
                profile=profile,
                concept=concept,
                issue_date__year=issue_date.year,
                issue_date__month=issue_date.month
            ).exists():
                messages.append(
                    f"Fila {row_idx}: Ya existe una boleta con el concepto '{concept}' "
                    f"para el periodo {issue_date.strftime('%Y-%m')}. Se saltó la fila."
                )
                continue

            Payslip.objects.create(
                profile=profile,
                concept=concept,
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
    
    @action(detail=False, methods=['delete'], url_path='clear-payslips')
    def clear_payslips(self, request):
        if not request.user.profile.role == 'admin':
            return Response(
                APIResponse.error(
                    message="No tiene permisos para realizar esta acción.",
                    code=status.HTTP_403_FORBIDDEN
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        payslips = Payslip.objects.all()
        total_deleted = payslips.count()

        for ps in payslips:
            if ps.pdf_file:
                ps.pdf_file.delete(save=False)

        payslips.delete()

        AuditLog.objects.create(
            profile=request.user.profile,
            action="ELIMINAR BOLETAS",
            description=f"Se eliminaron {total_deleted} boletas de todos los usuarios."
        )

        return Response(
            APIResponse.success(
                message=f"Se eliminaron {total_deleted} boletas correctamente."
            ),
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['delete'], url_path='delete-payslip')
    def delete_payslip(self, request):
        payslip_id = request.data.get('id')

        if not payslip_id:
            return Response(
                APIResponse.error(
                    message="Se requiere el ID de la boleta para eliminar.",
                    code=status.HTTP_400_BAD_REQUEST
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        if not request.user.profile.role == 'admin':
            return Response(
                APIResponse.error(
                    message="No tiene permisos para realizar esta acción.",
                    code=status.HTTP_403_FORBIDDEN
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            uuid_obj = UUID(payslip_id, version=4)
        except (ValueError, TypeError):
            return Response(
                APIResponse.error(
                    message=f"El ID '{payslip_id}' no es un UUID válido.",
                    code=status.HTTP_400_BAD_REQUEST
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payslip = Payslip.objects.get(id=payslip_id)
        except Payslip.DoesNotExist:
            return Response(
                APIResponse.error(
                    message=f"No se encontró ninguna boleta con ID {payslip_id}.",
                    code=status.HTTP_404_NOT_FOUND
                ),
                status=status.HTTP_404_NOT_FOUND
            )

        payslip.delete()

        AuditLog.objects.create(
            profile=request.user.profile,
            action="ELIMINAR BOLETA",
            description=f"Se eliminó la boleta con ID {payslip_id} del usuario {payslip.profile.dni}."
        )

        return Response(
            APIResponse.success(
                message=f"Boleta con ID {payslip_id} eliminada correctamente."
            ),
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'], url_path='list-payslips')
    def list_payslips(self, request):
        if not request.user.profile.role == 'admin':
            return Response(
                APIResponse.error(
                    message="No tiene permisos para realizar esta acción.",
                    code=status.HTTP_403_FORBIDDEN
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
        except ValueError:
            page = 1
            page_size = 20
        
        page = max(page, 1)
        page_size = max(page_size, 1)

        dni = request.query_params.get('dni')
        name = request.query_params.get('name')
        concept = request.query_params.get('concept')
        status_view = request.query_params.get('status')
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        queryset = Payslip.objects.select_related('profile', 'profile__user').order_by('-issue_date')

        if dni:
            queryset = queryset.filter(profile__dni__icontains=dni)

        queryset = queryset.annotate(
            full_name_concat=Concat(
                F('profile__user__first_name'),
                Value(' '),
                F('profile__user__last_name'),
                output_field=CharField()
            )
        )

        if name:
            tokens = [t.strip() for t in name.split() if t.strip()]
            for token in tokens: 
                queryset = queryset.filter(full_name_concat__icontains=token)


        if concept:
            queryset = queryset.filter(concept__icontains=concept)

        if status_view:
            queryset = queryset.filter(view_status=status_view)

        if month:
            try:
                month = int(month)
                queryset = queryset.filter(issue_date__month=month)
            except:
                pass

        if year:
            try:
                year = int(year)
                queryset = queryset.filter(issue_date__year=year)
            except:
                pass

        total = queryset.count()
        offset = (page - 1) * page_size
        payslips = queryset[offset: offset + page_size]

        results = []

        for p in payslips:
            user = p.profile.user
            full_name = f"{user.first_name} {user.last_name}".strip() if user else None
            
            results.append({
                "id": str(p.id),
                "profile_id": str(p.profile.id),
                "profile_dni": p.profile.dni,
                "full_name": full_name,
                "issue_date": p.issue_date.isoformat(),
                "view_status": p.view_status,
                "concept": p.concept,
                "amount": float(p.amount),
                "data_source": p.data_source,
                "payroll_type": p.payroll_type,
                "data_type": p.data_type,
                "position_order": p.position_order,
            })

        pagination = {
            "current_page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size,
            "has_next": offset + page_size < total,
            "has_previous": page > 1
        }

        return Response(
            APIResponse.success(
                data=results,
                message=f"{len(results)} boletas obtenidas.",
                meta={"pagination": pagination}
            ),
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='my-payslips')
    def my_payslips(self, request):
        user = request.user

        if user.profile.role != 'user':
            return Response(
                APIResponse.error(
                    message="No tiene permisos para acceder a sus boletas.",
                    code=status.HTTP_403_FORBIDDEN
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        profile = user.profile

        month = request.query_params.get('month') 
        year = request.query_params.get('year') 

        payslips_qs = Payslip.objects.filter(profile=profile).order_by('-issue_date')

        if year:
            try:
                year = int(year)
                payslips_qs = payslips_qs.filter(issue_date__year=year)
            except ValueError:
                return Response(
                    APIResponse.error(message="Año inválido"),
                    status=status.HTTP_400_BAD_REQUEST
                )

        if month:
            try:
                month = int(month)
                if not 1 <= month <= 12:
                    raise ValueError
                payslips_qs = payslips_qs.filter(issue_date__month=month)
            except ValueError:
                return Response(
                    APIResponse.error(message="Mes inválido"),
                    status=status.HTTP_400_BAD_REQUEST
                )

        page = int(request.query_params.get('page', 1))
        page_size = 20
        offset = (page - 1) * page_size
        limit = offset + page_size

        total = payslips_qs.count()
        payslips = payslips_qs[offset:limit]

        results = []
        for p in payslips:
            try:
                pdf_url = request.build_absolute_uri(p.pdf_file.url) if p.pdf_file else None
            except Exception:
                pdf_url = None

            results.append({
                "id": str(p.id),
                "profile_id": str(p.profile.id),
                "profile_dni": p.profile.dni,
                "issue_date": p.issue_date.isoformat(),
                "view_status": p.view_status,
                "concept": p.concept,
                "amount": float(p.amount),
                "data_source": p.data_source,
                "payroll_type": p.payroll_type,
                "data_type": p.data_type,
                "position_order": p.position_order,
                "pdf_url": pdf_url,
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
                message=f"{len(results)} boletas obtenidas.",
                meta={"pagination": pagination}
            ),
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='view-payslip')
    def view_payslip(self, request):
        payslip_id = request.query_params.get('id')
        if not payslip_id:
            return Response(
                APIResponse.error(
                    message="Debe proporcionar el ID de la boleta.",
                    code=status.HTTP_400_BAD_REQUEST
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            UUID(payslip_id, version=4)
        except ValueError:
            return Response(
                APIResponse.error(
                    message="El ID proporcionado no es un UUID válido.",
                    code=status.HTTP_400_BAD_REQUEST
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        payslip = get_object_or_404(Payslip, id=payslip_id)

        if payslip.profile.user != request.user:
            return Response(
                APIResponse.error(
                    message="No tiene permiso para acceder a esta boleta.",
                    code=status.HTTP_403_FORBIDDEN
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        if not payslip.pdf_file:
            return Response(
                APIResponse.error(
                    message="La boleta no tiene un archivo PDF asociado.",
                    code=status.HTTP_400_BAD_REQUEST
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        if payslip.view_status != 'seen':
            payslip.view_status = 'seen'
            payslip.save()

        AuditLog.objects.create(
            profile=request.user.profile,
            action="VISUALIZAR BOLETA",
            description=f"El usuario {request.user.username} visualizó la boleta {payslip.id} del periodo {payslip.issue_date}."
        )

        return Response(
            APIResponse.success(
                message="Boleta visualizada correctamente.",
                data={
                    "payslip_id": str(payslip.id),
                    "pdf_url": request.build_absolute_uri(payslip.pdf_file.url),
                    "status": payslip.view_status,
                    "issue_date": payslip.issue_date,
                    "concept": payslip.concept,
                    "amount": payslip.amount
                }
            ),
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='generate-payslip')
    def generate_payslip(self, request):
        user = request.user

        if not hasattr(user, 'profile') or user.profile.role != 'user':
            return Response(
                APIResponse.error(
                    message="No tiene permisos para generar boletas.",
                    code=status.HTTP_403_FORBIDDEN
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        payslip_id = request.query_params.get('id')
        if not payslip_id:
            return Response(
                APIResponse.error(message="Debe proporcionar el parámetro 'id' de la boleta."),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payslip = Payslip.objects.get(id=payslip_id, profile=user.profile)
        except Payslip.DoesNotExist:
            return Response(
                APIResponse.error(message="Boleta no encontrada o no pertenece al usuario."),
                status=status.HTTP_404_NOT_FOUND
            )

        profile = user.profile
        work_details = getattr(profile, 'work_details', None)

        issue_month_name = MONTHS_ES[payslip.issue_date.month - 1]
        issue_date_es = f"{issue_month_name} {payslip.issue_date.year}"
        print_date = timezone.now().strftime("%d/%m/%Y")

        remuneracion_total = payslip.amount
        asignacion_familiar = Decimal("113.00")
        reintegros = Decimal("585.90")

        total_bruto = remuneracion_total + asignacion_familiar + reintegros
        aporte_patronal = round(total_bruto * Decimal("0.09"), 2)

        total_descuento = Decimal("197.92") + Decimal("33.45") + Decimal("27.12")
        total_liquido = total_bruto - total_descuento

        payload = {
            "issue_date_es": issue_date_es,
            "print_date": print_date, 
            'dni': user.profile.dni,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'position': user.profile.position,
            'description': user.profile.description,
            'condition': user.profile.condition,
            'regimen': user.profile.regimen,
            'category': user.profile.category,
            "worked_days": work_details.worked_days if work_details else 0,
            "worked_hours": work_details.worked_hours if work_details else 0,
            "discount_lateness": (
                (work_details.discount_lateness or 0) + (work_details.personal_leave_hours or 0)
            ) if work_details else 0,
            "start_date": profile.start_date.strftime("%d/%m/%Y") if profile.start_date else "—",
            "end_date": profile.end_date.strftime("%d/%m/%Y") if profile.end_date else "VIGENTE",
            "remuneracion_total": payslip.amount,
            "asignacion_familiar": 113.00,
            "reintegros": 585.90, 
            "sistema_pension": profile.descriptionSP or "—",
            "codigo_afiliado": profile.identification_code or "—",
            "aporte_individual": 197.92,
            "comision_flujo": 33.45,
            "prima_seguro": 27.12,
            "total_descuento": total_descuento,
            "descuento_dominical": work_details.sunday_discount if work_details else 0,
            "dias_vacaciones": work_details.vacation_days if work_details else 0,
            "aporte_patronal": aporte_patronal,
            "total_bruto": total_bruto,
            'total_liquido': total_liquido,
        }

        html = render_to_string('boleta.html', payload)

        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_buffer)

        if pisa_status.err:
            return Response(
                APIResponse.error(message="Error al generar el PDF."),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        pdf_filename = f"boleta_{payslip.id}.pdf"
        payslip.pdf_file.save(pdf_filename, ContentFile(pdf_buffer.getvalue()))
        payslip.view_status = 'generated'
        payslip.save()

        pdf_url = request.build_absolute_uri(payslip.pdf_file.url)
        qr_bytes = generate_qr_code(pdf_url)

        send_payslip_email(
            user=user,
            secure_url=pdf_url,
            qr_bytes=qr_bytes,
            issue_date=payslip.issue_date
        )

        AuditLog.objects.create(
            profile=getattr(request.user, 'profile', None),
            action="GENERAR BOLETA",
            description=(
                f"El usuario {request.user.first_name} {request.user.last_name} generó la boleta con ID {payslip.id}, "
                f"correspondiente al periodo {payslip.issue_date}."
            )
        )

        return Response(
            APIResponse.success(
                data={
                    "id": str(payslip.id),
                    "pdf_url": payslip.pdf_file.url,
                    "view_status": payslip.view_status
                },
                message="Boleta generada exitosamente."
            ),
            status=status.HTTP_200_OK
        )    