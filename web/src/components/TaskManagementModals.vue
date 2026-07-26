<script setup>
defineProps({
  formMode: { type: String, default: null },
  formTitle: { type: String, required: true },
  taskForm: { type: Object, required: true },
  courses: { type: Array, required: true },
  formSaving: { type: Boolean, required: true },
  formError: { type: String, required: true },
  deleteDialogOpen: { type: Boolean, required: true },
  deleteConfirmationText: { type: String, required: true },
  deleteInput: { type: String, required: true },
  deleteError: { type: String, required: true },
  deleteSaving: { type: Boolean, required: true },
})

const emit = defineEmits([
  "close-form",
  "submit-form",
  "close-delete",
  "confirm-delete",
  "update:delete-input",
])
</script>

<template>
  <div v-if="formMode" class="modal-backdrop" @click.self="emit('close-form')">
    <form class="modal-card" @submit.prevent="emit('submit-form')">
      <div class="modal-header">
        <div><span class="eyebrow">任务管理</span><h2>{{ formTitle }}</h2></div>
        <button class="icon-button" type="button" aria-label="关闭表单" @click="emit('close-form')">×</button>
      </div>
      <label v-if="formMode === 'create'" class="form-field">
        <span>任务 ID</span>
        <input v-model.trim="taskForm.task_id" required placeholder="例如：os-lab-2" />
      </label>
      <label v-if="formMode === 'create'" class="form-field">
        <span>所属课程</span>
        <select v-model="taskForm.course" required>
          <option value="" disabled>选择课程</option>
          <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.name }}</option>
        </select>
      </label>
      <label v-else class="form-field"><span>任务 ID</span><input :value="taskForm.task_id" disabled /></label>
      <label class="form-field"><span>任务标题</span><input v-model.trim="taskForm.title" required placeholder="例如：完成实验报告" /></label>
      <div class="form-row">
        <label class="form-field"><span>截止日期</span><input v-model="taskForm.deadline" type="date" required /></label>
        <label class="form-field">
          <span>优先级</span>
          <select v-model="taskForm.priority" required>
            <option value="high">高</option><option value="medium">中</option><option value="low">低</option>
          </select>
        </label>
      </div>
      <label class="form-field"><span>具体要求</span><textarea v-model.trim="taskForm.description" rows="5" required placeholder="写下完成标准或提交要求"></textarea></label>
      <p v-if="formError" class="form-error" role="alert">{{ formError }}</p>
      <div class="modal-actions">
        <button class="button button-secondary" type="button" :disabled="formSaving" @click="emit('close-form')">取消</button>
        <button class="button button-primary" type="submit" :disabled="formSaving">{{ formSaving ? "正在保存……" : "保存任务" }}</button>
      </div>
    </form>
  </div>

  <div v-if="deleteDialogOpen" class="modal-backdrop" @click.self="emit('close-delete')">
    <section class="modal-card danger-modal" role="dialog" aria-modal="true">
      <div class="modal-header">
        <div><span class="eyebrow danger-text">不可逆操作</span><h2>删除任务？</h2></div>
        <button class="icon-button" type="button" aria-label="关闭删除确认" @click="emit('close-delete')">×</button>
      </div>
      <p class="danger-copy">删除前会自动备份业务数据库，但任务本身将从当前数据中移除。</p>
      <p class="confirmation-hint">请输入：<code>{{ deleteConfirmationText }}</code></p>
      <input
        :value="deleteInput"
        class="confirmation-input"
        autocomplete="off"
        placeholder="输入确认文本"
        @input="emit('update:delete-input', $event.target.value)"
        @keyup.enter="emit('confirm-delete')"
      />
      <p v-if="deleteError" class="form-error" role="alert">{{ deleteError }}</p>
      <div class="modal-actions">
        <button class="button button-secondary" type="button" :disabled="deleteSaving" @click="emit('close-delete')">取消</button>
        <button class="button button-danger" type="button" :disabled="deleteSaving" @click="emit('confirm-delete')">{{ deleteSaving ? "正在删除……" : "确认删除" }}</button>
      </div>
    </section>
  </div>
</template>
