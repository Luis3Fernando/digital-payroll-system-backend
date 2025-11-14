from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

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

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate(self, attrs):
        user = self.context['request'].user

        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({
                "current_password": "La contraseña actual es incorrecta."
            })

        if attrs['current_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                "new_password": "Debe ingresar una contraseña diferente a la actual."
            })

        return attrs