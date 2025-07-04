"""
微信CSV处理URL配置
"""
from django.urls import path
from . import views

app_name = 'wechat_csv'

urlpatterns = [
    # 认证相关
    path('login/', views.LoginView.as_view(), name='login'),
    path('login', views.LoginView.as_view(), name='login-no-slash'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('logout', views.LogoutView.as_view(), name='logout-no-slash'),

    # 核心功能
    path('process/', views.ProcessMessageView.as_view(), name='process'),
    path('process', views.ProcessMessageView.as_view(), name='process-no-slash'),
    path('update_table/', views.UpdateTableView.as_view(), name='update_table'),
    path('update_table', views.UpdateTableView.as_view(), name='update_table-no-slash'),
    path('submit/', views.SubmitToGitHubView.as_view(), name='submit'),
    path('submit', views.SubmitToGitHubView.as_view(), name='submit-no-slash'),

    # 管理功能
    path('records/', views.RecordsListView.as_view(), name='records'),
    path('records', views.RecordsListView.as_view(), name='records-no-slash'),
    path('history/', views.ProcessingHistoryListView.as_view(), name='history'),
    path('history', views.ProcessingHistoryListView.as_view(), name='history-no-slash'),
]
