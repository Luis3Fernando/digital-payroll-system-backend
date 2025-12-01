from rest_framework import status, viewsets
from rest_framework.response import Response
from .serializers import *
from common.response_handler import APIResponse
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action, authentication_classes, permission_classes
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.audit_logs.utils.audit import create_audit_log

User = get_user_model()

class AuthViewSet(viewsets.ViewSet):

    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            dni = data["user"]["dni"]

            try:
                profile = Profile.objects.get(dni=dni)
                create_audit_log(
                    profile=profile,
                    action="LOGIN_EXITOSO",
                    description=f"El usuario {profile.user.username} inició sesión."
                )

                profile.last_login = timezone.now()
                profile.save(update_fields=["last_login"])

            except Profile.DoesNotExist:
                create_audit_log(
                    profile=None,
                    action="LOGIN_FALLIDO",
                    description=f"Intento fallido de login con DNI {dni}."
                )

                return Response(
                    APIResponse.error(
                        message="No se encontró el perfil del usuario.",
                        code=status.HTTP_404_NOT_FOUND
                    ),
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(
                APIResponse.success(
                    data=data,
                    message="Inicio de sesión exitoso."
                ),
                status=status.HTTP_200_OK
            )

        dni = request.data.get("dni", "desconocido")
        create_audit_log(
            profile=None,
            action="LOGIN_FALLIDO",
            description=f"Intento fallido de login con DNI {dni}."
        )

        return Response(
            APIResponse.error(
                message="Error en las credenciales.",
                code=status.HTTP_400_BAD_REQUEST,
                errors=serializer.errors
            ),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    def logout(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh_token = serializer.validated_data['refresh']

        try:
            token = RefreshToken(refresh_token)
            profile = Profile.objects.get(user_id=token['user_id'])
            create_audit_log(
                profile=profile,
                action="LOGOUT",
                description=f"El usuario {profile.user.username} cerró sesión."
            )

            token.blacklist()

            return Response(
                APIResponse.success(
                    message="Cierre de sesión exitoso."
                ),
                status=status.HTTP_200_OK
            )
        except TokenError:
            return Response(
                APIResponse.error(
                    message="Token inválido o expirado.",
                    code=status.HTTP_400_BAD_REQUEST
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=False,
        methods=['post'],
        url_path='refresh'
    )
    @authentication_classes([])     
    @permission_classes([AllowAny]) 
    def refresh(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_refresh_token = serializer.validated_data["refresh"]

        try:
            old_refresh = RefreshToken(old_refresh_token)

            user_id = old_refresh["user_id"]
            user = User.objects.get(id=user_id)

            old_refresh.blacklist()

            new_refresh = RefreshToken.for_user(user)
            access_token = str(new_refresh.access_token)

            return Response(
                APIResponse.success(
                    data={"access": access_token, "refresh": str(new_refresh)},
                    message="Token refreshed successfully."
                ),
                status=status.HTTP_200_OK
            )

        except (TokenError, User.DoesNotExist):
            return Response(
                APIResponse.error(
                    message="Invalid or expired refresh token.",
                    code=status.HTTP_401_UNAUTHORIZED
                ),
                status=status.HTTP_401_UNAUTHORIZED
            )
