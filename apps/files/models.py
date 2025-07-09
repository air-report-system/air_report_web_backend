"""
文件管理模型
"""
import hashlib
import os
from django.db import models
from apps.core.models import BaseModel


def get_file_hash(file):
    """计算文件MD5哈希值"""
    hash_md5 = hashlib.md5()
    for chunk in file.chunks():
        hash_md5.update(chunk)
    return hash_md5.hexdigest()


class UploadedFile(BaseModel):
    """上传文件管理"""
    file = models.FileField(upload_to='uploads/%Y/%m/%d/', verbose_name='文件')
    original_name = models.CharField(max_length=255, verbose_name='原始文件名')
    file_size = models.BigIntegerField(verbose_name='文件大小')
    file_type = models.CharField(max_length=50, verbose_name='文件类型')
    mime_type = models.CharField(max_length=100, verbose_name='MIME类型')
    hash_md5 = models.CharField(max_length=32, verbose_name='MD5哈希')
    is_processed = models.BooleanField(default=False, verbose_name='是否已处理')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = '上传文件'
        verbose_name_plural = '上传文件'
        
    def __str__(self):
        return self.original_name
    
    def save(self, *args, **kwargs):
        if self.file and not self.hash_md5:
            self.hash_md5 = get_file_hash(self.file)
        if self.file and not self.file_size:
            self.file_size = self.file.size
        if self.file and not self.original_name:
            self.original_name = os.path.basename(self.file.name)
        super().save(*args, **kwargs)
    
    @property
    def file_extension(self):
        """获取文件扩展名"""
        return os.path.splitext(self.original_name)[1].lower()
    
    @property
    def is_image(self):
        """判断是否为图片文件"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        return self.file_extension in image_extensions
    
    @property
    def is_document(self):
        """判断是否为文档文件"""
        doc_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.txt']
        return self.file_extension in doc_extensions
