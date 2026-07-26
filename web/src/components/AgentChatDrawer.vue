<script setup>
defineProps({
  selectedCourse: { type: Object, default: null },
  chatMessages: { type: Array, required: true },
  chatSending: { type: Boolean, required: true },
  modelValue: { type: String, required: true },
})

const emit = defineEmits(["close", "send", "update:modelValue"])
</script>

<template>
  <aside class="chat-drawer" aria-label="Agent 对话">
    <div class="chat-header">
      <div>
        <span class="eyebrow">{{ selectedCourse?.id || "Course Agent" }}</span>
        <h2>{{ selectedCourse?.name || "课程 Agent" }}</h2>
        <p class="chat-scope">仅访问当前课程的任务与资料</p>
      </div>
      <button class="icon-button" type="button" aria-label="关闭对话" @click="emit('close')">×</button>
    </div>

    <div class="chat-messages" aria-live="polite">
      <div
        v-for="(message, index) in chatMessages"
        :key="`${message.role}-${index}`"
        :class="['chat-message', `message-${message.role}`]"
      >
        <span class="message-role">{{ message.role === "user" ? "你" : "Agent" }}</span>
        <p>{{ message.content }}</p>
      </div>
      <div v-if="chatSending" class="chat-message message-assistant">
        <span class="message-role">Agent</span>
        <p class="typing-dots">正在思考……</p>
      </div>
    </div>

    <form class="chat-composer" @submit.prevent="emit('send')">
      <textarea
        :value="modelValue"
        rows="3"
        :placeholder="selectedCourse ? `例如：${selectedCourse.name}有哪些待完成任务？` : '请先选择课程'"
        :disabled="!selectedCourse"
        @input="emit('update:modelValue', $event.target.value)"
        @keydown.enter.exact.prevent="emit('send')"
      ></textarea>
      <button class="button button-primary" type="submit" :disabled="chatSending || !selectedCourse || !modelValue.trim()">发送</button>
    </form>
  </aside>
</template>
