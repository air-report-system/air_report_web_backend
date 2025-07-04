"""
报告管理URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 使用标准路由器
router = DefaultRouter(trailing_slash=False)
router.register(r'', views.ReportViewSet, basename='report')
router.register(r'templates', views.ReportTemplateViewSet, basename='reporttemplate')

urlpatterns = [
    path('', include(router.urls)),
    path('create/', views.CreateReportView.as_view(), name='create-report'),
    path('create', views.CreateReportView.as_view(), name='create-report-no-slash'),
    path('stats/', views.ReportStatsView.as_view(), name='report-stats'),
    path('stats', views.ReportStatsView.as_view(), name='report-stats-no-slash'),
]
