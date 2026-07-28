<script setup>
defineProps({
  selectedCourse: { type: Object, default: null },
  tasks: { type: Array, required: true },
  filteredTasks: { type: Array, required: true },
  selectedTaskId: { type: String, required: true },
  taskFilter: { type: String, required: true },
  doneCount: { type: Number, required: true },
  tasksLoading: { type: Boolean, required: true },
  taskError: { type: String, required: true },
  statusLabel: { type: Function, required: true },
  priorityLabel: { type: Function, required: true },
  priorityClass: { type: Function, required: true },
})

const emit = defineEmits(["select", "create", "update:task-filter"])
</script>

<template>
  <div class="task-column">
    <div class="section-heading">
      <div>
        <span class="eyebrow">任务清单</span>
        <h2>{{ selectedCourse?.name || "选择一门课程" }}</h2>
      </div>
      <div class="task-summary">
        <span>{{ tasks.length }} 项任务</span>
        <span class="summary-divider"></span>
        <span>{{ doneCount }} 项已完成</span>
      </div>
    </div>

    <div class="filter-bar" role="tablist">
      <button
        v-for="filter in [
          { value: 'todo', label: '待完成' },
          { value: 'done', label: '已完成' },
          { value: 'all', label: '全部' },
        ]"
        :key="filter.value"
        :class="['filter-button', { active: taskFilter === filter.value }]"
        type="button"
        role="tab"
        :aria-selected="taskFilter === filter.value"
        @click="emit('update:task-filter', filter.value)"
      >
        {{ filter.label }}
      </button>
    </div>

    <p v-if="tasksLoading" class="state-message">正在加载任务……</p>
    <p v-else-if="taskError" class="state-message error-text">{{ taskError }}</p>

    <div v-else-if="filteredTasks.length" class="task-list">
      <article
        v-for="task in filteredTasks"
        :key="task.id"
        :class="['task-card', { selected: task.id === selectedTaskId }]"
        role="button"
        tabindex="0"
        @click="emit('select', task.id)"
        @keydown.enter="emit('select', task.id)"
        @keydown.space.prevent="emit('select', task.id)"
      >
        <div class="task-card-topline">
          <span :class="['status-marker', `status-${task.status}`]"></span>
          <span class="task-status-label">{{ statusLabel(task.status) }}</span>
          <span :class="['priority-chip', priorityClass(task.priority)]">
            {{ priorityLabel(task.priority) }}优先级
          </span>
        </div>
        <h3>{{ task.title }}</h3>
        <p class="task-description">{{ task.description }}</p>
        <div class="task-card-footer">
          <span>截止 {{ task.deadline }}</span>
          <span class="task-arrow">↗</span>
        </div>
      </article>
    </div>

    <div v-else class="empty-state">
      <span class="empty-mark">○</span>
      <strong>{{ taskFilter === "all" ? "还没有任务" : "没有匹配的任务" }}</strong>
      <p>
        {{ taskFilter === "all" ? "从一个小任务开始，把计划落到今天。" : "试试切换上方的筛选条件。" }}
      </p>
      <button
        v-if="taskFilter === 'all' && selectedCourse"
        class="button button-primary"
        type="button"
        @click="emit('create')"
      >
        新建第一个任务
      </button>
    </div>
  </div>
</template>
