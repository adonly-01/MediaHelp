<script setup lang="ts">
import { onActivated, onMounted } from 'vue';

import { Affix, Button, message } from 'ant-design-vue';

import { useVbenForm } from '#/adapter/form';

import { getSysConfigApi, updateSysConfigApi } from './api';

defineOptions({
  name: 'Config',
});

// Form 为弹窗组件
// formApi 为弹窗的方法
const [Form, formApi] = useVbenForm({
  wrapperClass: 'm-[20px]',
  layout: 'horizontal',
  resetButtonOptions: {
    show: false,
  },
  submitButtonOptions: {
    show: false,
  },
  schema: [
    {
      component: 'Divider',
      fieldName: '',
      label: 'Emby配置',
      labelWidth: 80,
      wrapperClass: 'w-full',
    },
    {
      component: 'Input',
      fieldName: 'emby_url',
      label: 'Emby地址',
      labelWidth: 100,
    },
    {
      component: 'Input',
      fieldName: 'emby_api_key',
      label: 'Emby APi秘钥',
      labelWidth: 100,
    },
    {
      component: 'Divider',
      fieldName: '',
      label: 'Alist配置',
      labelWidth: 80,
      wrapperClass: 'w-full',
    },
    {
      component: 'Input',
      fieldName: 'alist_url',
      label: 'Alist地址',
      labelWidth: 100,
    },
    {
      component: 'Input',
      fieldName: 'alist_api_key',
      label: 'Alist APi秘钥',
      labelWidth: 100,
    },
    {
      component: 'Divider',
      fieldName: '',
      label: '天翼云盘配置',
      labelWidth: 90,
      wrapperClass: 'w-full',
    },
    {
      component: 'Input',
      fieldName: 'tianyiAccount',
      label: '天翼云盘账号',
      labelWidth: 100,
    },
    {
      component: 'Input',
      fieldName: 'tianyiPassword',
      label: '天翼云盘密码',
      labelWidth: 100,
    },

  ],
});

// 加载配置数据
const loadConfig = async () => {
  const res = await getSysConfigApi({});
  formApi.setFieldValue('emby_url', res.emby_url);
  formApi.setFieldValue('emby_api_key', res.emby_api_key);
  formApi.setFieldValue('alist_url', res.alist_url);
  formApi.setFieldValue('alist_api_key', res.alist_api_key);
  formApi.setFieldValue('tianyiAccount', res.tianyiAccount);
  formApi.setFieldValue('tianyiPassword', res.tianyiPassword);

};

onMounted(() => {
  loadConfig();
});

onActivated(() => {
  // 当组件被缓存重新激活时，重新加载数据
  loadConfig();
});

const handleSave = async () => {
  const params = await formApi.getValues();
  await updateSysConfigApi(params);
  message.success('保存成功');
};
</script>
<template>
  <div>
    <Form />
    <Affix :offset-bottom="50">
      <div class="mr-[20px] flex justify-end">
        <Button type="primary" @click="handleSave">保存配置</Button>
      </div>
    </Affix>
  </div>
</template>
