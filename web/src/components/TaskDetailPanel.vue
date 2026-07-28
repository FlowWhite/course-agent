<script setup>
import { ref, watch } from "vue"

const props = defineProps({
  selectedTask: { type: Object, default: null },
  taskPlan: { type: Object, default: null },
  plansLoading: { type: Boolean, required: true },
  planSaving: { type: Boolean, required: true },
  planError: { type: String, required: true },
  taskAssessment: { type: Object, default: null },
  assessmentSaving: { type: Boolean, required: true },
  assessmentError: { type: String, required: true },
  statusLabel: { type: Function, required: true },
  priorityLabel: { type: Function, required: true },
  planStatusLabel: { type: Function, required: true },
})

const emit = defineEmits([
  "generate-plan",
  "confirm-plan",
  "toggle-status",
  "edit",
  "delete",
  "assess-submission",
])

const assessmentFile = ref(null)
const assessmentFileInput = ref(null)

const verdictLabels = {
  meets_requirements: "基本符合",
  needs_revision: "需要完善",
  insufficient_information: "证据不足",
}

const requirementStatusLabels = {
  met: "已满足",
  partially_met: "部分满足",
  missing: "未体现",
  not_assessable: "无法判断",
}

function selectAssessmentFile(event) {
  assessmentFile.value = event.target.files?.[0] || null
}

function submitAssessment() {
  if (assessmentFile.value) {
    emit("assess-submission", assessmentFile.value)
  }
}

watch(
  () => props.selectedTask?.id,
  () => {
    assessmentFile.value = null
    if (assessmentFileInput.value) {
      assessmentFileInput.value.value = ""
    }
  },
)
</script>

<template>
  <aside class="detail-column">
    <div v-if="selectedTask" class="detail-card">
      <div class="detail-card-heading">
        <div>
          <span class="eyebrow">任务详情</span>
          <h2>{{ selectedTask.title }}</h2>
        </div>
        <div class="detail-heading-actions">
          <span :class="['detail-status-badge', `status-${selectedTask.status}`]">
            {{ statusLabel(selectedTask.status) }}
          </span>
          <div class="detail-management-actions" aria-label="任务管理操作">
            <button class="detail-action-button" type="button" @click="emit('edit')">编辑</button>
            <button class="detail-action-button danger-text" type="button" @click="emit('delete')">删除</button>
          </div>
        </div>
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
              @click="emit('confirm-plan')"
            >确认并启动计划</button>
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
      </div>

      <section class="assessment-panel" aria-labelledby="assessment-title">
        <div class="assessment-heading">
          <div>
            <span class="eyebrow">作业评估</span>
            <h3 id="assessment-title">提交作业并检查要求</h3>
          </div>
          <span
            v-if="taskAssessment"
            :class="['assessment-verdict', `verdict-${taskAssessment.verdict}`]"
          >{{ verdictLabels[taskAssessment.verdict] || taskAssessment.verdict }}</span>
        </div>
        <p class="assessment-intro">
          上传 PDF、DOCX、TXT 或 MD。课程 Agent 会结合本任务要求与当前课程资料给出建议；文件只在本次评估期间使用，不会保存或修改任务。
        </p>

        <div class="assessment-upload-row">
          <label class="assessment-file-control">
            <span>选择作业文件</span>
            <input
              ref="assessmentFileInput"
              type="file"
              accept=".pdf,.docx,.txt,.md"
              :disabled="assessmentSaving"
              @change="selectAssessmentFile"
            >
          </label>
          <button
            class="button button-primary assessment-submit-button"
            type="button"
            :disabled="!assessmentFile || assessmentSaving"
            @click="submitAssessment"
          >{{ assessmentSaving ? "正在评估…" : "交给 Agent 评估" }}</button>
        </div>
        <p v-if="assessmentFile" class="assessment-file-name">待评估：{{ assessmentFile.name }}</p>
        <p v-if="assessmentError" class="form-error">{{ assessmentError }}</p>

        <div v-if="taskAssessment" class="assessment-result">
          <p class="assessment-file-name">已评估：{{ taskAssessment.file_name }}</p>
          <p v-if="taskAssessment.submission_truncated" class="assessment-caveat">
            作业文字过长，本次仅评估了开头与结尾的节选；请结合原文复核。
          </p>
          <p class="assessment-summary">{{ taskAssessment.summary }}</p>

          <ol class="assessment-check-list">
            <li v-for="check in taskAssessment.requirement_checks" :key="`${check.requirement}-${check.status}`">
              <div class="assessment-check-title">
                <strong>{{ check.requirement }}</strong>
                <span :class="['assessment-check-status', `check-${check.status}`]">
                  {{ requirementStatusLabels[check.status] || check.status }}
                </span>
              </div>
              <p><b>证据：</b>{{ check.evidence }}</p>
              <p><b>建议：</b>{{ check.recommendation }}</p>
            </li>
          </ol>

          <div v-if="taskAssessment.improvements?.length" class="assessment-notes">
            <strong>优先完善</strong>
            <ul>
              <li v-for="item in taskAssessment.improvements" :key="item">{{ item }}</li>
            </ul>
          </div>
          <p v-if="taskAssessment.limitations?.length" class="assessment-caveat">
            评估边界：{{ taskAssessment.limitations.join("；") }}
          </p>
        </div>
      </section>
    </div>

    <div v-else class="detail-empty">
      <div class="empty-orbit">✦</div>
      <span class="eyebrow">Focus view</span>
      <h2>选择一项任务</h2>
      <p>点击左侧任务卡片，在这里查看完整要求并执行操作。</p>
    </div>
  </aside>
</template>
