"""
订单信息记录URL配置
"""
from django.urls import path
from .views import (
    ProcessOrderInfoView, UpdateOrderDataView, SubmitOrderView,
    OrderRecordListView, OrderRecordDetailView
)

app_name = 'orders'

urlpatterns = [
    # 订单信息处理
    path('process/', ProcessOrderInfoView.as_view(), name='process-order-info'),
    path('process', ProcessOrderInfoView.as_view(), name='process-order-info-no-slash'),
    path('update/', UpdateOrderDataView.as_view(), name='update-order-data'),
    path('update', UpdateOrderDataView.as_view(), name='update-order-data-no-slash'),
    path('submit/', SubmitOrderView.as_view(), name='submit-order'),
    path('submit', SubmitOrderView.as_view(), name='submit-order-no-slash'),

    # 订单记录管理
    path('records/', OrderRecordListView.as_view(), name='order-records'),
    path('records', OrderRecordListView.as_view(), name='order-records-no-slash'),
    path('records/<int:pk>/', OrderRecordDetailView.as_view(), name='order-record-detail'),
]
