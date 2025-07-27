import os
import yaml
import json
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List, Protocol
from loguru import logger
from utils.http_client import http_client


class NotificationProvider(Protocol):
    """通知提供者协议"""

    async def send_message(self, title: str, content: str) -> bool:
        """发送消息"""
        ...

    def is_configured(self) -> bool:
        """检查是否已配置"""
        ...


class BaseNotificationProvider(ABC):
    """通知提供者基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def send_message(self, title: str, content: str) -> bool:
        """发送消息的抽象方法"""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """检查配置的抽象方法"""
        pass


class WeChatWorkProvider(BaseNotificationProvider):
    """企业微信通知提供者"""

    def is_configured(self) -> bool:
        return bool(self.config.get("wecom_webhook_key"))

    async def send_message(self, title: str, content: str) -> bool:
        try:
            webhook_key = self.config.get("wecom_webhook_key")
            endpoint = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={webhook_key}"

            payload = {
                "msgtype": "text",
                "text": {
                    "content": f"{title}\n\n{content}"
                }
            }

            response = await http_client.post(endpoint, json=payload)

            if isinstance(response, dict) and response.get("errcode") == 0:
                logger.info("企业微信通知发送成功")
                return True
            else:
                logger.error(f"企业微信通知发送失败: {response}")
                return False

        except Exception as e:
            logger.error(f"企业微信通知发送异常: {str(e)}")
            return False


class TelegramProvider(BaseNotificationProvider):
    """Telegram通知提供者"""

    def is_configured(self) -> bool:
        return bool(
            self.config.get("telegram_bot_token") and
            self.config.get("telegram_user_id")
        )

    async def send_message(self, title: str, content: str) -> bool:
        try:
            bot_token = self.config.get("telegram_bot_token")
            user_id = self.config.get("telegram_user_id")
            api_host = self.config.get("telegram_api_host")

            # 构建API端点
            if api_host:
                endpoint = f"{api_host}/bot{bot_token}/sendMessage"
            else:
                endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            payload = {
                "chat_id": user_id,
                "text": f"{title}\n\n{content}",
                "parse_mode": "HTML"
            }

            response = await http_client.post(endpoint, json=payload)

            if isinstance(response, dict) and response.get("ok"):
                logger.info("Telegram通知发送成功")
                return True
            else:
                logger.error(f"Telegram通知发送失败: {response}")
                return False

        except Exception as e:
            logger.error(f"Telegram通知发送异常: {str(e)}")
            return False


class NotificationProviderFactory:
    """通知提供者工厂"""

    _providers = {
        "wechat_work": WeChatWorkProvider,
        "telegram": TelegramProvider,
    }

    @classmethod
    def create_provider(cls, provider_type: str, config: Dict[str, Any]) -> Optional[BaseNotificationProvider]:
        """创建通知提供者实例"""
        provider_class = cls._providers.get(provider_type)
        if provider_class:
            return provider_class(config)
        return None

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """获取可用的通知提供者类型"""
        return list(cls._providers.keys())


class NotificationEvent:
    """通知事件"""

    def __init__(self, title: str, content: str, priority: str = "normal"):
        self.title = title
        self.content = content
        self.priority = priority
        self.timestamp = asyncio.get_event_loop().time()


class NotificationManager:
    """通知管理器 - 事件驱动架构"""

    _instance = None
    _config: Optional[Dict[str, Any]] = None
    _providers: List[BaseNotificationProvider] = []
    _event_queue: asyncio.Queue = None
    
    # 配置模式定义
    _config_schema = {
        "wecom_webhook_key": {"type": str, "default": "", "description": "企业微信Webhook密钥"},
        "telegram_bot_token": {"type": str, "default": "", "description": "Telegram机器人Token"},
        "telegram_user_id": {"type": str, "default": "", "description": "Telegram用户ID"},
        "telegram_api_host": {"type": str, "default": "", "description": "Telegram API地址"},
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotificationManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化通知管理器"""
        self.config_path = Path(__file__).parent.parent / "config" / "notification.yaml"
        self._event_queue = asyncio.Queue()
        self._ensure_config_directory()
        self._load_configuration()
        self._setup_providers()

    def _ensure_config_directory(self) -> None:
        """确保配置目录存在"""
        config_dir = self.config_path.parent
        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)

    def _load_configuration(self) -> None:
        """加载配置文件"""
        default_config = {key: schema["default"] for key, schema in self._config_schema.items()}

        if not self.config_path.exists():
            self._config = default_config
            self._persist_configuration()
        else:
            try:
                with open(self.config_path, 'r', encoding='utf-8') as file:
                    loaded_config = yaml.safe_load(file) or {}
                self._config = {**default_config, **loaded_config}
            except Exception as e:
                logger.error(f"配置加载失败: {e}")
                self._config = default_config

    def _persist_configuration(self) -> None:
        """持久化配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as file:
                yaml.safe_dump(self._config, file, allow_unicode=True, sort_keys=False)
        except Exception as e:
            logger.error(f"配置保存失败: {e}")

    def _setup_providers(self) -> None:
        """设置通知提供者"""
        self._providers = []

        # 创建企业微信提供者
        wechat_provider = NotificationProviderFactory.create_provider("wechat_work", self._config)
        if wechat_provider and wechat_provider.is_configured():
            self._providers.append(wechat_provider)

        # 创建Telegram提供者
        telegram_provider = NotificationProviderFactory.create_provider("telegram", self._config)
        if telegram_provider and telegram_provider.is_configured():
            self._providers.append(telegram_provider)

    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self._config.copy()

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """更新配置"""
        if self._config is None:
            self._config = {}

        # 验证并更新配置
        for key, value in new_config.items():
            if key in self._config_schema:
                self._config[key] = value

        self._persist_configuration()
        self._setup_providers()  # 重新设置提供者
        logger.info("通知配置更新完成")

    async def dispatch_notification(self, title: str, content: str, priority: str = "normal") -> Dict[str, bool]:
        """分发通知事件"""
        if not content.strip():
            logger.warning(f"通知内容为空，跳过发送: {title}")
            return {}

        # 创建通知事件
        event = NotificationEvent(title, content, priority)

        # 并发发送到所有配置的提供者
        results = {}
        if not self._providers:
            logger.info("未配置任何通知提供者")
            return results

        # 使用asyncio.gather并发执行
        tasks = []
        provider_names = []

        for provider in self._providers:
            if provider.is_configured():
                tasks.append(provider.send_message(event.title, event.content))
                provider_names.append(provider.__class__.__name__)

        if tasks:
            try:
                send_results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(send_results):
                    provider_name = provider_names[i]
                    if isinstance(result, Exception):
                        logger.error(f"{provider_name} 发送失败: {result}")
                        results[provider_name] = False
                    else:
                        results[provider_name] = result
            except Exception as e:
                logger.error(f"通知分发异常: {e}")

        return results

    async def send_notification(self, title: str, content: str) -> None:
        """发送通知（异步接口）"""
        await self.dispatch_notification(title, content)

    def send(self, title: str, content: str) -> None:
        """发送通知（同步接口，兼容性）"""
        try:
            # 检查是否在事件循环中
            try:
                loop = asyncio.get_running_loop()
                # 如果在事件循环中，创建任务
                asyncio.create_task(self.send_notification(title, content))
            except RuntimeError:
                # 如果不在事件循环中，创建新的事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.send_notification(title, content))
                finally:
                    loop.close()
        except Exception as e:
            logger.error(f"通知发送失败: {e}")

    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """获取提供者状态"""
        status = {}
        for provider in self._providers:
            provider_name = provider.__class__.__name__
            status[provider_name] = {
                "configured": provider.is_configured(),
                "type": provider_name.replace("Provider", "").lower()
            }
        return status

    async def test_providers(self) -> Dict[str, bool]:
        """测试所有提供者"""
        test_title = "MediaHelper 通知测试"
        test_content = "这是一条测试消息，用于验证通知配置是否正确。"

        return await self.dispatch_notification(test_title, test_content)


# 创建全局单例实例
notification_manager = NotificationManager()
