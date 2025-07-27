from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any
from api.deps import get_current_user
from models.user import User
from schemas.response import Response
from utils.notification_service import notification_manager

router = APIRouter(prefix="/notify", tags=["通知设置"])

class NotifyMessage(BaseModel):
    """通知消息模型"""
    title: str
    content: str

@router.get("/config", response_model=Response[Dict[str, Any]])
async def get_notify_config(current_user: User = Depends(get_current_user)):
    """获取通知配置"""
    config = notification_manager.get_config()
    return Response(data=config)

@router.put("/config", response_model=Response[Dict[str, Any]])
async def update_notify_config(
    config: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """更新通知配置"""
    notification_manager.update_config(config)
    updated_config = notification_manager.get_config()
    return Response(data=updated_config)

@router.post("/send", response_model=Response)
async def send_notify(
    message: NotifyMessage,
    current_user: User = Depends(get_current_user)
):
    """发送通知"""
    await notification_manager.send_notification(message.title, message.content)
    return Response(message="通知发送成功")

@router.get("/status", response_model=Response[Dict[str, Any]])
async def get_notify_status(current_user: User = Depends(get_current_user)):
    """获取通知提供者状态"""
    status = notification_manager.get_provider_status()
    return Response(data=status)

@router.post("/test", response_model=Response[Dict[str, bool]])
async def test_notify_providers(current_user: User = Depends(get_current_user)):
    """测试所有通知提供者"""
    results = await notification_manager.test_providers()
    return Response(data=results, message="通知测试完成")