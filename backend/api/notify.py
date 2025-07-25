from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any
from api.deps import get_current_user
from models.user import User
from schemas.response import Response
from utils.notification_service import notify_manager

router = APIRouter(prefix="/notify", tags=["通知设置"])

class NotifyMessage(BaseModel):
    """通知消息模型"""
    title: str
    content: str

@router.get("/config", response_model=Response[Dict[str, Any]])
async def get_notify_config(current_user: User = Depends(get_current_user)):
    """获取通知配置"""
    config = notify_manager.get_config()
    return Response(data=config)

@router.put("/config", response_model=Response[Dict[str, Any]])
async def update_notify_config(
    config: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """更新通知配置"""
    notify_manager.update_config(config)
    updated_config = notify_manager.get_config()
    return Response(data=updated_config)

@router.post("/send", response_model=Response)
async def send_notify(
    message: NotifyMessage,
    current_user: User = Depends(get_current_user)
):
    """发送通知"""
    notify_manager.send(message.title, message.content)
    return Response(message="通知发送成功") 