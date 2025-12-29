"""
月度报表URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter(trailing_slash=False)  # 禁用末尾斜杠
router.register(r'reports', views.MonthlyReportViewSet, basename='monthlyreport')
router.register(r'configs', views.MonthlyReportConfigViewSet, basename='monthlyreportconfig')

urlpatterns = [
    path('', include(router.urls)),
    path('create/', views.CreateMonthlyReportView.as_view(), name='create-monthly-report'),
    path('create', views.CreateMonthlyReportView.as_view(), name='create-monthly-report-no-slash'),
    path('create-from-db/', views.GenerateMonthlyReportFromDBView.as_view(), name='create-monthly-report-from-db'),
    path('create-from-db', views.GenerateMonthlyReportFromDBView.as_view(), name='create-monthly-report-from-db-no-slash'),
    path('preview-csv/', views.PreviewMonthlyReportCSVView.as_view(), name='preview-monthly-report-csv'),
    path('preview-csv', views.PreviewMonthlyReportCSVView.as_view(), name='preview-monthly-report-csv-no-slash'),
    path('generate-from-csv/', views.GenerateMonthlyReportFromCSVView.as_view(), name='generate-monthly-report-from-csv'),
    path('generate-from-csv', views.GenerateMonthlyReportFromCSVView.as_view(), name='generate-monthly-report-from-csv-no-slash'),
    path('stats/', views.MonthlyReportStatsView.as_view(), name='monthly-report-stats'),
    path('stats', views.MonthlyReportStatsView.as_view(), name='monthly-report-stats-no-slash'),
    path('upload-labor-cost/', views.LaborCostFileUploadView.as_view(), name='upload-labor-cost'),
    path('upload-labor-cost', views.LaborCostFileUploadView.as_view(), name='upload-labor-cost-no-slash'),
]
