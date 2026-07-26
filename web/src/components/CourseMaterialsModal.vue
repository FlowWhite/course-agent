<script setup>
defineProps({
  selectedCourse: { type: Object, default: null },
  courseFiles: { type: Array, required: true },
  filesLoading: { type: Boolean, required: true },
  fileUploading: { type: Boolean, required: true },
  fileError: { type: String, required: true },
  fileSizeLabel: { type: Function, required: true },
  parseStatusLabel: { type: Function, required: true },
})

const emit = defineEmits(["close", "upload", "delete"])
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <section class="modal-card materials-modal" role="dialog" aria-modal="true">
      <div class="modal-header">
        <div><span class="eyebrow">课程资料</span><h2>{{ selectedCourse?.name || "课程资料库" }}</h2></div>
        <button class="icon-button" type="button" @click="emit('close')">×</button>
      </div>
      <label class="file-upload-control">
        <span>{{ fileUploading ? "正在上传并解析…" : "上传 PDF、DOCX、TXT 或 MD（最大 20 MB）" }}</span>
        <input
          type="file"
          accept=".pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"
          :disabled="fileUploading || !selectedCourse"
          @change="emit('upload', $event)"
        />
      </label>
      <p v-if="fileError" class="form-error">{{ fileError }}</p>
      <p v-else-if="filesLoading" class="plan-muted">正在读取课程资料…</p>
      <ul v-else-if="courseFiles.length" class="material-list">
        <li v-for="courseFile in courseFiles" :key="courseFile.id">
          <div>
            <strong>{{ courseFile.original_filename }}</strong>
            <small>{{ courseFile.file_type.toUpperCase() }} · {{ fileSizeLabel(courseFile.file_size) }} · {{ parseStatusLabel(courseFile.parse_status) }}</small>
            <p v-if="courseFile.parse_error" class="material-error">{{ courseFile.parse_error }}</p>
          </div>
          <button class="text-button danger-text" type="button" @click="emit('delete', courseFile)">删除</button>
        </li>
      </ul>
      <p v-else class="plan-muted">还没有课程资料。上传后，Agent 会仅检索相关片段作为参考。</p>
    </section>
  </div>
</template>
