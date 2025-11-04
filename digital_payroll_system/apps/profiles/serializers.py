from rest_framework import serializers

class ProfileUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        required=True,
        help_text="Archivo Excel (.xlsx) con los usuarios a importar."
    )

class ProfileWorkDetailsUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        required=True,
        help_text="Archivo Excel (.xlsx) con los detalles de trabajo de los usuarios."
    )