import { requestClient } from '#/api/request';

/**
 * 获取定时任务列表
 */
export async function getCornTaskListApi() {
  return requestClient.get('/scheduled/tasks', {});
}

/**
 * 启用定时任务
 */
export async function enableCornTaskApi(taskName: string) {
  return requestClient.post(`/scheduled/tasks/${taskName}/enable`, {});
}

/**
 * 禁用定时任务
 */
export async function disableCornTaskApi(taskName: string) {
  return requestClient.post(`/scheduled/tasks/${taskName}/disable`, {});
}

/**
 * 删除定时任务
 */
export async function deleteCornTaskApi(taskName: string) {
  return requestClient.delete(`/scheduled/tasks/${taskName}`, {});
}

/**
 * 获取定时任务类型
 */
export async function getCornTaskTypeListApi() {
  return requestClient.get('/scheduled/task-types', {});
}

/**
 * 创建定时任务
 */
export async function createCornTaskApi(params: any) {
  return requestClient.post('/scheduled/tasks', params);
}

/**
 * 更新定时任务
 */
export async function updateCornTaskApi(params: any) {
  return requestClient.put(`/scheduled/tasks/${params.name}`, params);
}

/**
 * 立即执行定时任务
 */
export async function runCornTaskApi(taskName: string) {
  return requestClient.post(`/scheduled/execute/${taskName}`, {});
}

/**
 * 获取日期模块
 */
export async function getModuleLogListApi() {
  return requestClient.get('/logs/modules', {});
}

/**
 * 获取日志列表
 */
export async function getLogListApi(params: any) {
  return requestClient.get('/logs/list', {
    params: {
      ...params,
      page: 1,
      pageSize: 50,
    },
  });
}

/**
 * 获取重命名模板列表
 */
export async function getRenameTemplatesApi() {
  return requestClient.get('/smart-rename/templates', {});
}

/**
 * 获取模板变量列表
 */
export async function getTemplateVariablesApi() {
  return requestClient.get('/smart-rename/templates/variables', {});
}
