<script setup>
defineProps({
  selectedCourse: { type: Object, default: null },
})

const emit = defineEmits(["materials", "risks", "chat", "create", "logout"])
</script>

<template>
  <header class="topbar">
    <div class="breadcrumb">
      <span>课程工作台</span>
      <span class="breadcrumb-slash">/</span>
      <strong>今日计划</strong>
    </div>

    <div class="topbar-actions">
      <button class="button button-secondary" type="button" :disabled="!selectedCourse" @click="emit('materials')">
        <span class="button-glyph">▤</span>
        课程资料
      </button>
      <button class="button button-secondary" type="button" @click="emit('risks')">
        <span class="button-glyph">◈</span>
        风险雷达
      </button>
      <button class="button button-secondary" type="button" :disabled="!selectedCourse" @click="emit('chat')">
        <span class="button-glyph">✦</span>
        问本课程 Agent
      </button>
      <button class="button button-primary" type="button" :disabled="!selectedCourse" @click="emit('create')">
        <span class="button-glyph">＋</span>
        新建任务
      </button>
      <button class="button button-secondary" type="button" @click="emit('logout')">
        退出登录
      </button>
    </div>
  </header>
</template>
