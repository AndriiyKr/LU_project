# backend/apps/users/urls.py

from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import UserRegisterView, UserProfileView, MyTokenObtainPairView, ChangePasswordView

app_name = "users"

urlpatterns = [
    # -------------------------------------------------------------
    # Реєстрація нового користувача
    # -------------------------------------------------------------
    path("register/", UserRegisterView.as_view(), name="user-register"),

    # -------------------------------------------------------------
    # Перегляд та редагування профілю
    # -------------------------------------------------------------
    path("profile/", UserProfileView.as_view(), name="user-profile"),

    # -------------------------------------------------------------
    # Зміна пароля
    # -------------------------------------------------------------
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),

    # -------------------------------------------------------------
    # JWT авторизація
    # -------------------------------------------------------------
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
