<script setup>
defineProps({
  selectedTask: { type: Object, default: null },
  taskPlan: { type: Object, default: null },
  plansLoading: { type: Boolean, required: true },
  planSaving: { type: Boolean, required: true },
  planError: { type: String, required: true },
  statusLabel: { type: Function, required: true },
  priorityLabel: { type: Function, required: true },
  planStatusLabel: { type: Function, required: true },
})

const emit = defineEmits([
  "generate-plan",
  "plan-action",
  "toggle-status",
  "edit",
  "delete",
])
</script>

<template>
  <aside class="detail-column">
    <div v-if="selectedTask" class="detail-card">
      <div class="detail-card-heading">
        <div>
          <span class="eyebrow">任务详情</span>
          <h2>{{ selectedTask.title }}</h2>
        </div>
        <span :class="['detail-status-badge', `status-${selectedTask.status}`]">
          {{ statusLabel(selectedTask.status) }}
        </span>
      </div>

      <div class="detail-facts">
        <div><span>课程</span><strong>{{ selectedTask.course_name }}</strong></div>
        <div><span>截止日期</span><strong>{{ selectedTask.deadline }}</strong></div>
        <div><span>优先级</span><strong>{{ priorityLabel(selectedTask.priority) }}</strong></div>
        <div><span>任务 ID</span><strong class="mono-text">{{ selectedTask.id }}</strong></div>
      </div>

      <div class="detail-requirement">
        <span>具体要求</span>
        <p>{{ selectedTask.description }}</p>
      </div>

      <section class="plan-panel">
        <div class="plan-heading">
          <div class="plan-heading-copy">
            <span>学习计划</span>
            <strong v-if="taskPlan">{{ planStatusLabel(taskPlan.status) }}</strong>
            <p v-else-if="selectedTask.status === 'todo'" class="plan-heading-hint">
              根据任务和课程资料，生成可确认的执行步骤
            </p>
          </div>
          <button
            v-if="!taskPlan && selectedTask.status === 'todo'"
            class="button button-primary plan-generate-button"
            type="button"
            :disabled="planSaving"
            @click="emit('generate-plan')"
          >
            <span class="button-glyph" aria-hidden="true">✦</span>
            <span>{{ planSaving ? "正在生成…" : "生成学习计划草案" }}</span>
            <span class="plan-generate-arrow" aria-hidden="true">→</span>
          </button>
        </div>

        <p v-if="plansLoading" class="plan-muted">正在读取学习计划…</p>
        <p v-else-if="planError" class="form-error">{{ planError }}</p>
        <template v-else-if="taskPlan">
          <p class="plan-goal">{{ taskPlan.goal }}</p>
          <p v-if="taskPlan.prerequisite_knowledge?.length" class="plan-prerequisite">
            前置：{{ taskPlan.prerequisite_knowledge.join("；") }}
          </p>
          <ol class="plan-step-list">
            <li v-for="step in taskPlan.steps" :key="step.id">
              <div>
                <strong>{{ step.position }}. {{ step.title }}</strong>
                <small>{{ step.estimated_minutes }} 分钟 · {{ step.status }}</small>
                <p>{{ step.description }}</p>
              </div>
            </li>
          </ol>
          <p v-if="taskPlan.sources?.length" class="plan-sources">
            资料来源：
            <span v-for="source in taskPlan.sources" :key="`${source.file_id}-${source.page}`">
              {{ source.file_name }}{{ source.page ? `（第 ${source.page} 页）` : "" }}
            </span>
          </p>
          <div class="plan-actions">
            <button
              v-if="taskPlan.status === 'awaiting_confirmation'"
              class="button button-primary button-wide"
              type="button"
              :disabled="planSaving"
              @click="emit('plan-action', 'confirm')"
            >确认并启动计划</button>
            <button
              v-else-if="taskPlan.status === 'active'"
              class="button button-secondary button-wide"
              type="button"
              :disabled="planSaving"
              @click="emit('plan-action', 'pause')"
            >暂停计划</button>
            <button
              v-else-if="taskPlan.status === 'paused'"
              class="button button-primary button-wide"
              type="button"
              :disabled="planSaving"
              @click="emit('plan-action', 'resume')"
            >恢复计划</button>
          </div>
        </template>
        <p v-else class="plan-muted">生成计划后，确认才会启动；它不会修改任务状态。</p>
      </section>

      <div class="detail-actions">
        <button
          class="button button-primary button-wide"
          type="button"
          @click="emit('toggle-status', selectedTask.id, selectedTask.status === 'todo' ? 'done' : 'todo')"
        >
          {{ selectedTask.status === "todo" ? "标记为已完成" : "恢复为未完成" }}
        </button>
        <button class="button button-secondary button-wide" type="button" @click="emit('edit')">编辑任务</button>
        <button class="text-button danger-text" type="button" @click="emit('delete')">删除任务</button>
      </div>
    </div>

    <div v-else class="detail-empty">
      <div class="empty-orbit">✦</div>
      <span class="eyebrow">Focus view</span>
      <h2>选择一项任务</h2>
      <p>点击左侧任务卡片，在这里查看完整要求并执行操作。</p>
    </div>
  </aside>
</template>
