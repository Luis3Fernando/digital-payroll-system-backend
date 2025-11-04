from rest_framework import serializers

class PayslipUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        required=True,
        help_text="Archivo Excel (.xlsx) con las boletas a importar."
    )
