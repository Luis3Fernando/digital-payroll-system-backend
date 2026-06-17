from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from email.mime.image import MIMEImage

MONTHS_ES = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
]

def send_payslip_email(user, secure_url, qr_bytes, issue_date):
    subject = "Tu boleta de pago está lista"

    try:
        month_name = MONTHS_ES[issue_date.month - 1]
        issue_date_es = f"{month_name} {issue_date.year}"
    except Exception:
        issue_date_es = str(issue_date)

    html = render_to_string("emails/payslip_generated.html", {
        "user_name": user.get_full_name(),
        "secure_url": secure_url,
        "issue_date": issue_date_es,
    })

    email = EmailMultiAlternatives(
        subject=subject,
        body="Tu boleta está lista.",
        from_email=settings.EMAIL_HOST_USER,
        to=[user.email]
    )

    email.attach_alternative(html, "text/html")

    qr_image = MIMEImage(qr_bytes)
    qr_image.add_header("Content-ID", "<qr_image>")
    email.attach(qr_image)

    email.send()

def send_email_updated_notification(user, new_email):
    subject = "Tu correo ha sido actualizado correctamente"

    html_content = render_to_string("emails/email_updated.html", {
        "full_name": user.get_full_name(),
        "new_email": new_email
    })

    email = EmailMultiAlternatives(
        subject=subject,
        body="Tu correo ha sido actualizado.",
        from_email=settings.EMAIL_HOST_USER,
        to=[new_email]
    )

    email.attach_alternative(html_content, "text/html")
    email.send()


def send_password_changed_notification(user):
    subject = "Tu contraseña ha sido modificada"

    html_content = render_to_string("emails/password_changed.html", {
        "full_name": user.get_full_name(),
        "email": user.email,
    })

    email = EmailMultiAlternatives(
        subject=subject,
        body="Tu contraseña fue cambiada.",
        from_email=settings.EMAIL_HOST_USER,
        to=[user.email]
    )

    email.attach_alternative(html_content, "text/html")
    email.send()