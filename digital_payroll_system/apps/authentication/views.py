from rest_framework import status, viewsets
from rest_framework.response import Response
from .serializers import *
from common.response_handler import APIResponse

from django.contrib.auth import get_user_model

User = get_user_model()

class AuthViewSet(viewsets.ViewSet):

    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            return Response(
                APIResponse.success(
                    data=data,
                    message="Inicio de sesión exitoso."
                ),
                status=status.HTTP_200_OK
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

    def refresh(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_refresh_token = serializer.validated_data['refresh']

        try:
            old_refresh = RefreshToken(old_refresh_token)
            old_refresh.blacklist()

            user_id = old_refresh['user_id']
            user = User.objects.get(id=user_id)

            new_refresh = RefreshToken.for_user(user)
            access_token = str(new_refresh.access_token)

            return Response(
                APIResponse.success(
                    data={'access': access_token, 'refresh': str(new_refresh)},
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
