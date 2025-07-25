import yaml
import json
import requests
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

class NotificationService:
    """
    """
    _instance = None
    _config: Optional[Dict[str, Any]] = None
    
    # 简化的配置，只保留必要的通知方式
    _default_config = {
        # 控制台输出 - 用于调试和开发
        "CONSOLE": True,
        
        # 企业微信机器人 - 您当前使用的通知方式
        "QYWX_KEY": "",  # 企业微信机器人的 webhook key
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotificationService, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        """初始化通知服务"""
        self.config_path = Path(__file__).parent.parent / "config" / "notify.yaml"
        self._ensure_config_dir()
        self._load_config()

    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        config_dir = self.config_path.parent
        if not config_dir.exists():
            config_dir.mkdir(parents=True)

    def _load_config(self) -> None:
        """从文件加载配置"""
        if not self.config_path.exists():
            self._config = self._default_config.copy()
            self._save_config()
            logger.info(f"已创建默认通知配置文件：{self.config_path}")
        else:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
                # 检查是否有新增的配置项
                updated = False
                for key, value in self._default_config.items():
                    if key not in self._config:
                        self._config[key] = value
                        updated = True
                if updated:
                    self._save_config()
                    logger.info(f"通知配置文件已更新：{self.config_path}")

    def _save_config(self) -> None:
        """保存配置到文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, allow_unicode=True)

    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return self._config.copy()

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(new_config)
        self._save_config()
        logger.info("通知配置已更新")

    def _console_output(self, title: str, content: str) -> None:
        """控制台输出通知"""
        try:
            logger.info(f"\n📢 {title}\n\n{content}")
        except Exception as e:
            logger.error(f"控制台输出失败: {e}")

    def _wecom_robot(self, title: str, content: str) -> None:
        """企业微信机器人通知"""
        try:
            qywx_key = self._config.get("QYWX_KEY", "").strip()
            if not qywx_key:
                logger.warning("企业微信机器人 QYWX_KEY 未配置，跳过推送")
                return

            url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={qywx_key}"
            data = {
                "msgtype": "text",
                "text": {
                    "content": f"{title}\n\n{content}"
                }
            }

            response = requests.post(
                url, 
                json=data, 
                timeout=15,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    logger.info("企业微信机器人推送成功")
                else:
                    logger.error(f"企业微信机器人推送失败：{result.get('errmsg', '未知错误')}")
            else:
                logger.error(f"企业微信机器人推送失败：HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"企业微信机器人推送异常：{e}")

    def send(self, title: str, content: str) -> None:
        """发送通知"""
        if not content:
            logger.warning(f"{title} 推送内容为空")
            return

        # 收集启用的通知方式
        notify_methods = []
        
        # 控制台输出
        if self._config.get("CONSOLE", True):
            notify_methods.append(("控制台输出", self._console_output))
            
        # 企业微信机器人
        if self._config.get("QYWX_KEY", "").strip():
            notify_methods.append(("企业微信机器人", self._wecom_robot))

        if not notify_methods:
            logger.warning("没有启用任何通知方式")
            return

        # 创建线程并发发送通知
        threads = []
        for method_name, method_func in notify_methods:
            thread = threading.Thread(
                target=method_func, 
                args=(title, content), 
                name=f"notify-{method_name}"
            )
            threads.append(thread)
            thread.start()
            
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=30)  # 30秒超时

        logger.info(f"通知发送完成，使用了 {len(notify_methods)} 种通知方式")

# 创建全局通知服务实例
notify_manager = NotificationService()

# 为了保持向后兼容性，创建一个别名
NotifyManager = NotificationService
