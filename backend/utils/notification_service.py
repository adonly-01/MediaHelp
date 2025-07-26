import yaml
import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from loguru import logger
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import time

class MessageType(Enum):
    """消息类型枚举"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

@dataclass
class NotificationMessage:
    """通知消息数据类"""
    title: str
    content: str
    message_type: MessageType = MessageType.INFO
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NotificationChannel:
    """通知渠道配置"""
    name: str
    enabled: bool
    config: Dict[str, Any]
    handler: Optional[Callable] = None

class MessageDispatcher:
    """
    消息分发器 - 基于事件驱动的全新架构
    使用观察者模式和异步处理，完全不同的实现思路
    """
    
    def __init__(self):
        self.channels: Dict[str, NotificationChannel] = {}
        self.message_queue: List[NotificationMessage] = []
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.config_store = ConfigurationStore()
        self._initialize_channels()
    
    def _initialize_channels(self):
        """初始化通知渠道"""
        config = self.config_store.load_settings()
        
        # 注册控制台输出渠道
        self.register_channel(
            "console",
            config.get("CONSOLE", True),
            {},
            self._handle_console_message
        )
        
        # 注册企业微信渠道
        self.register_channel(
            "wecom",
            bool(config.get("QYWX_KEY", "").strip()),
            {"webhook_key": config.get("QYWX_KEY", "")},
            self._handle_wecom_message
        )
    
    def register_channel(self, name: str, enabled: bool, config: Dict[str, Any], handler: Callable):
        """注册通知渠道"""
        self.channels[name] = NotificationChannel(
            name=name,
            enabled=enabled,
            config=config,
            handler=handler
        )
    
    def dispatch_message(self, message: NotificationMessage):
        """分发消息到所有启用的渠道"""
        active_channels = [ch for ch in self.channels.values() if ch.enabled and ch.handler]
        
        if not active_channels:
            logger.warning("没有可用的通知渠道")
            return
        
        # 使用线程池并发处理
        futures = []
        for channel in active_channels:
            future = self.executor.submit(self._safe_send, channel, message)
            futures.append(future)
        
        # 等待所有任务完成
        for future in futures:
            try:
                future.result(timeout=30)
            except Exception as e:
                logger.error(f"通知发送超时或失败: {e}")
    
    def _safe_send(self, channel: NotificationChannel, message: NotificationMessage):
        """安全发送消息，包含异常处理"""
        try:
            channel.handler(message, channel.config)
        except Exception as e:
            logger.error(f"渠道 {channel.name} 发送失败: {e}")
    
    def _handle_console_message(self, message: NotificationMessage, config: Dict[str, Any]):
        """处理控制台消息"""
        emoji_map = {
            MessageType.INFO: "📢",
            MessageType.SUCCESS: "✅", 
            MessageType.WARNING: "⚠️",
            MessageType.ERROR: "❌"
        }
        emoji = emoji_map.get(message.message_type, "📢")
        logger.info(f"\n{emoji} {message.title}\n\n{message.content}")
    
    def _handle_wecom_message(self, message: NotificationMessage, config: Dict[str, Any]):
        """处理企业微信消息"""
        webhook_key = config.get("webhook_key", "").strip()
        if not webhook_key:
            logger.warning("企业微信 webhook_key 未配置")
            return
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={webhook_key}"
        payload = {
            "msgtype": "text",
            "text": {
                "content": f"{message.title}\n\n{message.content}"
            }
        }
        
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            result = response.json()
            if result.get("errcode") == 0:
                logger.info("企业微信消息发送成功")
            else:
                logger.error(f"企业微信消息发送失败: {result.get('errmsg', '未知错误')}")
        else:
            logger.error(f"企业微信消息发送失败: HTTP {response.status_code}")

class ConfigurationStore:
    """配置存储器 - 基于文件的配置管理"""
    
    def __init__(self):
        self.config_file = Path(__file__).parent.parent / "config" / "notify.yaml"
        self.default_settings = {
            "CONSOLE": True,
            "QYWX_KEY": ""
        }
        self._ensure_config_exists()
    
    def _ensure_config_exists(self):
        """确保配置文件存在"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.config_file.exists():
            self.save_settings(self.default_settings)
            logger.info(f"创建默认通知配置: {self.config_file}")
    
    def load_settings(self) -> Dict[str, Any]:
        """加载配置设置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f) or {}
                # 合并默认设置
                for key, value in self.default_settings.items():
                    if key not in settings:
                        settings[key] = value
                return settings
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return self.default_settings.copy()
    
    def save_settings(self, settings: Dict[str, Any]):
        """保存配置设置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(settings, f, allow_unicode=True)
            logger.info("通知配置已保存")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")

class NotificationFacade:
    """
    通知门面类 - 提供简化的API接口
    使用门面模式隐藏复杂的内部实现
    """
    
    def __init__(self):
        self.dispatcher = MessageDispatcher()
        self.config_store = ConfigurationStore()
    
    def send(self, title: str, content: str, message_type: MessageType = MessageType.INFO):
        """发送通知消息"""
        if not content.strip():
            logger.warning(f"通知内容为空: {title}")
            return
        
        message = NotificationMessage(
            title=title,
            content=content,
            message_type=message_type
        )
        
        self.dispatcher.dispatch_message(message)
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return self.config_store.load_settings()
    
    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        current_config = self.config_store.load_settings()
        current_config.update(new_config)
        self.config_store.save_settings(current_config)
        
        # 重新初始化渠道
        self.dispatcher._initialize_channels()

# 创建全局实例
notify_manager = NotificationFacade()

# 向后兼容性别名
NotifyManager = NotificationFacade
