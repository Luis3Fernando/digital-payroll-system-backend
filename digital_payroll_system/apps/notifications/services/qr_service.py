import qrcode
from io import BytesIO

def generate_qr_code(data: str):
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=5
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image()
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
