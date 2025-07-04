"""
文件管理URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter(trailing_slash=False)  # 禁用末尾斜杠
router.register(r'files', views.UploadedFileViewSet, basename='uploadedfile')

urlpatterns = [
    path('', include(router.urls)),
    path('upload/', views.FileUploadView.as_view(), name='file-upload'),
    path('upload', views.FileUploadView.as_view(), name='file-upload-no-slash'),
    path('bulk-upload/', views.BulkFileUploadView.as_view(), name='bulk-file-upload'),
    path('bulk-upload', views.BulkFileUploadView.as_view(), name='bulk-file-upload-no-slash'),
    path('stats/', views.FileStatsView.as_view(), name='file-stats'),
    path('stats', views.FileStatsView.as_view(), name='file-stats-no-slash'),
]
