from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from api.deps import get_current_user
from models.user import User
from schemas.response import Response
from utils.media_renamer import MediaRenamer, SmartBatchRenamer
from utils.notification_service import notification_manager
from loguru import logger

router = APIRouter(prefix="/smart-rename", tags=["智能重命名"])

class RenameFileRequest(BaseModel):
    """单文件重命名请求"""
    filename: str = Field(..., description="原文件名")
    custom_title: Optional[str] = Field(None, description="自定义标题")
    style: str = Field("simple", description="重命名风格")
    custom_template: Optional[str] = Field(None, description="自定义模板")

class BatchRenameRequest(BaseModel):
    """批量重命名请求"""
    filenames: List[str] = Field(..., description="文件名列表")
    custom_title: Optional[str] = Field(None, description="自定义标题")
    custom_season: Optional[int] = Field(None, description="自定义季数")
    directory_path: str = Field("", description="目录路径")
    style: str = Field("simple", description="重命名风格")

class PreviewRenameRequest(BaseModel):
    """预览重命名请求"""
    filename: str = Field(..., description="原文件名")
    custom_title: Optional[str] = Field(None, description="自定义标题")
    style: str = Field("simple", description="重命名风格")
    custom_template: Optional[str] = Field(None, description="自定义模板")

class BatchPreviewRequest(BaseModel):
    """批量预览请求"""
    filenames: List[str] = Field(..., description="文件名列表")
    custom_title: Optional[str] = Field(None, description="自定义标题")
    custom_season: Optional[int] = Field(None, description="自定义季数")
    directory_path: str = Field("", description="目录路径")

class SuggestionsRequest(BaseModel):
    """重命名建议请求"""
    filename: str = Field(..., description="原文件名")
    custom_title: Optional[str] = Field(None, description="自定义标题")

class CustomTemplateRequest(BaseModel):
    """自定义模板请求"""
    name: str = Field(..., description="模板名称")
    template: str = Field(..., description="模板内容")
    description: str = Field("", description="模板描述")

class TemplatePreviewRequest(BaseModel):
    """模板预览请求"""
    template: str = Field(..., description="模板内容")
    sample_filename: str = Field("示例剧集.第01集.mp4", description="示例文件名")

class RenameWithTemplateRequest(BaseModel):
    """使用模板重命名请求"""
    filename: str = Field(..., description="原文件名")
    template_name: str = Field(..., description="模板名称")
    custom_title: Optional[str] = Field(None, description="自定义标题")

# 创建全局实例
media_renamer = MediaRenamer()
batch_renamer = SmartBatchRenamer()

@router.post("/file", response_model=Response[str])
async def rename_single_file(
    req: RenameFileRequest,
    current_user: User = Depends(get_current_user)
):
    """重命名单个文件"""
    try:
        result = media_renamer.rename_file(
            filename=req.filename,
            style=req.style,
            custom_title=req.custom_title,
            custom_template=req.custom_template
        )
        return Response(data=result, message="重命名成功")
    except Exception as e:
        logger.error(f"单文件重命名失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/batch", response_model=Response[List[Dict[str, Any]]])
async def rename_batch_files(
    req: BatchRenameRequest,
    current_user: User = Depends(get_current_user)
):
    """批量重命名文件"""
    try:
        results = batch_renamer.batch_rename_with_context(
            filenames=req.filenames,
            directory_path=req.directory_path,
            custom_title=req.custom_title,
            custom_season=req.custom_season
        )

        # 发送批量重命名成功通知
        if results:
            await notification_manager.notify_rename_success(
                req.custom_title or "批量重命名",
                [{"file_name": f, "file_name_re": results.get(f)} for f in req.filenames]
            )

        return Response(data=results, message="批量重命名成功")
    except Exception as e:
        logger.error(f"批量重命名失败: {e}")

        # 发送批量重命名错误通知
        await notification_manager.notify_rename_error(
            req.custom_title or "批量重命名",
            str(e)
        )

        raise HTTPException(status_code=400, detail=str(e))

@router.post("/preview", response_model=Response[Dict[str, Any]])
async def preview_rename(
    req: PreviewRenameRequest,
    current_user: User = Depends(get_current_user)
):
    """预览重命名结果"""
    try:
        result = media_renamer.preview_rename(
            filename=req.filename,
            style=req.style,
            custom_title=req.custom_title
        )
        return Response(data=result, message="预览成功")
    except Exception as e:
        logger.error(f"预览重命名失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/preview/batch", response_model=Response[Dict[str, Any]])
async def preview_batch_rename(
    req: BatchPreviewRequest,
    current_user: User = Depends(get_current_user)
):
    """预览批量重命名结果"""
    try:
        result = media_renamer.preview_batch_rename(
            filenames=req.filenames,
            directory_path=req.directory_path,
            custom_title=req.custom_title
        )
        return Response(data=result, message="批量预览成功")
    except Exception as e:
        logger.error(f"批量预览失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/suggestions", response_model=Response[List[Dict[str, str]]])
async def get_rename_suggestions(
    req: SuggestionsRequest,
    current_user: User = Depends(get_current_user)
):
    """获取重命名建议"""
    try:
        # 使用媒体重命名器生成多种建议
        suggestions = []

        # 简洁格式建议
        simple_result = media_renamer.rename_file(
            filename=req.filename,
            style="simple",
            custom_title=req.custom_title
        )
        suggestions.append({
            "style": "简洁格式",
            "result": simple_result
        })

        # 标准格式建议
        standard_result = media_renamer.rename_file(
            filename=req.filename,
            style="standard",
            custom_title=req.custom_title
        )
        suggestions.append({
            "style": "标准格式",
            "result": standard_result
        })

        return Response(data=suggestions, message="获取建议成功")
    except Exception as e:
        logger.error(f"获取重命名建议失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/templates", response_model=Response[Dict[str, Dict[str, Any]]])
async def get_all_templates(current_user: User = Depends(get_current_user)):
    """获取所有可用模板"""
    try:
        templates = media_renamer.get_all_templates()
        return Response(data=templates, message="获取模板成功")
    except Exception as e:
        logger.error(f"获取模板失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/templates", response_model=Response[bool])
async def add_custom_template(
    req: CustomTemplateRequest,
    current_user: User = Depends(get_current_user)
):
    """添加自定义模板"""
    try:
        success = media_renamer.add_custom_template(
            name=req.name,
            template=req.template,
            description=req.description
        )
        if success:
            return Response(data=True, message="模板添加成功")
        else:
            raise HTTPException(status_code=400, detail="模板添加失败，请检查模板格式")
    except Exception as e:
        logger.error(f"添加自定义模板失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/templates/{template_name}", response_model=Response[bool])
async def remove_custom_template(
    template_name: str,
    current_user: User = Depends(get_current_user)
):
    """删除自定义模板"""
    try:
        success = media_renamer.remove_custom_template(template_name)
        if success:
            return Response(data=True, message="模板删除成功")
        else:
            raise HTTPException(status_code=404, detail="模板不存在")
    except Exception as e:
        logger.error(f"删除自定义模板失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/templates/preview", response_model=Response[str])
async def preview_template(
    req: TemplatePreviewRequest,
    current_user: User = Depends(get_current_user)
):
    """预览模板效果"""
    try:
        result = media_renamer.preview_template(
            template=req.template,
            sample_filename=req.sample_filename
        )
        return Response(data=result, message="模板预览成功")
    except Exception as e:
        logger.error(f"模板预览失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/templates/variables", response_model=Response[Dict[str, str]])
async def get_template_variables(current_user: User = Depends(get_current_user)):
    """获取可用的模板变量"""
    try:
        variables = media_renamer.get_template_variables()
        return Response(data=variables, message="获取变量成功")
    except Exception as e:
        logger.error(f"获取模板变量失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/templates/rename", response_model=Response[str])
async def rename_with_template(
    req: RenameWithTemplateRequest,
    current_user: User = Depends(get_current_user)
):
    """使用指定模板重命名文件"""
    try:
        result = media_renamer.rename_with_template(
            filename=req.filename,
            template_name=req.template_name,
            custom_title=req.custom_title
        )
        return Response(data=result, message="模板重命名成功")
    except Exception as e:
        logger.error(f"模板重命名失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history", response_model=Response[List[Dict[str, str]]])
async def get_rename_history(current_user: User = Depends(get_current_user)):
    """获取重命名历史"""
    try:
        history = media_renamer.get_rename_history()
        return Response(data=history, message="获取历史成功")
    except Exception as e:
        logger.error(f"获取重命名历史失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/history", response_model=Response[bool])
async def clear_rename_history(current_user: User = Depends(get_current_user)):
    """清空重命名历史"""
    try:
        media_renamer.clear_history()
        return Response(data=True, message="历史清空成功")
    except Exception as e:
        logger.error(f"清空重命名历史失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/notification/status", response_model=Response[Dict[str, Any]])
async def get_notification_status(current_user: User = Depends(get_current_user)):
    """获取通知状态"""
    try:
        status = notification_manager.get_provider_status()
        return Response(data=status, message="获取通知状态成功")
    except Exception as e:
        logger.error(f"获取通知状态失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/notification/test", response_model=Response[Dict[str, bool]])
async def test_rename_notification(current_user: User = Depends(get_current_user)):
    """测试重命名通知"""
    try:
        # 发送测试通知
        test_files = [
            {"file_name": "1.mp4", "file_name_re": "测试剧集.S01E01.mp4"},
            {"file_name": "2.mp4", "file_name_re": "测试剧集.S01E02.mp4"}
        ]

        results = await notification_manager.notify_rename_success("测试任务", test_files)
        return Response(data=results, message="测试通知发送完成")
    except Exception as e:
        logger.error(f"测试重命名通知失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
