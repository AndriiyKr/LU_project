# backend/apps/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # Можна додати додаткові поля, якщо потрібно
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.username

# ---
# backend/apps/users/serializers.py
from rest_framework import serializers
from .models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email')

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm Password")

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password', 'password2')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        user = CustomUser.objects.create(
            username=validated_data['username'],
            email=validated_data['email']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

# ---
# backend/apps/users/views.py
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

class MyTokenObtainPairView(TokenObtainPairView):
    # Можна кастомізувати серіалізатор, якщо треба додати дані в токен
    pass

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)

class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user

# ---
# backend/apps/users/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView

app_name = 'users'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', UserProfileView.as_view(), name='profile'),
]