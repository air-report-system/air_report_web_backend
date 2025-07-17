"""
用户认证URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('login/', views.LoginView.as_view(), name='login'),
    path('login', views.LoginView.as_view(), name='login-no-slash'),  # 支持没有斜杠的URL
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('logout', views.LogoutView.as_view(), name='logout-no-slash'),  # 支持没有斜杠的URL
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile', views.UserProfileView.as_view(), name='profile-no-slash'),  # 支持没有斜杠的URL
    path('background-image/', views.BackgroundImageView.as_view(), name='background-image'),
    path('background-image', views.BackgroundImageView.as_view(), name='background-image-no-slash'),  # 支持没有斜杠的URL
]
