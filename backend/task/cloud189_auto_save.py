# 天翼云盘自动保存任务
import re
from typing import Any, Dict, List, Optional
from loguru import logger
from utils import config_manager, logger_service, scheduled_manager
from utils.cloud189.client import Cloud189Client
from utils.media_renamer import MediaRenamer, SmartBatchRenamer
from utils.notification_service import notification_manager

class Cloud189AutoSave:
    """天翼云盘自动保存任务处理器"""

    def __init__(self):
        """初始化天翼云盘客户端和媒体重命名器"""
        # 任务相关属性
        self.client = None
        self.params = {}
        self.task = {}
        self.task_name = ""
        self.need_save_files_global = []

        # 初始化天翼云盘客户端
        self._init_cloud_client()

        # 初始化媒体重命名器
        self.media_renamer = MediaRenamer()
        self.batch_renamer = SmartBatchRenamer()

    def _init_cloud_client(self):
        """初始化天翼云盘客户端"""
        sys_config = config_manager.config_manager.get_config()
        username = sys_config.get("tianyiAccount", "")
        password = sys_config.get("tianyiPassword", "")
        sson_cookie = sys_config.get("tianyiCookie", "")

        logger.info(f"初始化天翼云盘客户端 - 用户名: {username[:3]}*** Cookie: {'已配置' if sson_cookie else '未配置'}")

        if (not username or not password) and not sson_cookie:
            logger.error("未配置天翼云盘账号，请在系统配置中添加 tianyiAccount 和 tianyiPassword 或 tianyiCookie")
            return

        self.client = Cloud189Client(
            username=username,
            password=password,
            sson_cookie=sson_cookie
        )
      
    async def dir_check_and_save(self, share_info: Dict, file_id: str = '', target_file_id: str = ''):
        """检查目录并保存文件的主要方法"""
        target_dir = target_file_id or self.params.get("targetDir", "-11")
        start_magic = self.params.get("startMagic", [])
        if not isinstance(start_magic, list):
            start_magic = [start_magic] if start_magic else []

        try:
            # 获取分享文件列表
            files_response = await self.client.list_share_files(
                share_id=share_info["shareId"],
                file_id=file_id if file_id else share_info["fileId"],
                share_mode=share_info.get("shareMode", "1"),
                access_code=share_info.get("accessCode", ""),
                is_folder=share_info.get("isFolder", "")
            )

            files = files_response.get("fileListAO", {}).get("fileList", [])
            folders = files_response.get("fileListAO", {}).get("folderList", [])

            # 获取目标文件列表
            target_response = await self.client.list_files(target_dir)
            target_files = target_response.get("fileListAO", {}).get("fileList", [])
            target_folders = target_response.get("fileListAO", {}).get("folderList", [])

            # 获取重命名配置
            rename_config = self._get_rename_config()
            logger.info(f"处理目录 {target_dir}, 文件数: {len(files)}, 文件夹数: {len(folders)}")

            # 处理文件夹
            await self._process_folders(folders, target_folders, target_dir, share_info)

            # 处理文件
            need_save_files = await self._process_files(files, target_files, start_magic, rename_config)

            # 保存文件
            await self._save_files(need_save_files, share_info, target_dir)

            # 重命名已保存的文件
            await self._rename_saved_files(need_save_files, target_dir)

        except Exception as e:
            logger.error(f"处理目录时发生错误: {e}")
            raise

    def _get_rename_config(self) -> Dict[str, Any]:
        """获取重命名配置"""
        # 优先使用新的重命名配置
        rename_style = self.params.get("renameStyle", "simple")
        rename_template = self.params.get("renameTemplate", "")

        # 如果使用自定义模板，优先使用 renameTemplate
        if rename_style == "custom" and rename_template:
            template = rename_template
        elif rename_template:
            template = rename_template
        else:
            # 兼容旧的 replace 参数
            template = self.params.get("replace", "")

        return {
            'custom_title': self.task_name,
            'template': template,
            'style': rename_style,
            'ignore_extension': self.params.get("ignoreExtension", False)
        }

    def _should_save_file(self, filename: str, start_magic: List[str]) -> bool:
        """判断文件是否应该保存"""
        if not start_magic:
            return True

        # 简化的过滤逻辑 - 检查文件名是否包含任何过滤关键词
        for magic in start_magic:
            if isinstance(magic, str) and magic in filename:
                return False
        return True

    def _check_file_exists(self, filename: str, existing_files: List[str], ignore_ext: bool = False) -> bool:
        """检查文件是否已存在"""
        if ignore_ext:
            filename_no_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
            existing_no_ext = [f.rsplit('.', 1)[0] if '.' in f else f for f in existing_files]
            return filename_no_ext in existing_no_ext
        return filename in existing_files

    def _rename_file(self, filename: str, rename_config: Dict[str, Any]) -> str:
        """重命名单个文件"""
        try:
            if rename_config.get('template'):
                # 使用自定义模板
                return self.media_renamer.rename_file(
                    filename=filename,
                    custom_template=rename_config['template'],
                    custom_title=rename_config['custom_title']
                )
            else:
                # 使用默认样式
                return self.media_renamer.rename_file(
                    filename=filename,
                    style=rename_config.get('style', 'simple'),
                    custom_title=rename_config['custom_title']
                )
        except Exception as e:
            logger.warning(f"文件重命名失败 {filename}: {e}")
            return filename

    def _is_video_file(self, filename: str) -> bool:
        """判断是否为视频文件"""
        video_extensions = {'.mp4', '.mkv', '.avi', '.rmvb', '.flv', '.wmv', '.mov', '.m4v', '.ts', '.webm'}
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        return f'.{ext}' in video_extensions

    async def _process_folders(self, folders: List[Dict], target_folders: List[Dict],
                              target_dir: str, share_info: Dict):
        """处理文件夹创建和递归保存"""
        dir_name_list = [dir_file["name"] for dir_file in target_folders]
        search_pattern = self.params.get("search_pattern", "")

        for folder in folders:
            if not search_pattern or re.search(search_pattern, folder["name"]):
                file_id = None

                if folder["name"] not in dir_name_list:
                    # 创建新文件夹
                    res = await self.client.create_folder(folder["name"], target_dir)
                    if res.get("res_code") == 0:
                        file_id = res.get("id")
                        logger.info(f"创建文件夹: {folder['name']} 成功")
                else:
                    # 使用现有文件夹
                    matching_folder = next((f for f in target_folders if f["name"] == folder["name"]), None)
                    if matching_folder:
                        file_id = matching_folder["id"]

                if file_id:
                    logger.info(f"处理文件夹: {folder['name']} (ID: {file_id})")
                    await self.dir_check_and_save(share_info, folder["id"], file_id)

    async def _process_files(self, files: List[Dict], target_files: List[Dict],
                            start_magic: List[str], rename_config: Dict[str, Any]) -> List[Dict]:
        """处理文件保存和重命名"""
        existing_files = [f["name"] for f in target_files]
        need_save_files = []

        for file in files:
            # 检查是否应该保存此文件
            if not self._should_save_file(file["name"], start_magic):
                continue

            # 检查文件是否已存在
            if self._check_file_exists(file["name"], existing_files, rename_config.get('ignore_extension', False)):
                continue

            # 生成重命名后的文件名
            renamed_filename = file["name"]
            if self._is_video_file(file["name"]):
                renamed_filename = self._rename_file(file["name"], rename_config)

            # 检查重命名后的文件是否已存在
            if not self._check_file_exists(renamed_filename, existing_files, rename_config.get('ignore_extension', False)):
                if renamed_filename != file["name"]:
                    file["name_re"] = renamed_filename
                need_save_files.append(file)
                self.need_save_files_global.append(file)

        return need_save_files

    async def _save_files(self, need_save_files: List[Dict], share_info: Dict, target_dir: str):
        """保存文件到目标目录"""
        if not need_save_files:
            return

        file_ids = [{"fileId": file["id"], "fileName": file["name"], "isFolder": False}
                   for file in need_save_files]

        logger.info(f"准备保存 {len(file_ids)} 个文件")
        await self.client.save_share_files(shareInfo=share_info, file_ids=file_ids, target_folder_id=target_dir)

    async def _rename_saved_files(self, need_save_files: List[Dict], target_dir: str):
        """重命名已保存的文件"""
        # 获取目标目录中的文件列表
        target_response = await self.client.list_files(target_dir)
        saved_files = target_response.get("fileListAO", {}).get("fileList", [])

        for saved_file in saved_files:
            # 找到对应的原始文件信息
            original_file = next((f for f in need_save_files if f["name"] == saved_file["name"]), None)

            if original_file and "name_re" in original_file and original_file["name"] != original_file["name_re"]:
                try:
                    await self.client.rename_file(saved_file["id"], original_file["name_re"])
                    logger.info(f"文件重命名成功: {original_file['name']} -> {original_file['name_re']}")
                except Exception as e:
                    logger.error(f"文件重命名失败: {original_file['name']} -> {original_file['name_re']}: {e}")


    def _disable_task_on_error(self, task: Dict[str, Any], error_msg: str):
        """在出错时禁用任务"""
        updated_task = task.copy()
        updated_task['enabled'] = False
        updated_task["params"] = task.get("params", {}).copy()
        updated_task["params"]["isShareUrlValid"] = False
        scheduled_manager.scheduled_manager.update_task(self.task_name, updated_task)
        logger.error(error_msg)

    def _format_file_list_output(self) -> str:
        """格式化文件列表输出"""
        if not self.need_save_files_global:
            return "没有需要保存的文件"

        file_list = []
        for file in self.need_save_files_global:
            file_info = f"🎬 {file['name']}"
            if file.get('name_re'):
                file_info += f"\n   ↳ 将重命名为: {file['name_re']}"
            file_list.append(file_info)

        return f"保存的文件:\n" + "\n".join(file_list)

    async def cloud189_auto_save(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        天翼云盘自动保存任务主方法

        Args:
            task: 任务配置字典，包含以下参数:
                - shareUrl: 分享链接
                - targetDir: 目标文件夹ID，默认为-11
                - sourceDir: 源文件夹ID（可选）
                - replace: 重命名模板（可选）
                - startMagic: 过滤条件（可选）
                - ignore_extension: 是否忽略扩展名（可选）

        Returns:
            任务执行结果字典或None
        """
        try:
            # 初始化任务参数
            self.task = task
            self.params = task.get("params", {})
            self.task_name = task.get("name", "")
            self.need_save_files_global = []

            logger_service.info_sync(f"天翼云盘自动转存任务开始 🏃‍➡️: {self.task_name}")

            # 发送任务开始通知
            await notification_manager.notify_task_start(self.task_name, "天翼云盘自动转存")

            # 验证必要参数
            share_url = self.params.get("shareUrl")
            target_dir = self.params.get("targetDir", "-11")

            if not share_url:
                logger.error("缺少必要参数: shareUrl")
                return None

            if not target_dir:
                logger.error("缺少必要参数: targetDir")
                return None

            # 验证账号登录
            if not await self.client.login():
                logger.error("天翼云盘登录失败")
                return None

            # 解析分享链接
            logger.info(f"解析分享链接: {share_url}")
            url, _ = self.client.parse_cloud_share(share_url)
            if not url:
                self._disable_task_on_error(task, "无效的分享链接")
                return None

            # 获取分享码和分享信息
            share_code = self.client.parse_share_code(url)
            try:
                share_info = await self.client.get_share_info(share_code)
                if share_info.get("res_code") != 0:
                    self._disable_task_on_error(task, "获取分享信息失败")
                    return None
            except Exception as e:
                self._disable_task_on_error(task, f"获取分享信息失败: {e}")
                return None

            # 执行文件保存和重命名
            await self.dir_check_and_save(share_info, self.params.get("sourceDir", ""))

            # 输出执行结果
            result_msg = self._format_file_list_output()
            logger_service.info_sync(f"天翼云盘自动转存任务 {self.task_name} - {result_msg}")
            logger_service.info_sync(f"天翼云盘自动转存任务结束 🏁: {self.task_name}")

            # 准备返回结果
            result = {
                "task_name": self.task_name,
                "task": self.task.get("task", ""),
                "need_save_files": [
                    {
                        "file_name": file["name"],
                        "file_name_re": file.get("name_re")
                    }
                    for file in self.need_save_files_global
                ]
            }

            # 发送任务完成通知
            await notification_manager.notify_task_complete(
                self.task_name,
                "天翼云盘自动转存",
                0.0,  # 这里可以添加实际的执行时间计算
                result
            )

            # 如果有重命名的文件，发送重命名成功通知
            if self.need_save_files_global:
                await notification_manager.notify_rename_success(
                    self.task_name,
                    result["need_save_files"]
                )

            return result

        except Exception as e:
            error_msg = str(e)
            logger_service.error_sync(f"天翼云盘自动转存任务异常 🚨: {self.task_name} - {error_msg}")

            # 发送任务错误通知
            await notification_manager.notify_task_error(
                self.task_name,
                "天翼云盘自动转存",
                error_msg
            )

            return None


