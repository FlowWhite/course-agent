<script setup>
defineProps({
  selectedCourse: { type: Object, default: null },
  risks: { type: Array, required: true },
  risksLoading: { type: Boolean, required: true },
  risksError: { type: String, required: true },
  riskLevelLabel: { type: Function, required: true },
})

const emit = defineEmits(["close"])
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <section class="modal-card risks-modal" role="dialog" aria-modal="true">
      <div class="modal-header">
        <div><span class="eyebrow">截止日期风险雷达</span><h2>{{ selectedCourse?.name || "全部课程" }}</h2></div>
        <button class="icon-button" type="button" @click="emit('close')">×</button>
      </div>
      <p v-if="risksLoading" class="plan-muted">正在计算风险…</p>
      <p v-else-if="risksError" class="form-error">{{ risksError }}</p>
      <ul v-else-if="risks.length" class="risk-list">
        <li v-for="risk in risks" :key="risk.task_id" :class="`risk-${risk.risk_level}`">
          <div class="risk-level">{{ riskLevelLabel(risk.risk_level) }}</div>
          <div>
            <strong>{{ risk.title }}</strong>
            <small>截止 {{ risk.deadline }} · 剩余 {{ risk.days_remaining }} 天</small>
            <p>{{ risk.reasons.join("；") }}</p>
            <span v-if="risk.sources?.length" class="risk-source">关联资料：{{ risk.sources[0].file_name }}</span>
          </div>
        </li>
      </ul>
      <p v-else class="plan-muted">当前筛选范围内没有待办任务风险。</p>
    </section>
  </div>
</template>
