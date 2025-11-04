from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from apps.profiles.models import Profile

class LoginSerializer(serializers.Serializer):
    dni = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        dni = data.get('dni')
        password = data.get('password')
        try:
            profile = Profile.objects.select_related('user').get(dni=dni)
            user = profile.user
        except Profile.DoesNotExist:
            raise serializers.ValidationError("Usuario no encontrado.")

        user = authenticate(username=user.username, password=password)
        if not user:
            raise serializers.ValidationError("Credenciales inválidas.")
        
        if not user.is_active:
            raise serializers.ValidationError("La cuenta está inactiva.")

        refresh = RefreshToken.for_user(user)

        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'dni': dni,
                'email': user.email,
                'role': getattr(profile, 'role', None),
            }
        }
    
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except TokenError:
            self.fail('invalid_token')

class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True)