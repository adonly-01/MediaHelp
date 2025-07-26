# 前端配置页面更新说明

## 概述

为了支持新的媒体重命名系统，对前端的天翼云盘自动保存任务配置页面进行了全面更新，提供更直观和强大的重命名配置功能。

## 🎯 更新内容

### 1. **新的重命名配置界面**

#### 智能重命名配置区域
- **重命名风格选择器**: 提供多种预设风格选项
- **自定义模板输入**: 支持完全自定义的重命名模板
- **模板变量提示**: 可点击插入的变量按钮
- **高级选项**: 忽略扩展名等配置

#### 配置选项
```typescript
// 重命名风格选项
const renameStyles = [
  { value: 'simple', label: '简洁格式 (标题.S01E01.扩展名)' },
  { value: 'standard', label: '标准格式 (包含画质、来源等信息)' },
  { value: 'custom', label: '自定义模板' },
  // 动态加载的预设模板
  // 用户自定义模板
];
```

### 2. **动态模板加载**

#### API 集成
```typescript
// 获取重命名模板
export async function getRenameTemplatesApi() {
  return requestClient.get('/smart-rename/templates', {});
}

// 获取模板变量
export async function getTemplateVariablesApi() {
  return requestClient.get('/smart-rename/templates/variables', {});
}
```

#### 模板数据结构
```typescript
interface RenameTemplate {
  value: string;        // 模板标识
  label: string;        // 显示名称
  template: string;     // 模板内容
  type: 'preset' | 'custom';  // 模板类型
}

interface TemplateVariable {
  variable: string;     // 变量名 (如 {title})
  description: string;  // 变量描述
}
```

### 3. **用户界面改进**

#### 重命名风格选择
```vue
<Select v-model:value="currentTask.renameStyle" placeholder="选择重命名风格">
  <!-- 基础选项 -->
  <Select.Option value="simple">简洁格式</Select.Option>
  <Select.Option value="standard">标准格式</Select.Option>
  <Select.Option value="custom">自定义模板</Select.Option>
  
  <!-- 预设模板组 -->
  <Select.OptGroup label="预设模板">
    <Select.Option v-for="template in presetTemplates" :value="template.value">
      {{ template.label }}
    </Select.Option>
  </Select.OptGroup>
  
  <!-- 自定义模板组 -->
  <Select.OptGroup label="自定义模板">
    <Select.Option v-for="template in customTemplates" :value="template.value">
      {{ template.label }}
    </Select.Option>
  </Select.OptGroup>
</Select>
```

#### 自定义模板输入
```vue
<div v-if="currentTask.renameStyle === 'custom'">
  <Input
    v-model:value="currentTask.renameTemplate"
    placeholder="例如: {title}.S{season:02d}E{episode:02d}.{extension}"
  />
  
  <!-- 变量提示区域 -->
  <div class="template-variables">
    <div class="grid grid-cols-2 gap-1">
      <div 
        v-for="variable in templateVariables" 
        class="variable-button"
        @click="insertVariable(variable.variable)"
        :title="variable.description"
      >
        {{ variable.variable }}
      </div>
    </div>
  </div>
</div>
```

### 4. **兼容性处理**

#### 传统配置支持
- 保留原有的 pattern/replace 配置选项
- 提供"兼容模式"切换
- 平滑的配置迁移

#### 配置参数映射
```typescript
const params = {
  // 新的重命名配置
  renameStyle: currentTask.value.renameStyle || 'simple',
  renameTemplate: currentTask.value.renameTemplate || '',
  ignoreExtension: currentTask.value.ignoreExtension || false,
  
  // 兼容旧的配置
  pattern: currentTask.value.pattern,
  replace: currentTask.value.replace,
};
```

## 🚀 功能特性

### 1. **直观的配置界面**
- **可视化选择**: 通过下拉菜单选择重命名风格
- **实时预览**: 模板变量的即时提示
- **智能提示**: 变量描述和使用说明

### 2. **强大的自定义功能**
- **模板编辑器**: 支持完全自定义的重命名模板
- **变量插入**: 点击即可插入模板变量
- **格式验证**: 前端基础的模板格式检查

### 3. **用户体验优化**
- **分组显示**: 预设模板和自定义模板分组显示
- **搜索过滤**: 支持模板名称搜索
- **快速操作**: 一键插入常用变量

## 📋 配置示例

### 基础配置
```json
{
  "renameStyle": "simple",
  "renameTemplate": "",
  "ignoreExtension": false
}
```

### 自定义模板配置
```json
{
  "renameStyle": "custom",
  "renameTemplate": "{title} - 第{season}季第{episode:02d}集 [{quality}].{extension}",
  "ignoreExtension": false
}
```

### 预设模板配置
```json
{
  "renameStyle": "tv_plex",
  "renameTemplate": "",
  "ignoreExtension": false
}
```

## 🔧 技术实现

### 1. **响应式数据管理**
```typescript
const renameTemplates = ref<RenameTemplate[]>([]);
const templateVariables = ref<TemplateVariable[]>([]);
const showLegacyOptions = ref(false);
```

### 2. **异步数据加载**
```typescript
onMounted(() => {
  loadRenameTemplates();
  loadTemplateVariables();
});
```

### 3. **用户交互处理**
```typescript
// 插入模板变量
const insertVariable = (variable: string) => {
  if (currentTask.value.renameTemplate) {
    currentTask.value.renameTemplate += variable;
  } else {
    currentTask.value.renameTemplate = variable;
  }
};
```

## 📈 用户体验提升

### 1. **学习成本降低**
- 预设模板减少用户学习成本
- 可视化配置界面更直观
- 变量提示帮助用户理解

### 2. **配置效率提升**
- 一键选择常用格式
- 快速插入模板变量
- 实时配置验证

### 3. **功能扩展性**
- 支持动态加载新模板
- 用户可创建和分享模板
- 灵活的配置选项

## 🔍 测试建议

### 1. **功能测试**
- 测试各种重命名风格的选择
- 测试自定义模板的输入和验证
- 测试模板变量的插入功能

### 2. **兼容性测试**
- 测试旧配置的加载和显示
- 测试配置迁移的正确性
- 测试新旧配置的混合使用

### 3. **用户体验测试**
- 测试界面的响应性和流畅度
- 测试不同屏幕尺寸的适配
- 测试错误提示和用户引导

## 总结

前端配置页面的更新为用户提供了：

1. **更直观的配置界面** - 可视化的重命名风格选择
2. **更强大的自定义功能** - 完全自定义的模板编辑
3. **更好的用户体验** - 智能提示和快速操作
4. **更好的兼容性** - 平滑的配置迁移和向后兼容

这些改进使得天翼云盘自动保存任务的配置变得更加简单和强大，用户可以轻松创建符合自己需求的重命名规则。
