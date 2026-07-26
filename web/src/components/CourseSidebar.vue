<script setup>
defineProps({
  courses: { type: Array, required: true },
  selectedCourseId: { type: String, required: true },
  loading: { type: Boolean, required: true },
  error: { type: String, required: true },
  courseInitials: { type: Function, required: true },
})

const emit = defineEmits(["select"])
</script>

<template>
  <aside class="sidebar">
    <div class="brand-lockup">
      <div class="brand-mark">CA</div>
      <div>
        <strong>Course Agent</strong>
        <span>学习工作台</span>
      </div>
    </div>

    <div class="sidebar-divider"></div>

    <div class="sidebar-section-heading">
      <span>我的课程</span>
      <span class="course-total">{{ courses.length }}</span>
    </div>

    <p v-if="loading" class="sidebar-muted">正在整理课程……</p>
    <p v-else-if="error" class="sidebar-error">{{ error }}</p>
    <nav v-else class="course-nav" aria-label="课程列表">
      <button
        v-for="course in courses"
        :key="course.id"
        :class="['course-nav-item', { active: course.id === selectedCourseId }]"
        type="button"
        @click="emit('select', course.id)"
      >
        <span class="course-avatar">{{ courseInitials(course.name) }}</span>
        <span class="course-nav-copy">
          <strong>{{ course.name }}</strong>
          <small>{{ course.teacher }}</small>
        </span>
        <span class="course-nav-count">{{ course.todo_count }}</span>
      </button>
    </nav>

    <div class="sidebar-footer">
      <span class="connection-dot"></span>
      <span>本地数据已连接</span>
    </div>
  </aside>
</template>
