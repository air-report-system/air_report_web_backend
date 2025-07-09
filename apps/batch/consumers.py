"""
批量处理WebSocket消费者
"""
import json
import logging
from typing import Dict, Any
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import BatchJob

logger = logging.getLogger(__name__)


class BatchProcessingConsumer(AsyncWebsocketConsumer):
    """
    批量处理WebSocket消费者
    处理批量任务的实时通信
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch_job_id = None
        self.batch_group_name = None
        self.user = None

    async def connect(self):
        """连接WebSocket"""
        try:
            # 获取用户信息
            self.user = self.scope["user"]
            
            # 检查用户是否已认证
            if isinstance(self.user, AnonymousUser):
                logger.warning("未认证用户尝试连接WebSocket")
                await self.close(code=4001)
                return
            
            # 接受WebSocket连接
            await self.accept()
            logger.info(f"用户 {self.user.username} 已连接到批量处理WebSocket")
            
            # 发送连接成功消息
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'data': {
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'message': 'WebSocket连接已建立'
                },
                'timestamp': self._get_timestamp()
            }))
            
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        """断开WebSocket连接"""
        try:
            # 离开批量任务组
            if self.batch_group_name:
                await self.channel_layer.group_discard(
                    self.batch_group_name,
                    self.channel_name
                )
                logger.info(f"用户 {self.user.username if self.user else 'Unknown'} 已离开批量任务组: {self.batch_group_name}")
            
            logger.info(f"用户 {self.user.username if self.user else 'Unknown'} 已断开WebSocket连接 (code: {close_code})")
            
        except Exception as e:
            logger.error(f"断开WebSocket连接时出错: {e}")

    async def receive(self, text_data):
        """接收客户端消息"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            message_data = data.get('data', {})
            
            logger.info(f"收到WebSocket消息: {message_type} from {self.user.username}")
            
            # 处理不同类型的消息
            if message_type == 'subscribe_batch_job':
                await self.handle_subscribe_batch_job(message_data)
            elif message_type == 'unsubscribe_batch_job':
                await self.handle_unsubscribe_batch_job(message_data)
            elif message_type == 'ping':
                await self.handle_ping()
            else:
                logger.warning(f"未知消息类型: {message_type}")
                await self.send_error(f"未知消息类型: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("无效的JSON数据")
            await self.send_error("无效的JSON数据")
        except Exception as e:
            logger.error(f"处理WebSocket消息时出错: {e}")
            await self.send_error(f"处理消息时出错: {str(e)}")

    async def handle_subscribe_batch_job(self, data: Dict[str, Any]):
        """处理订阅批量任务"""
        try:
            batch_job_id = data.get('batch_job_id')
            if not batch_job_id:
                await self.send_error("batch_job_id is required")
                return
            
            # 检查批量任务是否存在且用户有权限访问
            batch_job = await self.get_batch_job(batch_job_id)
            if not batch_job:
                await self.send_error(f"批量任务 {batch_job_id} 不存在或无权限访问")
                return
            
            # 如果之前订阅了其他任务，先取消订阅
            if self.batch_group_name:
                await self.channel_layer.group_discard(
                    self.batch_group_name,
                    self.channel_name
                )
            
            # 订阅新的批量任务
            self.batch_job_id = batch_job_id
            self.batch_group_name = f"batch_job_{batch_job_id}"
            
            await self.channel_layer.group_add(
                self.batch_group_name,
                self.channel_name
            )
            
            logger.info(f"用户 {self.user.username} 已订阅批量任务: {batch_job_id}")
            
            # 发送订阅成功消息
            await self.send(text_data=json.dumps({
                'type': 'subscription_success',
                'data': {
                    'batch_job_id': batch_job_id,
                    'batch_job_name': batch_job.name,
                    'message': f'已订阅批量任务: {batch_job.name}'
                },
                'timestamp': self._get_timestamp()
            }))
            
            # 发送当前任务状态
            await self.send_batch_status(batch_job)
            
        except Exception as e:
            logger.error(f"订阅批量任务时出错: {e}")
            await self.send_error(f"订阅批量任务失败: {str(e)}")

    async def handle_unsubscribe_batch_job(self, data: Dict[str, Any]):
        """处理取消订阅批量任务"""
        try:
            if self.batch_group_name:
                await self.channel_layer.group_discard(
                    self.batch_group_name,
                    self.channel_name
                )
                
                logger.info(f"用户 {self.user.username} 已取消订阅批量任务: {self.batch_job_id}")
                
                # 发送取消订阅成功消息
                await self.send(text_data=json.dumps({
                    'type': 'unsubscription_success',
                    'data': {
                        'batch_job_id': self.batch_job_id,
                        'message': '已取消订阅批量任务'
                    },
                    'timestamp': self._get_timestamp()
                }))
                
                self.batch_job_id = None
                self.batch_group_name = None
            
        except Exception as e:
            logger.error(f"取消订阅批量任务时出错: {e}")
            await self.send_error(f"取消订阅失败: {str(e)}")

    async def handle_ping(self):
        """处理心跳检测"""
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'data': {'message': 'pong'},
            'timestamp': self._get_timestamp()
        }))

    async def send_error(self, message: str):
        """发送错误消息"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'data': {'message': message},
            'timestamp': self._get_timestamp()
        }))

    async def send_batch_status(self, batch_job):
        """发送批量任务状态"""
        await self.send(text_data=json.dumps({
            'type': 'batch_progress_update',
            'data': {
                'batch_job_id': batch_job.id,
                'progress_percentage': batch_job.progress_percentage,
                'processed_files': batch_job.processed_files,
                'failed_files': batch_job.failed_files,
                'status': batch_job.status,
                'total_files': batch_job.total_files
            },
            'timestamp': self._get_timestamp()
        }))

    # 群组消息处理方法
    async def batch_progress_update(self, event):
        """处理批量任务进度更新"""
        await self.send(text_data=json.dumps({
            'type': 'batch_progress_update',
            'data': event['data'],
            'timestamp': self._get_timestamp()
        }))

    async def file_processing_update(self, event):
        """处理文件处理状态更新"""
        await self.send(text_data=json.dumps({
            'type': 'file_processing_update', 
            'data': event['data'],
            'timestamp': self._get_timestamp()
        }))

    async def batch_job_completed(self, event):
        """处理批量任务完成"""
        await self.send(text_data=json.dumps({
            'type': 'batch_job_completed',
            'data': event['data'],
            'timestamp': self._get_timestamp()
        }))

    # 数据库操作方法
    @database_sync_to_async
    def get_batch_job(self, batch_job_id: int):
        """获取批量任务"""
        try:
            return BatchJob.objects.filter(
                id=batch_job_id,
                created_by=self.user
            ).first()
        except Exception as e:
            logger.error(f"获取批量任务失败: {e}")
            return None

    def _get_timestamp(self) -> int:
        """获取当前时间戳"""
        from django.utils import timezone
        return int(timezone.now().timestamp() * 1000)


# 用于在任务中发送WebSocket消息的工具函数
def send_batch_progress_update(batch_job_id: int, progress_data: Dict[str, Any]):
    """发送批量任务进度更新"""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    channel_layer = get_channel_layer()
    if channel_layer:
        group_name = f"batch_job_{batch_job_id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'batch_progress_update',
                'data': progress_data
            }
        )


def send_file_processing_update(batch_job_id: int, file_data: Dict[str, Any]):
    """发送文件处理状态更新"""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    channel_layer = get_channel_layer()
    if channel_layer:
        group_name = f"batch_job_{batch_job_id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'file_processing_update',
                'data': file_data
            }
        )


def send_batch_job_completed(batch_job_id: int, completion_data: Dict[str, Any]):
    """发送批量任务完成消息"""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    channel_layer = get_channel_layer()
    if channel_layer:
        group_name = f"batch_job_{batch_job_id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'batch_job_completed',
                'data': completion_data
            }
        )