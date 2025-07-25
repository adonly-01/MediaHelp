import aiohttp
import asyncio
from typing import Optional, Dict, Any, Union
from loguru import logger
from utils.config_manager import config_manager

class HttpClient:
    _instance = None
    _session: Optional[aiohttp.ClientSession] = None
    _default_headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HttpClient, cls).__new__(cls)
        return cls._instance

    async def _ensure_session(self, headers: Dict[str, str] = None):
        """确保会话已创建"""
        if self._session is None or self._session.closed:
            # 获取代理配置
            sys_config = config_manager.get_config()
            proxy = None
            
            if sys_config.get("use_proxy", False):
                host = sys_config.get("proxy_host", "")
                port = sys_config.get("proxy_port", "")
                username = sys_config.get("proxy_username", "")
                password = sys_config.get("proxy_password", "")
                
                if host and port:
                    # 构建代理URL
                    if username and password:
                        proxy = f"http://{username}:{password}@{host}:{port}"
                        logger.info(f"使用带认证的代理: {host}:{port}")
                    else:
                        proxy = f"http://{host}:{port}"
                        logger.info(f"使用代理: {proxy}")
            
            merged_headers = {**self._default_headers}
            if headers:
                merged_headers.update(headers)
            
            # 创建会话
            self._session = aiohttp.ClientSession(
                headers=merged_headers,
                trust_env=True,  # 允许从环境变量读取代理设置
                connector=aiohttp.TCPConnector(
                    ssl=False,  # 禁用SSL验证
                    force_close=False,  # 不强制关闭连接
                    enable_cleanup_closed=True,  # 清理已关闭的连接
                    limit=100,  # 最大并发连接数
                    limit_per_host=20,  # 每个主机的最大并发连接数
                    keepalive_timeout=60  # 保持连接活跃的超时时间
                )
            )

    async def close(self):
        """关闭会话"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        json: Any = None,
        data: Any = None,
        timeout: int = 30,
        retry_times: int = 3,
        retry_delay: int = 1
    ) -> Union[Dict[str, Any], str]:
        """发送 HTTP 请求"""
        await self._ensure_session(headers)
        
        # 获取代理配置
        sys_config = config_manager.get_config()
        proxy = None
        if sys_config.get("use_proxy", False):
            host = sys_config.get("proxy_host", "")
            port = sys_config.get("proxy_port", "")
            if host and port:
                proxy = f"http://{host}:{port}"
        
        logger.info(f"请求参数: {method} {url} {params} {headers} {json} {data}")
        for i in range(retry_times):
            try:
                # logger.info(f"请求参数: {method} {url} {params} {headers} {json} {data}")
                async with self._session.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    json=json,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    allow_redirects=True,
                    verify_ssl=False,  # 禁用SSL验证
                    proxy=proxy  # 在请求时设置代理
                ) as response:
                    if response.status == 404:
                        raise aiohttp.ClientError(f"资源未找到: {url}")
                    
                    response.raise_for_status()
                    
                    content_type = response.headers.get('content-type', '').lower()
                    if 'application/json' in content_type:
                        result = await response.json()
                        # logger.info(f"请求响应: {result}")
                        return result
                    else:
                        result = await response.text()
                        return result
                        
            except asyncio.TimeoutError:
                logger.warning(f"请求超时 ({i + 1}/{retry_times}): {url}")
                if i == retry_times - 1:
                    raise
                    
            except aiohttp.ClientError as e:
                logger.error(f"请求错误 ({i + 1}/{retry_times}): {url}", exc_info=e)
                if i == retry_times - 1:
                    raise
                    
            await asyncio.sleep(retry_delay)

    async def get(self, url: str, **kwargs) -> Union[Dict[str, Any], str]:
        """发送 GET 请求"""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> Union[Dict[str, Any], str]:
        """发送 POST 请求"""
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> Union[Dict[str, Any], str]:
        """发送 PUT 请求"""
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> Union[Dict[str, Any], str]:
        """发送 DELETE 请求"""
        return await self.request("DELETE", url, **kwargs)

# 创建全局实例
http_client = HttpClient() 