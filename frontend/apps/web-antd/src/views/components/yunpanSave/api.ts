import { requestClient } from '#/api/request';



/**
 * 189 获取文件列表
 */
export const getCloud189FileListApi = (data: any) => {
  return requestClient.post('/cloud189/files', data);
};

/**
 * 189 获取分享文件列表
 */
export const getCloud189ShareFileListApi = (data: any) => {
  return requestClient.post('/cloud189/share/files', data);
};

/**
 * 189 保存文件
 */
export const saveCloud189FileApi = (data: any) => {
  return requestClient.post('/cloud189/share/save', data);
};

/**
 * 189 重命名文件
 */
export const createCloud189FolderApi = (data: any) => {
  return requestClient.post('/cloud189/folder', data);
};

/**
 * 189 重命名文件
 */
export const renameCloud189FileApi = (data: any) => {
  return requestClient.post('/cloud189/rename', data);
};

/**
 * 189 删除文件
 */
export const deleteCloud189FileApi = (data: any) => {
  return requestClient.post('/cloud189/delete', data);
};
