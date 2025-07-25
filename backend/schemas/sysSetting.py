from pydantic import BaseModel, Field
from typing import Optional, Dict, List

class TGChannel(BaseModel):
    """TG频道配置"""
    id: str = Field(..., description="频道ID")
    name: str = Field(..., description="频道名称")
    enable: bool = Field(default=True, description="是否启用")

class TGConfig(BaseModel):
    """TG配置"""
    baseUrl: str = Field("https://t.me/s", description="TG基础URL")
    channels: List[TGChannel] = Field(default_factory=list, description="频道列表")

class TGResourceConfig(BaseModel):
    """TG资源配置"""
    telegram: TGConfig = Field(default_factory=TGConfig, description="TG配置")
    cloudPatterns: Dict[str, str] = Field(default_factory=dict, description="云盘链接匹配模式")

class SysSettingBase(BaseModel):
    """系统配置基础模型"""
    emby_url: str = Field(default="", description="Emby服务器地址")
    emby_api_key: str = Field(default="", description="Emby API密钥")
    alist_url: str = Field(default="", description="Alist服务器地址")
    alist_api_key: str = Field(default="", description="Alist API密钥")
    tianyiAccount: str = Field(default="", description="天翼账号")
    tianyiPassword: str = Field(default="", description="天翼密码")
    tg_resource: Optional[TGResourceConfig] = Field(
        default_factory=TGResourceConfig,
        description="TG资源配置"
    )

class SysSettingCreate(SysSettingBase):
    """创建系统配置模型"""
    pass

class SysSettingUpdate(BaseModel):
    """更新系统配置模型"""
    emby_url: Optional[str] = Field(default=None, description="Emby服务器地址")
    emby_api_key: Optional[str] = Field(default=None, description="Emby API密钥")
    alist_url: Optional[str] = Field(default=None, description="Alist服务器地址")
    alist_api_key: Optional[str] = Field(default=None, description="Alist API密钥")
    tianyiAccount: Optional[str] = Field(default=None, description="天翼账号")
    tianyiPassword: Optional[str] = Field(default=None, description="天翼密码")
    use_proxy: Optional[bool] = Field(default=None, description="是否使用代理")
    proxy_host: Optional[str] = Field(default=None, description="代理主机")
    proxy_port: Optional[str] = Field(default=None, description="代理端口")
    proxy_username: Optional[str] = Field(default=None, description="代理用户名")
    proxy_password: Optional[str] = Field(default=None, description="代理密码")

class ProxyConfig(BaseModel):
    use_proxy: bool = False
    proxy_host: Optional[str] = None
    proxy_port: Optional[str] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
