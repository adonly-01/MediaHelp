<script setup lang="ts">
import { ref } from 'vue';

import { Button, message, Tag } from 'ant-design-vue';

import TaskEditor from '#/views/cornTask/components/TaskEditor.vue';
import { getTaskByUrl } from '#/views/utils';

const props = defineProps<{
  item: any;
}>();
const emit = defineEmits(['save']);
// const parsedItem = ref<any>({});

// const parseResourceText = (text: string) => {
//   const result = {
//     name: '',
//     description: '',
//     size: '',
//     share: '',
//     link: '',
//     tags: [] as string[],
//   };

//   // 解析名称 - 支持方括号和书名号格式
//   const nameRegex = /^(?:名称：)?[「[]?([^」\]]+)[」\]]?/u;
//   const nameMatch = text.match(nameRegex);
//   if (nameMatch?.[1]) {
//     result.name = nameMatch[1].trim();
//   }

//   // 解析简介或描述
//   const descRegex =
//     /(?:简介|描述)：([\s\S]+?)(?=链接：|https:\/\/|🏷|标签：|大小：|📁)/u;
//   const descMatch = text.match(descRegex);
//   if (descMatch?.[1]) {
//     result.description = descMatch[1].trim();
//   }
//   return result;
// };

// onMounted(() => {
//   // parsedItem.value = parseResourceText(props.item.title);
// });

// watch(
//   () => props.item,
//   (newVal) => {
//     // parsedItem.value = parseResourceText(newVal.title);
//   },
// );

const onJump = () => {
  window.open(props.item.cloudLinks?.[0], '_blank');
};

const onSave = () => {
  emit('save', props.item);
};
// 定时任务
const open = ref(false);
const currentTask = ref<any>({});
const onCreateTask = () => {
  const shareUrl = props.item.cloudLinks?.[0];
  if (shareUrl) {
    currentTask.value = {
      task: getTaskByUrl(shareUrl),
      name: props.item.keyword || props.item.title,
      params: {
        shareUrl,
      },
    };
    open.value = true;
  } else {
    message.error('创建任务出错，没有分享链接');
  }
};
</script>

<template>
  <div class="rounded-lg border">
    <div class="flex p-4 shadow-sm">
      <div class="w-1/3">
        <div class="relative pb-[150%]">
          <img
            :src="item.image"
            class="absolute inset-0 h-full w-full rounded-lg object-cover"
            alt="海报"
          />
          <Tag
            class="absolute left-[2px] top-[2px] z-10"
            color="blue"
            :bordered="false"
          >
            {{ item.cloudType }}
          </Tag>
        </div>
      </div>
      <div class="flex w-2/3 flex-col justify-between pl-4">
        <div>
          <h3 class="mb-2 truncate text-lg font-bold" :alt="item.title">
            {{
              item.title?.indexOf('名称') === -1
                ? item.title
                : item.title?.split('名称：')[1]
            }}
          </h3>
          <p class="mb-2 line-clamp-3 text-gray-600">
            {{ item.content }}
          </p>
        </div>
        <div class="text-sm text-gray-500">
          <p class="flex items-center overflow-hidden whitespace-nowrap">
            标签:
            <span class="ml-1 flex-1 overflow-hidden">
              <Tag
                v-for="tag in item.tags"
                :key="tag"
                :color="
                  ['pink', 'red', 'orange', 'cyan', 'blue', 'purple'][
                    Math.floor(Math.random() * 6)
                  ]
                "
                class="mr-1 inline-block"
              >
                {{ tag }}
              </Tag>
            </span>
          </p>
        </div>
      </div>
    </div>
    <div class="h-[50px] w-full border-t text-right">
      <Button type="link" class="m-2" size="middle" @click="onJump">
        跳转
      </Button>
      <Button
        type="link"
        class="m-2"
        size="middle"
        @click="onSave"
        v-show="['tianyiyun'].includes(item.cloudType)"
      >
        转存
      </Button>
      <Button type="link" class="m-2" size="middle" @click="onCreateTask">
        创建定时任务
      </Button>
    </div>
    <TaskEditor v-model:open="open" :task="currentTask" />
  </div>
</template>
