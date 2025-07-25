<script setup lang="ts">
import type { PropType } from 'vue';

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

import {
  AutoComplete,
  Button,
  Form,
  FormItem,
  Input,
  InputNumber,
  message,
  Modal,
  Select,
} from 'ant-design-vue';

import { getResourceListApi } from '#/views/resource/api';
import {
  getCloudTypeByTask,
  getCloudTypeByUrl,
  getTaskByUrl,
} from '#/views/utils';

import {
  createCornTaskApi,
  getCornTaskTypeListApi,
  updateCornTaskApi,
} from '../api';
import SelectFolder from './SelectFolder.vue';

const props = defineProps({
  task: {
    type: Object as PropType<any>,
    default: () => ({}),
  },
});
const emit = defineEmits(['success']);
const open = defineModel<boolean>('open', {
  default: false,
  type: Boolean,
});
const formRef = ref<any>(null);
watch(
  () => props.task,
  (newVal) => {
    getCornTaskTypeListApi().then((_res) => {
      taskTypeList.value = _res || [];
    });
    const task = newVal;
    cloudType.value = getCloudTypeByTask(task.task);
    currentTask.value.task = task.task;
    currentTask.value.name = task.name;
    lastTaskName = task.name;
    const params = task?.params || {};
    currentTask.value.shareUrl = params.shareUrl;
    currentTask.value.targetDir = params.targetDir;
    currentTask.value.sourceDir = params.sourceDir;
    currentTask.value.startMagic = params.startMagic || [];
    currentTask.value.pattern = params.pattern;
    currentTask.value.replace = params.replace;
    currentTask.value.cron = task.cron ?? '0 19-23 * * *';
    resourceList.value = [];
    allResourceList.value = [];
    cloudTypeList.value = [];
  },
);

const modalTitle = computed(() => {
  return props.task.name || '创建定时任务';
});
const width = ref('');
const currentTask = ref<any>({});
const taskTypeList = ref<any[]>([]);

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
const loading = ref(false);
const resourceList = ref<any[]>([]);
const allResourceList = ref<any[]>([]);
const cloudTypeList = ref<any[]>([]);
const cloudType = ref('');
const loadResource = async (keyword?: string) => {
  resourceList.value = [];
  loading.value = true;
  const res = await getResourceListApi({
    keyword,
  }).finally(() => {
    loading.value = false;
  });
  // 平展资源列表
  const flatResourceList: any[] = [];
  res.forEach((item: any) => {
    const { list } = item;
    if (list.length > 0) {
      list?.forEach((item2: any) => {
        flatResourceList.push({
          ...item.channelInfo,
          ...item2,
        });
      });
    }
  });
  cloudTypeList.value = [
    ...new Set(flatResourceList.map((item) => item.cloudType)),
  ].map((item) => ({
    label: item,
    value: item,
  }));
  allResourceList.value = flatResourceList || [];
  filterResource(keyword);
};

const filterResource = (keyword?: string) => {
  if (cloudType.value) {
    resourceList.value = allResourceList.value
      .filter((item) => item.cloudType === cloudType.value)
      .map((item) => {
        return {
          ...item,
          keyword,
          label: item.title,
          value: item.cloudLinks?.[0],
        };
      });
    return;
  }
  resourceList.value = allResourceList.value;
};

const handleSearch = (_value: string) => {
  if (currentTask.value?.task) {
    cloudType.value = 'tianyiyun';
    // 进行资源搜索
    loadResource(_value);
  } else {
    message.warning('请先选择任务类型');
  }
};

const onSelect: any = (_value: string, option: any) => {
  currentTask.value.shareUrl = option.cloudLinks?.[0];
  currentTask.value.name = option.keyword;
};
let lastTaskName = '';
const handleNameChange: any = (value: string) => {
  if (!value) {
    resourceList.value = [];
  }
  if (props.task?.name) {
    nextTick(() => {
      currentTask.value.name = lastTaskName;
      message.warning('编辑禁止修改任务名称');
    });
  }
};
const onJump = (item: any) => {
  window.open(item.cloudLinks?.[0], '_blank');
};
const selectFolderOpen = ref(false);
const url = ref('');
const onShareUrlChange: any = (e: any) => {
  currentTask.value.task = getTaskByUrl(e.target.value);
  cloudType.value = getCloudTypeByUrl(e.target.value);
};
const onSelectFolder = () => {
  if (!currentTask.value?.shareUrl) {
    message.warning('请先输入分享链接');
    return;
  }
  const shareUrl = currentTask.value.shareUrl;
  currentTask.value.task = getTaskByUrl(shareUrl);
  cloudType.value = getCloudTypeByUrl(shareUrl);
  url.value = shareUrl;
  selectFolderOpen.value = true;
};
const onSelecSelftFolder = () => {
  cloudType.value = getCloudTypeByTask(currentTask.value.task);
  if (!cloudType.value) {
    message.warning('请先选择任务类型');
    return;
  }
  url.value = '';
  selectFolderOpen.value = true;
};
const onSelectFolderOkShareQuark = (url: string) => {
  currentTask.value.shareUrl = url;
};
const onSelectFolderOkShareTianyiyun = (fid: string) => {
  currentTask.value.sourceDir = fid;
};

const onSelectFolderOkSelfTianyiyun = (fid: string) => {
  currentTask.value.targetDir = fid;
};

// 重名命规则
const onSelectPattern: any = (value: string) => {
  currentTask.value.pattern = value;
  currentTask.value.replace = '';
};
// 保存文件规则
const onAddRule = () => {
  currentTask.value.startMagic?.push({
    type: '',
    symbol: '',
    value: '',
  });
};
const onDeleteRule = (index: number) => {
  currentTask.value.startMagic?.splice(index, 1);
};
const onOk = () => {
  formRef.value.validate().then((res: any) => {
    const params = {
      task: res.task,
      name: res.name,
      cron: res.cron,
      params: {
        shareUrl: res.shareUrl,
        targetDir: res.targetDir,
        sourceDir: currentTask.value.sourceDir,
        startMagic: res.startMagic,
        pattern: currentTask.value.pattern,
        isShareUrlValid: true,
        replace: currentTask.value.replace,
      },
    };
    const methods = props.task?.cron ? updateCornTaskApi : createCornTaskApi;
    methods(params).then(() => {
      message.success('保存成功');
      emit('success');
      open.value = false;
    });
  });
};
</script>

<template>
  <Modal
    v-model:open="open"
    :title="modalTitle"
    :width="width"
    @ok="onOk"
    :destroy-on-close="true"
  >
    <Form
      ref="formRef"
      class="m-4"
      :model="currentTask"
      :label-col="{ span: 4 }"
      :wrapper-col="{ span: 14 }"
    >
      <FormItem
        label="任务类型"
        name="task"
        :rules="[{ required: true, message: '请选择任务类型' }]"
      >
        <Select
          v-model:value="currentTask.task"
          :disabled="!!props.task?.name"
          placeholder="请选择任务类型"
          :options="taskTypeList"
        />
      </FormItem>
      <FormItem
        label="任务名称"
        name="name"
        :rules="[{ required: true, message: '请输入任务名称' }]"
      >
        <AutoComplete
          v-model:value="currentTask.name"
          :options="resourceList"
          @select="onSelect"
        >
          <template #option="item">
            <div>
              <Button type="link" @click.stop="onJump(item)">链接</Button>
              {{ item.label }}
            </div>
          </template>
          <Input.Search
            placeholder="请输入任务名称"
            enter-button
            :loading="loading"
            @change="handleNameChange"
            @search="handleSearch"
            v-model:value="currentTask.name"
          />
        </AutoComplete>
      </FormItem>
      <FormItem
        label="分享链接"
        name="shareUrl"
        :rules="[{ required: true, message: '请输入分享链接' }]"
      >
        <Input.Group compact>
          <Input
            v-model:value="currentTask.shareUrl"
            style="width: calc(100% - 88px)"
            @change="onShareUrlChange"
          />
          <Button type="primary" @click="onSelectFolder">选择目录</Button>
        </Input.Group>
      </FormItem>
      <FormItem
        label="保存到"
        name="targetDir"
        :rules="[{ required: true, message: '请选择目标文件夹' }]"
      >
        <Input.Group compact>
          <Input
            v-model:value="currentTask.targetDir"
            disabled
            style="width: calc(100% - 88px)"
          />
          <Button type="primary" @click="onSelecSelftFolder">选择目录</Button>
        </Input.Group>
      </FormItem>
      <FormItem label="重名命规则">
        <Input.Group compact>
          <AutoComplete
            v-model:value="currentTask.pattern"
            :options="[
              { label: '视频系列', value: 'VIDEO_SERIES' },
              { label: '电视节目', value: 'SERIES_FORMAT' },
              { label: '综艺节目', value: 'VARIETY_SHOW' },
              { label: '内容过滤', value: 'CONTENT_FILTER' },
            ]"
            @select="onSelectPattern"
            style="width: 50%"
          >
            <Input
              v-model:value="currentTask.pattern"
              placeholder="请输入匹配规则"
            />
          </AutoComplete>
          <Input
            v-model:value="currentTask.replace"
            style="width: 50%"
            allow-clear
            placeholder="请输入替换规则"
          />
        </Input.Group>
      </FormItem>
      <FormItem label="保存文件规则" name="startMagic">
        <div class="w-full">
          <Button type="primary" @click="onAddRule">添加规则</Button>
          <Input.Group
            compact
            class="mt-2"
            v-for="(item, index) in currentTask.startMagic"
            :key="index"
          >
            <Select
              v-model:value="item.type"
              style="width: calc(33% - 20px)"
              placeholder="请选择规则类型"
            >
              <Select.Option value="EPISODE">集数</Select.Option>
              <Select.Option value="SEASON">季数</Select.Option>
              <Select.Option value="SEASON_FULL">完整季数</Select.Option>
              <Select.Option value="YEAR">年份</Select.Option>
              <Select.Option value="CHINESE_TEXT">中文内容</Select.Option>
            </Select>
            <Select
              v-model:value="item.symbol"
              style="width: calc(33% - 20px)"
              placeholder="请选择符号"
            >
              <Select.Option value=">">大于</Select.Option>
              <Select.Option value="<">小于</Select.Option>
              <Select.Option value="=">等于</Select.Option>
            </Select>
            <InputNumber
              v-model:value="item.value"
              style="width: calc(33% - 20px)"
              placeholder="请输入数字"
            />
            <Button type="primary" @click="onDeleteRule(index)" danger>
              删除
            </Button>
          </Input.Group>
        </div>
      </FormItem>
      <FormItem label="保存文件正则" name="search_pattern">
        <Input
          v-model:value="currentTask.search_pattern"
          placeholder="请输入保存文件正则"
        />
      </FormItem>
      <FormItem
        label="定时规则"
        name="cron"
        :rules="[{ required: true, message: '请输入定时规则' }]"
      >
        <Input v-model:value="currentTask.cron" placeholder="请输入定时规则" />
      </FormItem>
    </Form>
    <SelectFolder
      v-model:open="selectFolderOpen"
      :url="url"
      :cloud-type="cloudType"

      @ok-share-tianyiyun="onSelectFolderOkShareTianyiyun"

      @ok-self-tianyiyun="onSelectFolderOkSelfTianyiyun"
    />
  </Modal>
</template>
