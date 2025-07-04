"""
OCR处理URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter(trailing_slash=False)  # 禁用末尾斜杠
router.register(r'results', views.OCRResultViewSet, basename='ocrresult')
router.register(r'point-learning', views.PointLearningViewSet, basename='pointlearning')
router.register(r'point-values', views.PointValueViewSet, basename='pointvalue')

urlpatterns = [
    path('', include(router.urls)),
    path('process/', views.ProcessImageView.as_view(), name='process-image'),
    path('process', views.ProcessImageView.as_view(), name='process-image-no-slash'),
    path('upload-and-process/', views.UploadAndProcessView.as_view(), name='upload-and-process'),
    path('upload-and-process', views.UploadAndProcessView.as_view(), name='upload-and-process-no-slash'),
    path('test/', views.TestOCRView.as_view(), name='test-ocr'),
    path('test', views.TestOCRView.as_view(), name='test-ocr-no-slash'),
    path('infer-check-type/', views.CheckTypeInferenceAPIView.as_view(), name='infer-check-type'),
    path('infer-check-type', views.CheckTypeInferenceAPIView.as_view(), name='infer-check-type-no-slash'),
    path('data-sync/', views.DataSyncAPIView.as_view(), name='data-sync'),
    path('data-sync', views.DataSyncAPIView.as_view(), name='data-sync-no-slash'),
]
