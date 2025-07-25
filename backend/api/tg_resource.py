from fastapi import APIRouter, Depends, Query
from typing import Any, Dict, List, Optional
from api.deps import get_current_user
from models.user import User
from schemas.response import Response
from utils.tg_resource_sdk import tg_resource
import base64
from urllib.parse import quote
from loguru import logger
from datetime import datetime
from utils.config_manager import config_manager

router = APIRouter(prefix="/tg-resource", tags=["TG资源"])

def process_image_url(url: str) -> str:
    """
    处理图片URL，将Telegram CDN的URL转换为代理URL
    根据配置文件中的use_proxy决定是否使用代理
    """
    if not url:
        return url
        
    # 检查是否需要代理
    sys_config = config_manager.get_config()
    use_proxy = sys_config.get("use_proxy", False)
    
    if use_proxy and "cdn-telegram.org" in url:
        try:
            # 先对URL进行编码
            encoded_url = quote(url)
            # 再进行base64编码
            base64_url = base64.urlsafe_b64encode(encoded_url.encode('utf-8')).decode('utf-8')
            return f"/api/v1/proxy/image_proxy?url={base64_url}"
        except Exception as e:
            logger.error(f"处理图片URL时出错: {str(e)}")
            return url
    return url

def organize_search_results(results: Any) -> List[Dict]:
    """
    组织搜索结果，按频道分组
    """
    try:
        # 确保我们有有效的结果
        if results is None:
            return []
            
        # 处理字典类型的结果
        if isinstance(results, dict):
            # 如果结果是包装在字典中的列表
            if "data" in results:
                if isinstance(results["data"], dict) and "data" in results["data"]:
                    results = results["data"]["data"]
                else:
                    results = results["data"]
            elif "list" in results:
                results = results["list"]
            elif "items" in results:
                results = results["items"]
                
        # 确保结果是列表类型
        if not isinstance(results, list):
            return []
            
        # 按频道ID分组
        channel_groups = {}
        
        for result in results:
            if not isinstance(result, dict):
                continue
                
            # 获取频道信息
            channel_info = result.get("channelInfo", {})
            channel_id = channel_info.get("id")
            if not channel_id:
                continue
                
            channel_name = channel_info.get("name", "")
            channel_logo = channel_info.get("channelLogo", "")
            
            # 处理频道logo
            if channel_logo:
                channel_logo = process_image_url(channel_logo)
                
            # 创建或获取频道组
            if channel_id not in channel_groups:
                channel_groups[channel_id] = {
                    "list": [],
                    "channelInfo": {
                        "id": channel_id,
                        "name": channel_name,
                        "channelLogo": channel_logo
                    },
                    "id": channel_id
                }
                
            # 处理资源列表
            resource_list = result.get("list", [])
            if not isinstance(resource_list, list):
                continue
                
            for resource in resource_list:
                try:
                    # 处理图片URL
                    image_url = resource.get("image", "")
                    if image_url:
                        image_url = process_image_url(image_url)
                        
                    # 处理云盘链接
                    cloud_links = resource.get("cloudLinks") or resource.get("cloud_links") or []
                    if isinstance(cloud_links, str):
                        cloud_links = [cloud_links]
                        
                    # 处理标签
                    tags = resource.get("tags") or []
                    if isinstance(tags, str):
                        tags = [tag.strip() for tag in tags.split("#") if tag.strip()]
                        tags = [f"#{tag}" for tag in tags]
                        
                    # 构建标准化的结果项
                    item = {
                        "messageId": str(resource.get("messageId") or resource.get("message_id", "")),
                        "title": resource.get("title", ""),
                        "completeTitle": None,
                        "link": None,
                        "pubDate": resource.get("pubDate") or resource.get("pub_date") or datetime.now().isoformat(),
                        "content": resource.get("content") or resource.get("description", ""),
                        "description": None,
                        "image": image_url,
                        "cloudLinks": cloud_links,
                        "tags": tags,
                        "cloudType": resource.get("cloudType") or resource.get("cloud_type", ""),
                        "channel": channel_name,
                        "channelId": channel_id
                    }
                    
                    channel_groups[channel_id]["list"].append(item)
                    
                except Exception as e:
                    logger.error(f"处理资源项时出错: {str(e)}")
                    continue
                
        return list(channel_groups.values())
        
    except Exception as e:
        logger.error(f"组织搜索结果时出错: {str(e)}")
        return []

@router.get("/search")
async def search_resources(
    keyword: str = Query(default="", description="搜索关键词"),
    channel_id: Optional[str] = Query(default=None, description="频道ID（可选）"),
    message_id: Optional[str] = Query(default=None, description="消息ID（可选，用于分页）"),
    current_user: User = Depends(get_current_user)
):
    """
    搜索TG资源
    
    参数:
    - keyword: 搜索关键词
    - channel_id: 指定频道ID（可选）
    - message_id: 指定消息ID（可选，用于分页）
    
    返回示例:
    ```json
    {
        "code": 200,
        "message": "操作成功",
        "data": {
            "data": [
                {
                    "list": [
                        {
                            "messageId": "123",
                            "title": "资源标题",
                            "completeTitle": null,
                            "link": null,
                            "pubDate": "2024-03-21T10:00:00Z",
                            "content": "资源描述",
                            "description": null,
                            "image": "https://example.com/image.jpg",
                            "cloudLinks": [
                                "https://pan.example.com/xxx"
                            ],
                            "tags": ["#资源", "#电影"],
                            "cloudType": "aliyun",
                            "channel": "频道名称",
                            "channelId": "channel123"
                        }
                    ],
                    "channelInfo": {
                        "id": "channel123",
                        "name": "频道名称",
                        "channelLogo": "https://example.com/logo.jpg"
                    },
                    "id": "channel123"
                }
            ]
        }
    }
    ```
    
    说明:
    1. 如果不指定 channel_id，将搜索所有已配置的频道
    2. 可以通过 message_id 参数实现分页，获取指定消息之前的内容
    3. 返回的资源列表按时间倒序排列
    4. 只返回包含云盘链接的消息
    5. cloudType 表示云盘类型，支持：
       - aliyun: 阿里云盘
       - tianyiyun: 天翼云盘
       - baidu: 百度网盘
    """
    try:
        # 获取搜索结果
        logger.info(f"开始搜索，关键词: {keyword}, 频道ID: {channel_id}, 消息ID: {message_id}")
        results = await tg_resource.search_all(
            keyword=keyword,
            channel_id=channel_id,
            message_id=message_id
        )
        
        # 组织结果
        organized_results = organize_search_results(results)
        
        return Response(
            code=200,
            message="操作成功",
            data=organized_results
        )
        
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        return Response(
            code=-1,
            message=f"搜索失败: {str(e)}"
        )

@router.get("/config", response_model=Response[Dict[str, Any]])
async def get_resource_config(
    current_user: User = Depends(get_current_user)
):
    """
    获取TG资源配置
    
    返回示例:
    ```json
    {
        "code": 200,
        "message": "操作成功",
        "data": {
            "telegram": {
                "baseUrl": "https://t.me/s",
                "channels": [
                    {"id": "ailaoban", "name": "AI老班"},
                    {"id": "ailiaoba", "name": "AI聊吧"}
                ]
            },
            "cloudPatterns": {
                "aliyun": "https?://www\\.aliyundrive\\.com/s/[a-zA-Z0-9]+",
                "tianyiyun": "https?://cloud\\.189\\.cn/web/share\\?code=[a-zA-Z0-9]+"
            }
        }
    }
    ```
    """
    config = tg_resource._get_config()
    return Response(data=config)

@router.put("/config", response_model=Response)
async def update_resource_config(
    channels: Optional[List[Dict[str, str]]] = None,
    patterns: Optional[Dict[str, str]] = None,
    current_user: User = Depends(get_current_user)
):
    """
    更新TG资源配置
    
    参数:
    - channels: 频道列表，格式：[{"id": "频道ID", "name": "频道名称"}]
    - patterns: 云盘链接匹配模式，格式：{"aliyun": "正则表达式"}
    
    示例:
    ```json
    {
        "channels": [
            {"id": "ailaoban", "name": "AI老班"},
            {"id": "ailiaoba", "name": "AI聊吧"}
        ],
        "patterns": {
            "aliyun": "https?://www\\.aliyundrive\\.com/s/[a-zA-Z0-9]+",
            "tianyiyun": "https?://cloud\\.189\\.cn/web/share\\?code=[a-zA-Z0-9]+"
        }
    }
    ```
    """
    await tg_resource.update_config(channels, patterns)
    return Response(message="配置更新成功") 