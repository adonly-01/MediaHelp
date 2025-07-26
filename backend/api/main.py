from fastapi import APIRouter
from api.auth import router as auth_router
from api.douban import router as douban_router
from api.sysSetting import router as sysSetting_router
from api.notify import router as notify_router
from api.tg_resource import router as tg_resource_router
from api import proxy
from api.cloud189 import router as cloud189_router
from api.scheduled import router as scheduled_router
from api.logs import router as logs_router
from api.emby import router as emby_router
from api.smart_rename import router as smart_rename_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(douban_router)
api_router.include_router(sysSetting_router)
api_router.include_router(notify_router)
api_router.include_router(tg_resource_router)
api_router.include_router(cloud189_router)
api_router.include_router(scheduled_router, prefix="/scheduled", tags=["scheduled"])
api_router.include_router(logs_router)
api_router.include_router(emby_router)
api_router.include_router(smart_rename_router)

# 注册代理服务路由
api_router.include_router(proxy.router)
