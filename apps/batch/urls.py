"""
批量处理URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter(trailing_slash=False)  # 禁用末尾斜杠
router.register(r'jobs', views.BatchJobViewSet, basename='batchjob')

urlpatterns = [
    path('', include(router.urls)),
    path('create/', views.BulkFileUploadAndBatchView.as_view(), name='bulk-upload-and-batch'),
    path('create', views.BulkFileUploadAndBatchView.as_view(), name='bulk-upload-and-batch-no-slash'),
    path('create-from-files/', views.CreateBatchJobView.as_view(), name='create-batch-job'),
    path('create-from-files', views.CreateBatchJobView.as_view(), name='create-batch-job-no-slash'),
    path('stats/', views.BatchStatsView.as_view(), name='batch-stats'),
    path('stats', views.BatchStatsView.as_view(), name='batch-stats-no-slash'),
]
