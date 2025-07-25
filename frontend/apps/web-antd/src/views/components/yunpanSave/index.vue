<script setup lang="ts">
import type { PropType } from 'vue';

import { computed, onMounted, onUnmounted, ref, watch } from 'vue';

import { Button, message, Modal } from 'ant-design-vue';

import FolderSelect from '../FolderSelect/index.vue';
import {
  createCloud189FolderApi,
  deleteCloud189FileApi,
  getCloud189FileListApi,
  getCloud189ShareFileListApi,
  renameCloud189FileApi,
  saveCloud189FileApi,
} from './api';

const props = defineProps({
  item: {
    type: Object as PropType<any>,
    default: () => ({}),
  },
});
const shareUrl = computed(() => {
  return props.item?.cloudLinks?.[0] || '';
});
const fileList = ref<any[]>([]);
const selectedFile = ref<any[]>([]);
const paths = ref<any[]>([]);
const fileList2 = ref<any[]>([]);
const paths2 = ref<any[]>([]);
const open = defineModel<boolean>('open', {
  default: false,
  type: Boolean,
});
const loading = defineModel<boolean>('loading', {
  default: false,
  type: Boolean,
});
const saveOperation = ['分享文件', '保存到'];
const currentStep = ref<number>(0);
const okText = computed(() => {
  return currentStep.value === 0 ? '保存到' : '保存';
});
const modalTitle = computed(() => {
  return saveOperation[currentStep.value];
});

const width = ref('800px');

const updateWidth = () => {
  const w = window.innerWidth;
  if (w < 640) {
    width.value = '90vw';
  } else if (w < 768) {
    width.value = '800px';
  } else if (w < 1024) {
    width.value = '1000px';
  } else if (w < 1280) {
    width.value = '1000px';
  } else {
    width.value = '1000px';
  }
};

onMounted(() => {
  updateWidth();
  window.addEventListener('resize', updateWidth);
});

onUnmounted(() => {
  window.removeEventListener('resize', updateWidth);
});


let filePaths: any[] = [];
const selfSavePaths = (dir: any, filePaths: any[]) => {
  if (dir.fid) {
    const index = filePaths.findIndex((item) => item.fid === dir.fid);
    if (index === -1) {
      filePaths.push(dir);
    } else {
      filePaths = filePaths.slice(0, index + 1);
    }
  } else {
    filePaths = [];
  }
};
const getShareFileList = async (dir: any = {}) => {
  if (props.item?.cloudType === 'tianyiyun') {
    loading.value = true;
    const res = await getCloud189ShareFileListApi({
      share_url: shareUrl.value,
      file_id: dir.fid,
    }).finally(() => {
      loading.value = false;
    });
    const { fileListAO } = res;
    fileList.value = [
      ...(fileListAO?.folderList ?? []).map((item: any) => ({
        ...item,
        file_name: item.name,
        fid: item.id,
        dir: true,
      })),
      ...(fileListAO?.fileList ?? []).map((item: any) => ({
        ...item,
        file_name: item.name,
        fid: item.id,
        file: true,
      })),
    ];
    if (dir.fid) {
      // 如果当前目录有fid，则将当前目录添加到filepaths中
      const index = filePaths.findIndex((item) => item.fid === dir.fid);
      if (index === -1) {
        filePaths.push(dir);
      } else {
        filePaths = filePaths.slice(0, index + 1);
      }
    } else {
      filePaths = [];
    }
    selfSavePaths(dir, filePaths);
    paths.value = [...filePaths];
  }
};
const filepaths2: any[] = [];
const getFileList = async (dir: any = {}) => {
  if (props.item?.cloudType === 'tianyiyun') {
    loading.value = true;
    const res = await getCloud189FileListApi({
      folder_id: dir.fid === undefined ? '-11' : String(dir.fid),
    }).finally(() => {
      loading.value = false;
    });
    const { fileListAO } = res;
    fileList2.value = [
      ...(fileListAO?.folderList ?? []).map((item: any) => ({
        ...item,
        file_name: item.name,
        fid: item.id,
        dir: true,
      })),
      ...(fileListAO?.fileList ?? []).map((item: any) => ({
        ...item,
        file_name: item.name,
        fid: item.id,
        file: true,
      })),
    ];
    if (dir.fid) {
      // 如果当前目录有fid，则将当前目录添加到filepaths中
      const index = filePaths.findIndex((item) => item.fid === dir.fid);
      if (index === -1) {
        filePaths.push(dir);
      } else {
        filePaths = filePaths.slice(0, index + 1);
      }
    } else {
      filePaths = [];
    }
    selfSavePaths(dir, filePaths);
    paths2.value = [...filePaths];
  }
};

const saveShareFile = async () => {
  if (props.item?.cloudType === 'tianyiyun') {
    const target_folder_id =
      paths2.value[paths2.value.length - 1]?.fid ?? '-11';
    const file_ids =
      selectedFile.value.length > 0
        ? selectedFile.value.map((item) => ({
            fileId: item.fid,
            fileName: item.file_name,
            isFolder: item.dir,
          }))
        : fileList.value.map((item) => ({
            fileId: item.fid,
            fileName: item.file_name,
            isFolder: item.dir,
          }));
    return await saveCloud189FileApi({
      share_url: shareUrl.value,
      target_folder_id,
      file_ids,
    });
  }
};

watch(open, (value) => {
  if (value) {
    fileList.value = [];
    fileList2.value = [];
    paths.value = [];
    paths2.value = [];
    selectedFile.value = [];
    currentStep.value = 0;
    getShareFileList();
  }
});

const navigateTo = (dir: any) => {
  if (currentStep.value === 0) {
    getShareFileList(dir);
  } else {
    getFileList(dir);
  }
};

const onOk = async () => {
  if (currentStep.value === 0) {
    // 下一步
    currentStep.value = 1;
    if (fileList2.value.length === 0) {
      getFileList();
    }
  } else {
    // 保存
    await saveShareFile();
    open.value = false;
    message.success('保存成功');
  }
};

const onBack = () => {
  currentStep.value = 0;
};

const createDir = async (fileName: any) => {
  if (!fileName) {
    message.error('请输入文件夹名称');
    return;
  }
  if (props.item?.cloudType === 'tianyiyun') {
    loading.value = true;
    await createCloud189FolderApi({
      folder_name: fileName,
      parent_id: paths2.value[paths2.value.length - 1]?.fid ?? '-11',
    })
      .finally(() => {
        loading.value = false;
      })
      .then(() => {
        getFileList({
          fid: paths2.value[paths2.value.length - 1]?.fid ?? '-11',
        });
      });
  }
};

const rename = async (_file: any) => {
  if (props.item?.cloudType === 'tianyiyun') {
    loading.value = true;
    await renameCloud189FileApi({
      file_id: _file.fid,
      new_name: _file.file_name,
    })
      .finally(() => {
        loading.value = false;
      })
      .then(() => {
        getFileList({
          fid: paths2.value[paths2.value.length - 1]?.fid ?? '-11',
        });
      });
  }
};

const deleteFile = async (_file: any) => {
  if (props.item?.cloudType === 'tianyiyun') {
    loading.value = true;
    await deleteCloud189FileApi({
      file_ids: [
        {
          fileId: _file.fid,
          fileName: _file.file_name,
          isFolder: _file.dir ? 1 : 0,
        },
      ],
    })
      .finally(() => {
        loading.value = false;
      })
      .then(() => {
        getFileList({
          fid: paths2.value[paths2.value.length - 1]?.fid ?? '-11',
        });
      });
  }
};
</script>

<template>
  <Modal
    v-model:open="open"
    :title="modalTitle"
    :width="width"
    destroy-on-close
  >
    <div v-loading="loading" v-show="currentStep === 0">
      <FolderSelect
        v-model:selected-file="selectedFile"
        :file-list="fileList"
        :paths="paths"
        @navigate-to="navigateTo"
      />
    </div>
    <div v-loading="loading" v-show="currentStep === 1">
      <FolderSelect
        :if-use-checkbox="false"
        :file-list="fileList2"
        :paths="paths2"
        :if-use-file-manager="true"
        @navigate-to="navigateTo"
        @create-dir="createDir"
        @rename="rename"
        @delete="deleteFile"
      />
    </div>
    <template #footer>
      <Button @click="onBack" v-show="currentStep === 1"> 返回 </Button>
      <Button type="primary" @click="onOk">{{ okText }}</Button>
    </template>
  </Modal>
</template>
