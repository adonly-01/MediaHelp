import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

class ConfigManager:
    _instance = None
    _config: Dict[str, Any] = {}
    _default_config = {
        # Emby 配置
        "emby_url": "",  # Emby 服务器地址
        "emby_api_key": "",  # Emby API密钥
        # Alist 配置
        "alist_url": "",  # Alist 服务器地址
        "alist_api_key": "",  # Alist API密钥
        # 天翼云盘配置
        "tianyiAccount": "",  # 天翼云盘账号
        "tianyiPassword": "",  # 天翼云盘密码
        "tianyiCookie": "",  # 天翼云盘cookie
        "cloud189_session": {  # 天翼云盘session信息
            "access_token": "",
            "session_key": "",
            "expires_in": 0
        },
        # 代理配置
        "use_proxy": False,  # 是否使用代理
        "proxy_host": "",  # 代理主机地址
        "proxy_port": "",  # 代理端口
        "proxy_username": "",  # 代理用户名（可选）
        "proxy_password": "",  # 代理密码（可选）
        # TG资源配置
        "tg_resource": {
            "telegram": {
                "baseUrl": "https://t.me/s",
                "channels": [
                    {"id": "ailaoban", "name": "AI老班", "enable": True},
                    {"id": "ailiaoba", "name": "AI聊吧", "enable": True}
                ]
            },
            "cloudPatterns": {
                "aliyun": "https?://www\\.aliyundrive\\.com/s/[a-zA-Z0-9]+",
                "tianyiyun": "https?://cloud\\.189\\.cn/t/[a-zA-Z0-9]+",
                "baidu": "https?://pan\\.baidu\\.com/s/[a-zA-Z0-9_-]+"
            }
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._init_config()
        return cls._instance

    def _init_config(self):
        """初始化配置"""
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
        self._config_file = os.path.join(config_dir, "sys.yaml")

        # 创建配置目录
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        # 读取或创建配置文件
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"读取配置文件失败: {e}")
                self._config = {}
        else:
            self._config = {}
            
        # 使用默认配置补充缺失的配置项
        self._ensure_default_config()

    def _ensure_default_config(self):
        """确保所有默认配置项都存在"""
        is_modified = False
        
        def update_nested_dict(current: dict, default: dict) -> bool:
            modified = False
            for key, value in default.items():
                if key not in current:
                    current[key] = value
                    modified = True
                elif isinstance(value, dict) and isinstance(current[key], dict):
                    if update_nested_dict(current[key], value):
                        modified = True
            return modified

        if update_nested_dict(self._config, self._default_config):
            is_modified = True

        if is_modified:
            self._save_config()

    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self._config, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")

    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return self._config

    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        def update_nested_dict(current: dict, updates: dict):
            for key, value in updates.items():
                if isinstance(value, dict) and key in current and isinstance(current[key], dict):
                    update_nested_dict(current[key], value)
                else:
                    current[key] = value

        update_nested_dict(self._config, new_config)
        self._save_config()

    def set_value(self, key: str, value: Any):
        """设置单个配置项的值"""
        keys = key.split('.')
        current = self._config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
        self._save_config()

# 创建全局实例
config_manager = ConfigManager()