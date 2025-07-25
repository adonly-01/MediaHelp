<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue';

import { message, Modal } from 'ant-design-vue';

import FolderSelect from '#/views/components/FolderSelect/index.vue';
import {
  createCloud189FolderApi,
  deleteCloud189FileApi,
  getCloud189FileListApi,
  getCloud189ShareFileListApi,
  renameCloud189FileApi,
} from '#/views/components/yunpanSave/api';

const props = defineProps({
  cloudType: {
    default: '',
    type: String,
  },
  url: {
    default: '',
    type: String,
  },
});
const emit = defineEmits([
  'okShareTianyiyun',
  'okSelfTianyiyun',
]);

const open = defineModel<boolean>('open', { required: true });
const width = ref('');
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

watch(open, (value) => {
  if (value) {
    fileList.value = [];
    paths.value = [];

    loading.value = false;
    filePaths = [];
    lastShareUrl = undefined;
    if (props.url) {
      getShareFileList();
    } else {
      getFileList();
    }
  }
});

const fileList = ref<any[]>([]);
const paths = ref<any[]>([]);
const loading = ref(false);

const navigateTo = (dir: any) => {
  if (props.url) {
    getShareFileList(dir);
  } else {
    getFileList(dir);
  }
};
const onOk = () => {
  if (props.url) {
    if (props.cloudType === 'tianyiyun') {
      emit('okShareTianyiyun', paths.value[paths.value.length - 1]?.fid ?? '');
    }
  } else {
    if (props.cloudType === 'tianyiyun') {
      emit(
        'okSelfTianyiyun',
        paths.value[paths.value.length - 1]?.fid ?? '-11',
      );
    }
  }
  open.value = false;
};


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
  if (props.cloudType === 'tianyiyun') {
    loading.value = true;
    const res = await getCloud189ShareFileListApi({
      share_url: props.url,
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
const getFileList = async (dir: any = {}) => {
  if (props.cloudType === 'tianyiyun') {
    loading.value = true;
    const res = await getCloud189FileListApi({
      folder_id: dir.fid === undefined ? '-11' : String(dir.fid),
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
const createDir = async (fileName: any) => {
  if (!fileName) {
    message.error('请输入文件夹名称');
    return;
  }
  if (props.cloudType === 'tianyiyun') {
    loading.value = true;
    await createCloud189FolderApi({
      folder_name: fileName,
      parent_id: paths.value[paths.value.length - 1]?.fid ?? '-11',
    })
      .finally(() => {
        loading.value = false;
      })
      .then(() => {
        getFileList({
          fid: paths.value[paths.value.length - 1]?.fid ?? '-11',
        });
      });
  }
};

const rename = async (_file: any) => {
  if (props.cloudType === 'tianyiyun') {
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
          fid: paths.value[paths.value.length - 1]?.fid ?? '-11',
        });
      });
  }
};

const deleteFile = async (_file: any) => {
  if (props.cloudType === 'tianyiyun') {
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
          fid: paths.value[paths.value.length - 1]?.fid ?? '-11',
        });
      });
  }
};
onMounted(() => {
  updateWidth();
  window.addEventListener('resize', updateWidth);
});

onUnmounted(() => {
  window.removeEventListener('resize', updateWidth);
});
</script>
<template>
  <Modal
    v-model:open="open"
    title="选择目录"
    :width="width"
    @ok="onOk"
    ok-text="选择当前文件夹"
  >
    <div class="m-4" v-loading="loading">
      <FolderSelect
        :file-list="fileList"
        :paths="paths"
        :if-use-checkbox="false"
        :if-use-file-manager="url ? false : true"
        @navigate-to="navigateTo"
        @create-dir="createDir"
        @rename="rename"
        @delete="deleteFile"
      />
    </div>
  </Modal>
</template>
