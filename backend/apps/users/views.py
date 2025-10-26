# backend/apps/users/views.py

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import (
    UserSerializer,
    UserRegisterSerializer,
    ChangePasswordSerializer,
    MyTokenObtainPairSerializer,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

User = get_user_model()

class MyTokenObtainPairView(TokenObtainPairView):
    """Кастомний View для логіну, використовує кастомний серіалізатор."""
    serializer_class = MyTokenObtainPairSerializer

# -------------------------------------------------------------
# Реєстрація нового користувача
# -------------------------------------------------------------
class UserRegisterView(generics.CreateAPIView):
    """
    Реєстрація нового користувача.
    """
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = []  # Доступно без авторизації


# -------------------------------------------------------------
# Перегляд та редагування профілю
# -------------------------------------------------------------
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Отримання і редагування власного профілю користувача.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# -------------------------------------------------------------
# Зміна пароля
# -------------------------------------------------------------
class ChangePasswordView(generics.UpdateAPIView):
    """
    Зміна пароля користувачем.
    """
    serializer_class = ChangePasswordSerializer
    model = User
    permission_classes = [IsAuthenticated]

    def get_object(self, queryset=None):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Перевірка старого пароля
            if not user.check_password(serializer.data.get("old_password")):
                return Response({"old_password": ["Неправильний старий пароль"]}, status=status.HTTP_400_BAD_REQUEST)

            # Встановлюємо новий пароль
            user.set_password(serializer.data.get("new_password"))
            user.save()
            return Response({"status": "success", "message": "Пароль змінено"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
