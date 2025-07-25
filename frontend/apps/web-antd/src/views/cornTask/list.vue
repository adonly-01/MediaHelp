<script setup lang="ts">
import type { VxeGridProps } from '#/adapter/vxe-table';

import { onActivated, onMounted, ref } from 'vue';

import { cloneDeep } from '@vben/utils';

import { Button, message, Switch } from 'ant-design-vue';
import dayjs from 'dayjs';

import { useVbenVxeGrid } from '#/adapter/vxe-table';

import {
  deleteCornTaskApi,
  disableCornTaskApi,
  enableCornTaskApi,
  getCornTaskListApi,
  runCornTaskApi,
} from './api';
import TaskEditor from './components/TaskEditor.vue';

const open = ref(false);
const currentTask = ref<any>({});
const gridOptions: VxeGridProps = {
  minHeight: 500,
  columns: [
    { title: '序号', type: 'seq', width: 50 },
    { field: 'name', title: '任务名称', minWidth: 150 },
    {
      field: 'next_run',
      title: '下次运行时间',
      minWidth: 180,
      formatter: ({ cellValue }): string => {
        if (cellValue) {
          return dayjs(cellValue).format('YYYY-MM-DD HH:mm:ss');
        }
        return '';
      },
    },
    {
      field: 'enabled',
      title: '状态',
      minWidth: 100,
      slots: {
        default: 'enabled',
      },
    },
    {
      field: 'task',
      title: '任务类型',
      minWidth: 100,
      formatter: ({ cellValue }): string => {
        if (cellValue === 'cloud189_auto_save') {
          return '天翼自动转存';
        }
        return '';
      },
    },
    {
      field: 'action',
      title: '操作',
      fixed: 'right',
      width: 220,
      slots: {
        default: 'action',
      },
    },
  ],
  editConfig: {
    trigger: 'click',
    mode: 'row',
  },
  pagerConfig: {
    enabled: false,
  },
  proxyConfig: {
    enabled: false,
  },
  showOverflow: true,
};

const [Grid, gridApi] = useVbenVxeGrid({ gridOptions });
const loading = ref(false);
const reload = () => {
  loading.value = true;
  getCornTaskListApi()
    .then((res: any) => {
      gridApi.grid.loadData(res || []);
    })
    .finally(() => {
      loading.value = false;
    });
};

onMounted(() => {
  reload();
});

onActivated(() => {
  reload();
});

const addRowEvent = () => {
  currentTask.value = {};
  open.value = true;
};

const editRowEvent = (_row: any) => {
  currentTask.value = cloneDeep(_row);
  open.value = true;
};

const deleteRowEvent = (_row: any) => {
  deleteCornTaskApi(_row.name).then(() => {
    message.success('删除成功');
    reload();
  });
};

const runTaskEvent = (row: any) => {
  loading.value = true;
  runCornTaskApi(row.name)
    .then(() => {
      message.success('执行成功');
      reload();
    })
    .finally(() => {
      loading.value = false;
    });
};

const handleSwitchEvent = (row: any) => {
  if (row.enabled) {
    disableCornTaskApi(row.name).then(() => {
      message.success('禁用成功');
      reload();
    });
  } else {
    enableCornTaskApi(row.name).then(() => {
      message.success('启用成功');
      reload();
    });
  }
};
</script>
<template>
  <div class="h-full" v-loading="loading">
    <Grid class="mt-0">
      <template #toolbar-tools>
        <Button @click="reload" type="primary" class="mr-2">刷新</Button>
        <Button type="primary" @click="addRowEvent" class="mb-2 mr-[10px] mt-2">
          创建定时任务
        </Button>
      </template>
      <template #enabled="{ row }">
        <span
          v-if="row.params?.isShareUrlValid === false"
          class="text-yellow-500"
        >
          分享链接失效
        </span>
        <div v-else>
          <Switch :checked="row.enabled" @click="handleSwitchEvent(row)" />
          <span :class="row.enabled ? 'text-green-500' : 'text-red-500'">{{
            row.enabled ? ' 启用' : ' 禁用'
          }}</span>
        </div>
      </template>
      <template #action="{ row }">
        <Button type="link" @click="runTaskEvent(row)" success>
          立即执行
        </Button>
        <Button type="link" @click="editRowEvent(row)">编辑</Button>
        <Button type="link" @click="deleteRowEvent(row)" danger>删除</Button>
      </template>
    </Grid>
    <TaskEditor v-model:open="open" :task="currentTask" @success="reload" />
  </div>
</template>
