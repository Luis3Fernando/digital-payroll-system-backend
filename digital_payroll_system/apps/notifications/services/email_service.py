from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from email.mime.image import MIMEImage

def send_payslip_email(user, secure_url, qr_bytes, issue_date):
    subject = "Tu boleta de pago está lista"
    html = render_to_string("emails/payslip_generated.html", {
        "user_name": user.get_full_name(),
        "secure_url": secure_url,
        "issue_date": issue_date,
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