#!/usr/bin/env python
"""
Replit环境OCR测试脚本
用于诊断OCR处理问题
"""
import os
import sys
import django
from pathlib import Path

# 设置Django环境
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.replit')

django.setup()

import logging
import requests
from django.conf import settings
from apps.ocr.services import GeminiOCRService, OpenAIOCRService, get_ocr_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_network_connectivity():
    """测试网络连接"""
    logger.info("=== 测试网络连接 ===")
    
    # 测试基本网络连接
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        logger.info("✓ 基本网络连接正常")
    except OSError as e:
        logger.error(f"✗ 基本网络连接失败: {e}")
        return False
    
    # 测试HTTP请求
    try:
        response = requests.get("https://httpbin.org/ip", timeout=10)
        logger.info(f"✓ HTTP请求成功: {response.status_code}")
        logger.info(f"IP地址: {response.json()}")
    except Exception as e:
        logger.error(f"✗ HTTP请求失败: {e}")
        return False
    
    return True

def test_gemini_api():
    """测试Gemini API连接"""
    logger.info("=== 测试Gemini API ===")
    
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if not api_key:
        logger.error("✗ Gemini API密钥未设置")
        return False
    
    logger.info(f"✓ Gemini API密钥已设置: {api_key[:10]}...")
    
    base_url = getattr(settings, 'GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com')
    logger.info(f"✓ Gemini基础URL: {base_url}")
    
    # 测试API连接
    try:
        url = f"{base_url}/v1beta/models"
        headers = {'x-goog-api-key': api_key}
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            logger.info("✓ Gemini API连接成功")
            return True
        else:
            logger.error(f"✗ Gemini API连接失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"✗ Gemini API连接异常: {e}")
        return False

def test_openai_api():
    """测试OpenAI API连接"""
    logger.info("=== 测试OpenAI API ===")
    
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        logger.error("✗ OpenAI API密钥未设置")
        return False
    
    logger.info(f"✓ OpenAI API密钥已设置: {api_key[:10]}...")
    
    base_url = getattr(settings, 'OPENAI_BASE_URL', 'https://api.openai.com/v1')
    logger.info(f"✓ OpenAI基础URL: {base_url}")
    
    # 测试API连接
    try:
        url = f"{base_url}/models"
        headers = {'Authorization': f'Bearer {api_key}'}
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            logger.info("✓ OpenAI API连接成功")
            return True
        else:
            logger.error(f"✗ OpenAI API连接失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"✗ OpenAI API连接异常: {e}")
        return False

def test_ocr_service():
    """测试OCR服务初始化"""
    logger.info("=== 测试OCR服务 ===")
    
    try:
        service = get_ocr_service()
        logger.info(f"✓ OCR服务创建成功: {service.__class__.__name__}")
        return True
    except Exception as e:
        logger.error(f"✗ OCR服务创建失败: {e}")
        return False

def test_file_system():
    """测试文件系统"""
    logger.info("=== 测试文件系统 ===")
    
    # 检查媒体目录
    media_root = getattr(settings, 'MEDIA_ROOT', None)
    if media_root and os.path.exists(media_root):
        logger.info(f"✓ 媒体目录存在: {media_root}")
    else:
        logger.warning(f"? 媒体目录不存在: {media_root}")
    
    # 检查测试数据
    test_data_dir = BASE_DIR / 'test_data'
    if test_data_dir.exists():
        test_files = list(test_data_dir.glob('*.jpg'))
        logger.info(f"✓ 测试数据目录存在，包含 {len(test_files)} 个图片文件")
        return len(test_files) > 0
    else:
        logger.warning("? 测试数据目录不存在")
        return False

def test_environment():
    """测试环境配置"""
    logger.info("=== 测试环境配置 ===")
    
    # 检查关键配置
    configs = [
        ('DEBUG', getattr(settings, 'DEBUG', None)),
        ('USE_PROXY', getattr(settings, 'USE_PROXY', None)),
        ('CELERY_TASK_ALWAYS_EAGER', getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', None)),
        ('USE_OPENAI_OCR', getattr(settings, 'USE_OPENAI_OCR', None)),
    ]
    
    for name, value in configs:
        logger.info(f"  {name}: {value}")
    
    # 检查环境变量
    env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY']
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            logger.info(f"  环境变量 {var}: {value}")

def main():
    """主测试函数"""
    logger.info("开始Replit环境OCR诊断")
    logger.info("=" * 50)
    
    # 运行所有测试
    tests = [
        test_environment,
        test_network_connectivity,
        test_file_system,
        test_ocr_service,
        test_gemini_api,
        test_openai_api,
    ]
    
    results = {}
    for test in tests:
        try:
            result = test()
            results[test.__name__] = result
        except Exception as e:
            logger.error(f"测试 {test.__name__} 发生异常: {e}")
            results[test.__name__] = False
        logger.info("-" * 30)
    
    # 总结
    logger.info("=== 测试结果总结 ===")
    for test_name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"{test_name}: {status}")
    
    # 建议
    logger.info("=== 建议 ===")
    if not results.get('test_network_connectivity', False):
        logger.info("- 检查网络连接和防火墙设置")
    
    if not results.get('test_gemini_api', False) and not results.get('test_openai_api', False):
        logger.info("- 检查API密钥和网络访问权限")
        logger.info("- 考虑使用备用OCR方案")
    
    if not results.get('test_file_system', False):
        logger.info("- 准备测试图片文件")

if __name__ == '__main__':
    main()