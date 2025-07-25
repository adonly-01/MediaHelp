# 天翼云盘自动保存任务
import re
from typing import Any, Dict
from loguru import logger
from utils import config_manager, logger_service, scheduled_manager
from utils.cloud189.client import Cloud189Client
from utils.smart_rename import SmartRenameEngine

class Cloud189AutoSave:
    client = {}
    params = {}
    task = {}
    task_name = ""
    need_save_files_global = []
    def __init__(self):
      # 创建客户端实例，它会自动从配置文件加载session
      sys_config = config_manager.config_manager.get_config()
      username = sys_config.get("tianyiAccount", "")
      password = sys_config.get("tianyiPassword", "")
      sson_cookie = sys_config.get("tianyiCookie", "")

      logger.info(f"username: {username} password: {password} sson_cookie: {sson_cookie}")

      if (not username or not password) and not sson_cookie:
        logger.error("未配置天翼云盘账号，请在系统配置中添加 tianyiAccount 和 tianyiPassword 或 tianyiCookie")
        return
  
      self.client = Cloud189Client(
          username=username,
          password=password,
          sson_cookie=sson_cookie
      )
      
    async def dir_check_and_save(self, share_info, file_id = '', target_file_id = ''):
      target_dir = target_file_id or self.params.get("targetDir", "-11")
      start_magic = self.params.get("startMagic", [])
      if not isinstance(start_magic, list):
        start_magic = [start_magic] if start_magic else []
      # 获取分享文件列表
      filesResponse = await self.client.list_share_files(
        share_id=share_info["shareId"],
        file_id= file_id if file_id else share_info["fileId"],
        share_mode=share_info.get("shareMode", "1"),
        access_code=share_info.get("accessCode", ""),
        is_folder=share_info.get("isFolder", "")
      )
        
      files = filesResponse.get("fileListAO", {}).get("fileList", [])
      folders = filesResponse.get("fileListAO", {}).get("folderList", [])
      
      #获取目标文件列表
      target_response = await self.client.list_files(target_dir)
      target_files = target_response.get("fileListAO", {}).get("fileList", [])
      target_folders = target_response.get("fileListAO", {}).get("folderList", [])
      
      
      # 文件判重
      smart_patterns = scheduled_manager.scheduled_manager.get_config().get("smart_rename_patterns", {})
      rename_engine = SmartRenameEngine(smart_patterns)
      rename_engine.set_task_name(self.task_name)
      
      # 智能正则转换
      pattern, replace = rename_engine.apply_text_pattern(
          self.params.get("pattern", ""), self.params.get("replace", "")
      )
      logger.info(f"pattern: {pattern}")
      logger.info(f"replace: {replace}")
      # 文件夹对比 创建文件夹
      dir_name_list = [dir_file["name"] for dir_file in target_folders]
      for folder in folders:
        search_pattern = (
            self.params.get("search_pattern", "")
        )
        if re.search(search_pattern, folder["name"]):
          if folder["name"] not in dir_name_list:
            res = await self.client.create_folder(folder["name"], target_dir)
            if res.get("res_code") == 0:
              file_id = res.get("id")
              logger.info(f"创建文件夹: {folder['name']} 成功")
          else:
            # 使用列表推导式找到匹配的文件夹
            matching_folder = next((f for f in target_folders if f["name"] == folder["name"]), None)
            if matching_folder:
              file_id = matching_folder["id"]
          logger.info(f"文件夹ID: {file_id}")
          await self.dir_check_and_save(share_info, folder["id"], file_id)
      # 文件
      dir_name_list = [dir_file["name"] for dir_file in target_files]
      need_save_files = []
      for file in files:
        # 正则文件名匹配  选择那些需要保存的文件
        should_save = True
        if start_magic:
            should_save = rename_engine.check_filter_conditions(start_magic, file["name"])
        if (not rename_engine.check_file_exists(
                    file["name"],
                    dir_name_list,
                    (self.params.get("ignore_extension")),
                ) and should_save):
          # 替换后的文件名
          file_name_re = rename_engine.transform_filename(pattern, replace, file["name"])
          # 判断替换后的文件名是否存在
          if not rename_engine.check_file_exists(
              file_name_re,
              dir_name_list,
              self.params.get("ignore_extension"),
          ):
              # 视频文件才进行重命名
              if re.search(r'\.(mp4|mkv|avi|rmvb|flv|wmv|mov|m4v)$', file["name"].lower()):
                  file["name_re"] = file_name_re
              need_save_files.append(file)
              self.need_save_files_global.append(file)
              
      #保存文件
      file_ids = [{"fileId": file["id"], "fileName": file["name"], "isFolder": False} for file in need_save_files]
      if file_ids:
        await self.client.save_share_files(shareInfo=share_info, file_ids=file_ids, target_folder_id=target_dir)
      
      #重命名文件
      need_rename_files = await self.client.list_files(target_dir)
      need_rename_files = need_rename_files.get("fileListAO", {}).get("fileList", [])
      for file in need_rename_files:
        before_file = next((f for f in need_save_files if f["name"] == file["name"]), None)
        if (before_file and "name_re" in before_file) and before_file['name']!=before_file['name_re']:
          rename_response = await self.client.rename_file(file["id"], before_file["name_re"])
          logger.info(f"重命名文件 {file['name']} 为 {before_file['name_re']}: {rename_response}")


    async def cloud189_auto_save(self, task: Dict[str, Any]):
        """天翼云盘自动保存任务
        参数:
        1. shareUrl: 分享链接
        2. targetDir: 目标文件夹ID，默认为-11
        3. others: 其他参数
        """
        try:  
          self.task = task
          self.params = task.get("params", {})
          self.task_name = task.get("name", "")
          logger_service.info_sync(f"天翼云盘自动转存任务 开始🏃‍➡️: {self.task_name} ({self.task.get('task', '')})")
          target_dir = self.params.get("targetDir", "-11")
          share_url = self.params.get("shareUrl")
          if not share_url:
              logger.error("缺少必要参数: shareUrl")
              return

          if not target_dir:
              logger.error("缺少必要参数: targetDir")
              return
          # 验证账号登录
          if not await self.client.login():
              logger.error("天翼云盘登录失败")
              return
          # TODO: 后续的转存逻辑
          # 获取分享信息
          # 解析分享链接
          logger.info(f"解析分享链接: {share_url}")
          url, _ = self.client.parse_cloud_share(share_url)
          if not url:
              # 创建新的任务对象进行更新
              updated_task = task.copy()
              updated_task['enabled'] = False
              updated_task["params"] = task.get("params", {}).copy()
              updated_task["params"]["isShareUrlValid"] = False
              scheduled_manager.scheduled_manager.update_task(self.task_name, updated_task)
              logger.error("无效的分享链接")
              return
          # 获取分享码
          share_code = self.client.parse_share_code(url)

          # 获取分享信息
          try:
            share_info = await self.client.get_share_info(share_code)
            if share_info.get("res_code") != 0:
              # 创建新的任务对象进行更新
              updated_task = task.copy()  
              updated_task['enabled'] = False
              updated_task["params"] = task.get("params", {}).copy()
              updated_task["params"]["isShareUrlValid"] = False
              scheduled_manager.scheduled_manager.update_task(self.task_name, updated_task)
              logger.error("获取分享信息失败")
              return
          except Exception as e:
            # 创建新的任务对象进行更新
            updated_task = task.copy()
            updated_task['enabled'] = False
            updated_task["params"] = task.get("params", {}).copy()
            updated_task["params"]["isShareUrlValid"] = False
            scheduled_manager.scheduled_manager.update_task(self.task_name, updated_task)
            logger.error(f"获取分享信息失败: {e}")
            return
          self.need_save_files_global = []
          await self.dir_check_and_save(share_info, self.params.get("sourceDir", ""))
          # 格式化打印需要保存的文件列表
          if self.need_save_files_global:
            file_list_str = "\n".join([f"🎬 {file['name']}" + (f"\n   ↳ 将重命名为: {file['name_re']}" if file.get('name_re') else "") for file in self.need_save_files_global])
            logger_service.info_sync(f"天翼云盘自动转存任务 {self.task_name} ({self.task.get('task', '')}) 保存的文件:\n{file_list_str}")
          else:
            logger_service.info_sync(f"天翼云盘自动转存任务 {self.task_name} ({self.task.get('task', '')}) 没有需要保存的文件")
          logger_service.info_sync(f"天翼云盘自动转存任务 结束🏁: {self.task_name} ({self.task.get('task', '')})")
          return {
            "task_name": f'{self.task_name}',
            "task": self.task.get("task", ""),
            "need_save_files": [{"file_name": file["name"], "file_name_re": file.get("name_re")} for file in self.need_save_files_global]
          }
        except Exception as e:
          logger_service.error_sync(f"天翼云盘自动转存任务 异常🚨: {self.task_name} ({self.task.get('task', '')}) {e}")


