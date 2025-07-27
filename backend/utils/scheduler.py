import asyncio
from datetime import datetime
from typing import Dict, Any, Callable, Optional, List
from loguru import logger
import re
from task import cloud189_auto_save
from utils.emby_manager import emby_manager
from utils.notification_service import notification_manager
from utils.scheduled_manager import scheduled_manager

class TaskResult:
    """任务执行结果类"""
    def __init__(self, success: bool, message: str, execution_time: datetime, is_manual: bool):
        self.success = success
        self.message = message
        self.execution_time = execution_time
        self.is_manual = is_manual

class TaskScheduler:
    _instance = None
    _running = False
    _task_handlers: Dict[str, Callable] = {}
    _last_run_times: Dict[str, datetime] = {}  # 记录每个任务的上次执行时间
    _running_tasks: Dict[str, asyncio.Task] = {}  # 记录正在运行的任务
    _task_results: Dict[str, TaskResult] = {}  # 记录任务执行结果

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskScheduler, cls).__new__(cls)
        return cls._instance

    def register_task_handler(self, task_type: str, handler: Callable):
        """注册任务处理器"""
        self._task_handlers[task_type] = handler

    def register_system_tasks(self):
        """注册系统默认的任务处理器"""
        self.register_task_handler("cloud189_auto_save", cloud189_auto_save.Cloud189AutoSave().cloud189_auto_save)
        logger.info("系统任务注册完成")

    def _record_task_result(self, task_name: str, success: bool, message: str, is_manual: bool):
        """记录任务执行结果"""
        self._task_results[task_name] = TaskResult(
            success=success,
            message=message,
            execution_time=datetime.now(),
            is_manual=is_manual
        )

    def get_task_result(self, task_name: str) -> Optional[Dict[str, Any]]:
        """获取任务执行结果"""
        result = self._task_results.get(task_name)
        if result:
            return {
                "success": result.success,
                "message": result.message,
                "execution_time": result.execution_time.isoformat(),
                "is_manual": result.is_manual
            }
        return None

    async def _execute_task(self, task: Dict[str, Any], is_manual: bool = False):
        """执行任务"""
        task_name = task.get("name", "unknown")
        try:
            task_type = task.get("task")
            if not task_type:
                logger.error(f"任务类型未指定: {task_name}")
                self._record_task_result(task_name, False, "任务类型未指定", is_manual)
                return

            # 获取任务处理器
            handler = self._task_handlers.get(task_type)
            if not handler:
                logger.error(f"未找到任务处理器: {task_type}")
                self._record_task_result(task_name, False, "未找到任务处理器", is_manual)
                return

            # 检查任务是否已在运行
            if task_name in self._running_tasks and not self._running_tasks[task_name].done():
                if is_manual:
                    logger.warning(f"任务正在运行中，将终止当前执行并重新启动: {task_name}")
                    self._running_tasks[task_name].cancel()
                    try:
                        await self._running_tasks[task_name]
                    except asyncio.CancelledError:
                        pass
                else:
                    logger.warning(f"任务正在运行中，跳过本次执行: {task_name}")
                    self._record_task_result(task_name, False, "任务正在运行中，跳过本次执行", is_manual)
                    return

            # 执行任务，传递完整的任务信息
            execution_type = "手动" if is_manual else "自动"
            logger.info(f"开始{execution_type}执行任务: {task_name}")
            
            # 创建任务并保存引用
            task_coroutine = handler(task)
            task_obj = asyncio.create_task(task_coroutine)
            self._running_tasks[task_name] = task_obj
            
            # 等待任务完成并获取结果
            task_result = await task_obj
            
            # 更新上次执行时间（仅对自动执行有效）
            if not is_manual:
                self._last_run_times[task_name] = datetime.now()
                
            
            # 处理任务返回的结果
            if isinstance(task_result, dict):
                # 如果任务返回了结果，记录到任务结果中
                success = task_result.get('success', True)
                message = task_result.get('message', f"任务{execution_type}执行完成")
                self._record_task_result(task_name, success, message, is_manual)
            # 返回任务结果供其他地方使用
                return task_result
            else:
                logger.info(f"任务{execution_type}执行完成: {task_name}")
                self._record_task_result(task_name, True, f"任务{execution_type}执行完成", is_manual)
                return None

        except asyncio.CancelledError:
            logger.info(f"任务已取消: {task_name}")
            self._record_task_result(task_name, False, "任务已取消", is_manual)
        except Exception as e:
            error_message = f"任务执行失败: {str(e)}"
            logger.error(f"{error_message}")
            self._record_task_result(task_name, False, error_message, is_manual)
        finally:
            # 清理任务引用
            if task_name in self._running_tasks:
                del self._running_tasks[task_name]

    async def _check_and_execute_tasks(self):
        """检查并执行到期的任务"""
        # 缓存每个任务的next_run时间，避免每次都重新计算
        task_next_runs = {}
        
        while self._running:
            try:
                # 获取所有启用的任务
                enabled_tasks = scheduled_manager.get_enabled_tasks()
                current_time = datetime.now()
                task_run_result = []

                for task in enabled_tasks:
                    task_name = task.get("name")
                    if not task_name:
                        continue

                    # 获取或缓存任务的下次执行时间
                    if task_name not in task_next_runs:
                        next_run = scheduled_manager.get_next_run_time(task)
                        if next_run:
                            task_next_runs[task_name] = next_run
                        else:
                            continue
                    else:
                        next_run = task_next_runs[task_name]

                    # 检查是否需要执行
                    last_run = self._last_run_times.get(task_name)
                    # logger.info(f"last_run: {last_run}, next_run: {next_run}, current_time: {current_time} flag:{(next_run <= current_time and last_run < next_run)}")
                    if not last_run or (next_run <= current_time and last_run < next_run):
                        # 执行任务并获取结果
                        result = await self._execute_task(task)
                        if result:
                            task_run_result.append(result)
                        
                        # 任务执行后，重新计算下次运行时间
                        new_next_run = scheduled_manager.get_next_run_time(task)
                        if new_next_run:
                            task_next_runs[task_name] = new_next_run

                # 打印任务执行结果
                logger.info(f"任务执行结果: {task_run_result} {task_next_runs}")
                if task_run_result:
                    await self.task_done_notify_refresh_emby(task_run_result)
                # 清理已删除任务的执行记录
                task_names = {task.get("name") for task in enabled_tasks}
                removed_tasks = set(self._last_run_times.keys()) - task_names
                for task_name in removed_tasks:
                    self._last_run_times.pop(task_name, None)
                    task_next_runs.pop(task_name, None)  # 同时清理缓存

                # 每分钟检查一次
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"任务检查失败: {str(e)}")
                await asyncio.sleep(60)  # 发生错误时等待一分钟后继续

    async def start(self):
        """启动调度器"""
        if self._running:
            return

        # 注册系统任务
        self.register_system_tasks()
        
        self._running = True
        logger.info("定时任务调度器已启动")
        await self._check_and_execute_tasks()

    async def stop(self):
        """停止调度器"""
        self._running = False
        
        # 取消所有正在运行的任务
        for task_name, task in self._running_tasks.items():
            if not task.done():
                logger.info(f"正在取消任务: {task_name}")
                task.cancel()
        
        # 等待所有任务完成
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
        
        logger.info("定时任务调度器已停止")

    async def execute_task_now(self, task_name: str) -> bool:
        """立即执行指定任务"""
        try:
            # 获取任务配置
            task = scheduled_manager.get_task_by_name(task_name)
            if not task:
                logger.error(f"未找到任务: {task_name}")
                return False

            # 检查任务是否启用
            if not task.get("enabled", False):
                logger.warning(f"任务未启用: {task_name}")
                return False

            # 立即执行任务
            result = await self._execute_task(task, is_manual=True)
            if result:
                await self.task_done_notify_refresh_emby([result])
            return True

        except Exception as e:
            logger.error(f"立即执行任务失败: {task_name} - {str(e)}")
            return False

    async def cancel_task(self, task_name: str) -> bool:
        """取消正在运行的任务"""
        try:
            if task_name in self._running_tasks and not self._running_tasks[task_name].done():
                self._running_tasks[task_name].cancel()
                try:
                    await self._running_tasks[task_name]
                except asyncio.CancelledError:
                    pass
                logger.info(f"已取消任务: {task_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"取消任务失败: {task_name} - {str(e)}")
            return False

    def get_running_tasks(self) -> List[str]:
        """获取正在运行的任务列表"""
        return [
            task_name for task_name, task in self._running_tasks.items()
            if not task.done()
        ]

    async def task_done_notify_refresh_emby(self, task_run_result: List[Dict[str, Any]]):
        message = ""
        need_flush_emby = []
        # 安全处理任务结果
        for result in task_run_result:
            if not isinstance(result, dict):
                continue
                
            need_save_files = result.get("need_save_files", [])
            if not need_save_files:
                continue
            task_name = result.get("task_name", "")
            task_type = result.get("task", "未知任务")
            file_list = []
            
            for file_info in need_save_files:
                if not isinstance(file_info, dict):
                    continue
                    
                file_name = file_info.get("file_name", "")
                file_name_re = file_info.get("file_name_re", "")
                
                if file_name_re:
                    file_list.append(f"🎬 {file_name}\n   ↳ 将重命名为: {file_name_re}")
                else:
                    file_list.append(f"🎬 {file_name}")
            if file_list:
                file_list_str = "\n".join(file_list)+"\n\n"
                message += f"任务执行结果: {task_name}{task_type} 执行成功\n保存的文件:\n{file_list_str}"
                need_flush_emby.append(task_name)
        if message:
            if await emby_manager.isEmbyManagerEnable():
                flag = []
                for task_name in need_flush_emby:
                    flag.append(await emby_manager.searchAndRefreshItem(task_name))
            if all(flag):
                 message += "\n🔄 EMBY刷新媒体库成功"
            notification_manager.send(title='📺MediaHelper 任务执行结果:', content=message)
# 创建全局实例
task_scheduler = TaskScheduler() 