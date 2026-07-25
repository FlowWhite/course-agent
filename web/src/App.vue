<script setup>
import { computed, onMounted, ref } from "vue"

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000"

const SESSION_STORAGE_KEY = "course-agent-web-session"
const sessionId =
  sessionStorage.getItem(SESSION_STORAGE_KEY) ||
  `web-${Date.now()}`

sessionStorage.setItem(
  SESSION_STORAGE_KEY,
  sessionId
)

const AUTH_STORAGE_KEY =
  "course-agent-access-token"
const accessToken = ref(
  sessionStorage.getItem(AUTH_STORAGE_KEY) || ""
)

const loginForm = ref({
  username: "",
  password: "",
  confirmPassword: "",
})
const authMode = ref("login")
const loginLoading = ref(false)
const loginError = ref("")
const registerLoading = ref(false)
const registerError = ref("")
const authNotice = ref("")

const courses = ref([])
const selectedCourseId = ref("")
const tasks = ref([])
const selectedTaskId = ref("")
const taskFilter = ref("all")

const loading = ref(true)
const tasksLoading = ref(false)
const error = ref("")
const taskError = ref("")
const notice = ref(null)

const formMode = ref(null)
const formSaving = ref(false)
const formError = ref("")
const taskForm = ref(createEmptyForm())

const deleteDialogOpen = ref(false)
const deleteInput = ref("")
const deleteError = ref("")
const deleteSaving = ref(false)

const chatOpen = ref(false)
const chatInput = ref("")
const chatSending = ref(false)
const chatMessagesByCourse = ref({})
const chatMessages = ref([])

const materialsOpen = ref(false)
const courseFiles = ref([])
const filesLoading = ref(false)
const fileUploading = ref(false)
const fileError = ref("")

const risksOpen = ref(false)
const risks = ref([])
const risksLoading = ref(false)
const risksError = ref("")

const taskPlan = ref(null)
const plansLoading = ref(false)
const planSaving = ref(false)
const planError = ref("")

const selectedCourse = computed(() => {
  return courses.value.find(
    (course) => course.id === selectedCourseId.value
  ) || null
})

const selectedTask = computed(() => {
  return tasks.value.find(
    (task) => task.id === selectedTaskId.value
  ) || null
})

function activateCourseAgentChat(courseId = selectedCourseId.value) {
  const course = courses.value.find(
    (item) => item.id === courseId,
  )

  if (!course) {
    chatMessages.value = []
    return
  }

  if (!chatMessagesByCourse.value[course.id]) {
    chatMessagesByCourse.value[course.id] = [
      {
        role: "assistant",
        content:
          `你好，我是“${course.name}”的专属 Agent。` +
          "我只会查询和处理这门课程的任务与资料。",
      },
    ]
  }

  chatMessages.value = chatMessagesByCourse.value[course.id]
}

const filteredTasks = computed(() => {
  if (taskFilter.value === "all") {
    return tasks.value
  }

  return tasks.value.filter(
    (task) => task.status === taskFilter.value
  )
})

const todoCount = computed(() => {
  return tasks.value.filter(
    (task) => task.status === "todo"
  ).length
})

const doneCount = computed(() => {
  return tasks.value.filter(
    (task) => task.status === "done"
  ).length
})

const formTitle = computed(() => {
  return formMode.value === "create"
    ? "新建任务"
    : "编辑任务"
})

const deleteConfirmationText = computed(() => {
  if (!selectedTask.value) {
    return ""
  }

  return `确认删除任务 ${selectedTask.value.id}`
})

function createEmptyForm() {
  return {
    task_id: "",
    course: selectedCourseId.value || "",
    title: "",
    deadline: "",
    priority: "medium",
    description: "",
  }
}

function showNotice(type, message) {
  notice.value = { type, message }

  window.setTimeout(() => {
    if (notice.value?.message === message) {
      notice.value = null
    }
  }, 3600)
}

function saveAccessToken(token) {
  accessToken.value = token

  sessionStorage.setItem(
    AUTH_STORAGE_KEY,
    token,
  )
}

function clearAccessToken() {
  accessToken.value = ""
  sessionStorage.removeItem(AUTH_STORAGE_KEY)
}

function buildRequestHeaders(existingHeaders) {
  const headers = new Headers(existingHeaders || {})

  if (accessToken.value) {
    headers.set(
      "Authorization",
      `Bearer ${accessToken.value}`,
    )
  }

  return headers
}

async function login() {
  loginLoading.value = true
  loginError.value = ""
  authNotice.value = ""

  try {
    const result = await requestJson(
      "/api/v1/auth/login",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: loginForm.value.username,
          password: loginForm.value.password,
        }),
      },
      "登录失败",
    )

    saveAccessToken(result.access_token)
    loginForm.value.password = ""
    chatMessagesByCourse.value = {}
    chatMessages.value = []
    await loadCourses()
  } catch (exception) {
    loginError.value = exception.message
  } finally {
    loginLoading.value = false
  }
}

function switchAuthMode(nextMode) {
  authMode.value = nextMode
  loginError.value = ""
  registerError.value = ""
  authNotice.value = ""
  loginForm.value.password = ""
  loginForm.value.confirmPassword = ""
}

async function register() {
  registerLoading.value = true
  registerError.value = ""
  authNotice.value = ""

  if (
    loginForm.value.password !==
    loginForm.value.confirmPassword
  ) {
    registerError.value = "两次输入的密码不一致"
    registerLoading.value = false
    return
  }

  try {
    const result = await requestJson(
      "/api/v1/auth/register",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: loginForm.value.username,
          password: loginForm.value.password,
        }),
      },
      "注册失败",
    )

    authMode.value = "login"
    loginForm.value.password = ""
    loginForm.value.confirmPassword = ""
    authNotice.value =
      result.message || "注册成功，请登录"
  } catch (exception) {
    registerError.value = exception.message
  } finally {
    registerLoading.value = false
  }
}

function logout() {
  clearAccessToken()
  courses.value = []
  tasks.value = []
  selectedCourseId.value = ""
  selectedTaskId.value = ""
  courseFiles.value = []
  risks.value = []
  taskPlan.value = null
  chatMessagesByCourse.value = {}
  chatMessages.value = []
  chatOpen.value = false
}

function getErrorMessage(result, fallback) {
  if (result?.error) {
    return result.error
  }

  if (Array.isArray(result?.detail)) {
    return result.detail
      .map((item) => item.msg)
      .join("；")
  }

  if (result?.detail) {
    return result.detail
  }

  return fallback
}

async function requestJson(
  path,
  options = {},
  fallback = "请求失败",
) {
  let response

  try {
    const requestOptions = {
      ...options,
      headers: buildRequestHeaders(options.headers),
    }

    response = await fetch(
      `${API_BASE_URL}${path}`,
      requestOptions,
    )
  } catch (exception) {
    throw new Error(
      "无法连接到 API 服务，请确认 FastAPI 正在运行。"
    )
  }

  const result = await response.json().catch(() => null)

  if (response.status === 401) {
    clearAccessToken()

    throw new Error(
      "登录已失效，请重新登录",
    )
  }

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        result,
        `${fallback}（HTTP ${response.status}）`,
      )
    )
  }

  if (result?.success === false) {
    throw new Error(
      getErrorMessage(result, fallback)
    )
  }

  return result?.data ?? result
}

async function loadCourses() {
  loading.value = true
  error.value = ""

  try {
    courses.value = await requestJson(
      "/api/v1/courses",
      {},
      "课程加载失败",
    )

    if (!courses.value.length) {
      selectedCourseId.value = ""
      tasks.value = []
      chatMessagesByCourse.value = {}
      chatMessages.value = []
      return
    }

    const currentCourseExists = courses.value.some(
      (course) => course.id === selectedCourseId.value
    )

    if (!currentCourseExists) {
      selectedCourseId.value = courses.value[0].id
    }

    activateCourseAgentChat(selectedCourseId.value)

    await Promise.all([
      loadTasks(selectedCourseId.value),
      loadCourseFiles(selectedCourseId.value),
      loadRisks(selectedCourseId.value),
    ])
  } catch (exception) {
    error.value = exception.message
  } finally {
    loading.value = false
  }
}

async function selectCourse(courseId) {
  selectedCourseId.value = courseId
  selectedTaskId.value = ""
  taskFilter.value = "all"
  taskPlan.value = null
  chatInput.value = ""
  activateCourseAgentChat(courseId)
  await Promise.all([
    loadTasks(courseId),
    loadCourseFiles(courseId),
    loadRisks(courseId),
  ])
}

async function loadTasks(courseId) {
  if (!courseId) {
    tasks.value = []
    return
  }

  tasksLoading.value = true
  taskError.value = ""
  selectedTaskId.value = ""

  try {
    const params = new URLSearchParams({
      course: courseId,
      status: "all",
    })

    tasks.value = await requestJson(
      `/api/v1/tasks?${params.toString()}`,
      {},
      "任务加载失败",
    )
  } catch (exception) {
    taskError.value = exception.message
    tasks.value = []
  } finally {
    tasksLoading.value = false
  }
}

async function loadTaskDetail(taskId) {
  selectedTaskId.value = taskId

  try {
    const task = await requestJson(
      `/api/v1/tasks/${encodeURIComponent(taskId)}`,
      {},
      "任务详情加载失败",
    )

    replaceTask(task)
    await loadTaskPlans(task.id)
  } catch (exception) {
    showNotice("error", exception.message)
  }
}

function replaceTask(nextTask) {
  const taskIndex = tasks.value.findIndex(
    (task) => task.id === nextTask.id
  )

  if (taskIndex === -1) {
    tasks.value.push(nextTask)
    return
  }

  tasks.value[taskIndex] = nextTask
}

async function loadCourseFiles(courseId = selectedCourseId.value) {
  if (!courseId) {
    courseFiles.value = []
    return
  }

  filesLoading.value = true
  fileError.value = ""
  try {
    const params = new URLSearchParams({ course_id: courseId })
    courseFiles.value = await requestJson(
      `/api/v1/files?${params.toString()}`,
      {},
      "课程资料加载失败",
    )
  } catch (exception) {
    fileError.value = exception.message
  } finally {
    filesLoading.value = false
  }
}

async function uploadCourseFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ""
  if (!file || !selectedCourseId.value || fileUploading.value) {
    return
  }

  const formData = new FormData()
  formData.append("course_id", selectedCourseId.value)
  formData.append("file", file)
  fileUploading.value = true
  fileError.value = ""
  try {
    const uploaded = await requestJson(
      "/api/v1/files",
      { method: "POST", body: formData },
      "课程资料上传失败",
    )
    courseFiles.value.unshift(uploaded)
    showNotice(
      uploaded.parse_status === "parsed" ? "success" : "error",
      uploaded.parse_status === "parsed"
        ? "课程资料已上传并完成解析。"
        : `文件已保存，但解析失败：${uploaded.parse_error || "请检查文件。"}`,
    )
  } catch (exception) {
    fileError.value = exception.message
  } finally {
    fileUploading.value = false
  }
}

async function deleteCourseFile(courseFile) {
  const confirmation = window.prompt(
    `要删除“${courseFile.original_filename}”吗？\n请输入：确认删除文件 ${courseFile.id}`,
  )
  if (confirmation === null) {
    return
  }

  try {
    await requestJson(
      `/api/v1/files/${encodeURIComponent(courseFile.id)}`,
      {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmation: confirmation.trim() }),
      },
      "课程资料删除失败",
    )
    courseFiles.value = courseFiles.value.filter(
      (item) => item.id !== courseFile.id,
    )
    showNotice("success", "课程资料已删除。")
  } catch (exception) {
    fileError.value = exception.message
  }
}

async function loadRisks(courseId = selectedCourseId.value) {
  risksLoading.value = true
  risksError.value = ""
  try {
    const params = new URLSearchParams()
    if (courseId) {
      params.set("course_id", courseId)
    }
    risks.value = await requestJson(
      `/api/v1/insights/risks?${params.toString()}`,
      {},
      "风险雷达加载失败",
    )
  } catch (exception) {
    risksError.value = exception.message
  } finally {
    risksLoading.value = false
  }
}

async function loadTaskPlans(taskId) {
  plansLoading.value = true
  planError.value = ""
  try {
    const params = new URLSearchParams({ task_id: taskId })
    const plans = await requestJson(
      `/api/v1/plans?${params.toString()}`,
      {},
      "学习计划加载失败",
    )
    taskPlan.value = plans.find(
      (plan) => !["completed", "cancelled"].includes(plan.status),
    ) || plans[0] || null
  } catch (exception) {
    planError.value = exception.message
  } finally {
    plansLoading.value = false
  }
}

async function generateTaskPlan() {
  if (!selectedTask.value || planSaving.value) {
    return
  }
  planSaving.value = true
  planError.value = ""
  try {
    taskPlan.value = await requestJson(
      `/api/v1/tasks/${encodeURIComponent(selectedTask.value.id)}/plan`,
      { method: "POST" },
      "学习计划草案生成失败",
    )
    showNotice("success", "已生成学习计划草案，请确认后再启动。")
  } catch (exception) {
    planError.value = exception.message
  } finally {
    planSaving.value = false
  }
}

async function changePlanState(action, stepId = "") {
  if (!taskPlan.value || planSaving.value) {
    return
  }
  planSaving.value = true
  planError.value = ""
  const suffix = action === "complete"
    ? `/steps/${encodeURIComponent(stepId)}/complete`
    : `/${action}`
  try {
    taskPlan.value = await requestJson(
      `/api/v1/plans/${encodeURIComponent(taskPlan.value.id)}${suffix}`,
      { method: "POST" },
      "学习计划状态更新失败",
    )
    await loadRisks()
  } catch (exception) {
    planError.value = exception.message
  } finally {
    planSaving.value = false
  }
}

async function updateTaskStatus(taskId, nextStatus) {
  const previousTask = tasks.value.find(
    (task) => task.id === taskId
  )

  try {
    const task = await requestJson(
      `/api/v1/tasks/${encodeURIComponent(taskId)}/status`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          status: nextStatus,
        }),
      },
      "任务状态更新失败",
    )

    replaceTask(task)
    selectedTaskId.value = task.id

    if (
      previousTask &&
      previousTask.status !== task.status
    ) {
      const course = courses.value.find(
        (item) => item.id === task.course_id
      )

      if (course) {
        const delta = task.status === "todo"
          ? 1
          : -1

        course.todo_count = Math.max(
          0,
          course.todo_count + delta,
        )
      }
    }

    showNotice(
      "success",
      nextStatus === "done"
        ? "任务已标记为完成。"
        : "任务已恢复为未完成。",
    )
  } catch (exception) {
    showNotice("error", exception.message)
  }
}

function openCreate() {
  formMode.value = "create"
  formError.value = ""
  taskForm.value = {
    ...createEmptyForm(),
    course: selectedCourseId.value,
  }
}

function openEdit() {
  if (!selectedTask.value) {
    return
  }

  formMode.value = "edit"
  formError.value = ""
  taskForm.value = {
    task_id: selectedTask.value.id,
    course: selectedTask.value.course_id,
    title: selectedTask.value.title,
    deadline: selectedTask.value.deadline,
    priority: selectedTask.value.priority,
    description: selectedTask.value.description,
  }
}

function closeForm() {
  if (formSaving.value) {
    return
  }

  formMode.value = null
  formError.value = ""
}

async function submitTaskForm() {
  formSaving.value = true
  formError.value = ""

  try {
    let task
    const wasCreating = formMode.value === "create"

    if (wasCreating) {
      task = await requestJson(
        "/api/v1/tasks",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            task_id: taskForm.value.task_id,
            course: taskForm.value.course,
            title: taskForm.value.title,
            deadline: taskForm.value.deadline,
            priority: taskForm.value.priority,
            description: taskForm.value.description,
          }),
        },
        "任务创建失败",
      )
    } else {
      task = await requestJson(
        `/api/v1/tasks/${encodeURIComponent(taskForm.value.task_id)}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            title: taskForm.value.title,
            deadline: taskForm.value.deadline,
            priority: taskForm.value.priority,
            description: taskForm.value.description,
          }),
        },
        "任务修改失败",
      )
    }

    formMode.value = null
    selectedCourseId.value = task.course_id
    await loadCourses()
    selectedTaskId.value = task.id
    replaceTask(task)

    showNotice(
      "success",
      wasCreating
        ? "任务已创建。"
        : "任务已更新。",
    )
  } catch (exception) {
    formError.value = exception.message
  } finally {
    formSaving.value = false
  }
}

function openDeleteDialog() {
  if (!selectedTask.value) {
    return
  }

  deleteDialogOpen.value = true
  deleteInput.value = ""
  deleteError.value = ""
}

function closeDeleteDialog() {
  if (deleteSaving.value) {
    return
  }

  deleteDialogOpen.value = false
  deleteInput.value = ""
  deleteError.value = ""
}

async function confirmDelete() {
  if (!selectedTask.value) {
    return
  }

  if (
    deleteInput.value.trim() !==
    deleteConfirmationText.value
  ) {
    deleteError.value =
      `请输入：${deleteConfirmationText.value}`
    return
  }

  deleteSaving.value = true
  deleteError.value = ""

  try {
    await requestJson(
      `/api/v1/tasks/${encodeURIComponent(selectedTask.value.id)}`,
      {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          confirmation: deleteInput.value.trim(),
        }),
      },
      "任务删除失败",
    )

    const deletedTitle = selectedTask.value.title
    selectedTaskId.value = ""
    closeDeleteDialog()
    await loadCourses()

    showNotice(
      "success",
      `“${deletedTitle}”已删除，删除前数据库已备份。`,
    )
  } catch (exception) {
    deleteError.value = exception.message
  } finally {
    deleteSaving.value = false
  }
}

function toggleChat() {
  if (!chatOpen.value) {
    activateCourseAgentChat()
  }
  chatOpen.value = !chatOpen.value
}

async function sendChat() {
  const message = chatInput.value.trim()
  const course = selectedCourse.value

  if (!message || !course || chatSending.value) {
    return
  }

  activateCourseAgentChat(course.id)
  const messages = chatMessagesByCourse.value[course.id]
  messages.push({
    role: "user",
    content: message,
  })
  chatInput.value = ""
  chatSending.value = true

  try {
    const data = await requestJson(
      "/api/v1/chat",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: sessionId,
          course_id: course.id,
          message,
        }),
      },
      "Agent 请求失败",
    )

    messages.push({
      role: "assistant",
      content: data.reply,
    })
  } catch (exception) {
    messages.push({
      role: "assistant",
      content: `请求失败：${exception.message}`,
    })
  } finally {
    chatSending.value = false
  }
}

function statusLabel(status) {
  return status === "todo" ? "未完成" : "已完成"
}

function priorityLabel(priority) {
  const labels = {
    high: "高",
    medium: "中",
    low: "低",
  }

  return labels[priority] || priority
}

function courseInitials(name) {
  return name?.slice(0, 2) || "课"
}

function priorityClass(priority) {
  return `priority-${priority}`
}

function fileSizeLabel(size) {
  if (size < 1024 * 1024) {
    return `${Math.max(1, Math.round(size / 1024))} KB`
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function parseStatusLabel(status) {
  const labels = {
    pending: "等待解析",
    parsing: "正在解析",
    parsed: "已解析",
    failed: "解析失败",
  }
  return labels[status] || status
}

function planStatusLabel(status) {
  const labels = {
    awaiting_confirmation: "等待确认",
    active: "进行中",
    paused: "已暂停",
    completed: "已完成",
    cancelled: "已取消",
    draft: "草案",
  }
  return labels[status] || status
}

function riskLevelLabel(level) {
  const labels = {
    low: "低风险",
    medium: "中风险",
    high: "高风险",
    critical: "紧急",
  }
  return labels[level] || level
}

onMounted(() => {
  if (accessToken.value) {
    loadCourses()
  }
})
</script>

<template>
  <div
    v-if="!accessToken"
    class="auth-shell"
  >
    <section class="auth-card">
      <div class="brand-mark auth-brand-mark">CA</div>
      <p class="auth-eyebrow">COURSE AGENT</p>
      <h1>登录课程工作台</h1>
      <p class="auth-subtitle">
        登录后查看课程、任务和 Agent 对话。
      </p>

      <p
        v-if="authNotice"
        class="auth-success"
        role="status"
      >
        {{ authNotice }}
      </p>

      <form
        v-if="authMode === 'login'"
        class="auth-form"
        @submit.prevent="login"
      >
        <label>
          <span>用户名</span>
          <input
            v-model="loginForm.username"
            type="text"
            autocomplete="username"
            placeholder="请输入用户名"
            required
          />
        </label>

        <label>
          <span>密码</span>
          <input
            v-model="loginForm.password"
            type="password"
            autocomplete="current-password"
            placeholder="请输入密码"
            required
          />
        </label>

        <p
          v-if="loginError"
          class="form-error"
          role="alert"
        >
          {{ loginError }}
        </p>

        <button
          class="button button-primary auth-submit"
          type="submit"
          :disabled="loginLoading"
        >
          {{ loginLoading ? "登录中..." : "登录" }}
        </button>
      </form>

      <form
        v-else
        class="auth-form"
        @submit.prevent="register"
      >
        <label>
          <span>用户名</span>
          <input
            v-model="loginForm.username"
            type="text"
            autocomplete="username"
            placeholder="请输入用户名"
            required
          />
        </label>

        <label>
          <span>密码</span>
          <input
            v-model="loginForm.password"
            type="password"
            autocomplete="new-password"
            placeholder="请输入至少 8 位密码"
            minlength="8"
            required
          />
        </label>

        <label>
          <span>确认密码</span>
          <input
            v-model="loginForm.confirmPassword"
            type="password"
            autocomplete="new-password"
            placeholder="请再次输入密码"
            minlength="8"
            required
          />
        </label>

        <p
          v-if="registerError"
          class="form-error"
          role="alert"
        >
          {{ registerError }}
        </p>

        <button
          class="button button-primary auth-submit"
          type="submit"
          :disabled="registerLoading"
        >
          {{ registerLoading ? "注册中..." : "注册" }}
        </button>
      </form>

      <button
        class="auth-switch"
        type="button"
        @click="switchAuthMode(
          authMode === 'login' ? 'register' : 'login'
        )"
      >
        {{
          authMode === "login"
            ? "还没有账号？去注册"
            : "已有账号？返回登录"
        }}
      </button>
    </section>
  </div>

  <div v-else class="app-shell">
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
        <span class="course-total">
          {{ courses.length }}
        </span>
      </div>

      <p v-if="loading" class="sidebar-muted">
        正在整理课程……
      </p>

      <p v-else-if="error" class="sidebar-error">
        {{ error }}
      </p>

      <nav v-else class="course-nav" aria-label="课程列表">
        <button
          v-for="course in courses"
          :key="course.id"
          :class="[
            'course-nav-item',
            {
              active: course.id === selectedCourseId,
            },
          ]"
          type="button"
          @click="selectCourse(course.id)"
        >
          <span class="course-avatar">
            {{ courseInitials(course.name) }}
          </span>
          <span class="course-nav-copy">
            <strong>{{ course.name }}</strong>
            <small>{{ course.teacher }}</small>
          </span>
          <span class="course-nav-count">
            {{ course.todo_count }}
          </span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <span class="connection-dot"></span>
        <span>本地数据已连接</span>
      </div>
    </aside>

    <main class="workspace">
      <header class="topbar">
        <div class="breadcrumb">
          <span>课程工作台</span>
          <span class="breadcrumb-slash">/</span>
          <strong>今日计划</strong>
        </div>

        <div class="topbar-actions">
          <button
            class="button button-secondary"
            type="button"
            :disabled="!selectedCourse"
            @click="materialsOpen = true"
          >
            <span class="button-glyph">▤</span>
            课程资料
          </button>

          <button
            class="button button-secondary"
            type="button"
            @click="risksOpen = true"
          >
            <span class="button-glyph">◈</span>
            风险雷达
          </button>

          <button
            class="button button-secondary"
            type="button"
            :disabled="!selectedCourse"
            @click="toggleChat"
          >
            <span class="button-glyph">✦</span>
            问本课程 Agent
          </button>

          <button
            class="button button-primary"
            type="button"
            :disabled="!selectedCourse"
            @click="openCreate"
          >
            <span class="button-glyph">＋</span>
            新建任务
          </button>
          <button
            class="button button-secondary"
            type="button"
            @click="logout"
          >
            退出登录
          </button>
        </div>
      </header>

      <section class="hero-panel">
        <div class="hero-copy">
          <span class="eyebrow">
            {{ selectedCourse?.id || "COURSE DESK" }}
          </span>
          <h1>
            {{ selectedCourse?.name || "课程与项目管理" }}
          </h1>
          <p>
            把今天要推进的事情放在眼前，先完成最重要的一件。
          </p>
        </div>

        <div class="hero-stat">
          <span>当前课程待办</span>
          <strong>{{ todoCount }}</strong>
          <small>
            {{ selectedCourse?.teacher || "等待课程数据" }}
          </small>
        </div>
      </section>

      <div
        v-if="notice"
        :class="['notice', `notice-${notice.type}`]"
        role="status"
      >
        <span>{{ notice.type === "success" ? "✓" : "!" }}</span>
        {{ notice.message }}
      </div>

      <section class="workspace-grid">
        <div class="task-column">
          <div class="section-heading">
            <div>
              <span class="eyebrow">任务清单</span>
              <h2>
                {{ selectedCourse?.name || "选择一门课程" }}
              </h2>
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
                { value: 'all', label: '全部' },
                { value: 'todo', label: '待完成' },
                { value: 'done', label: '已完成' },
              ]"
              :key="filter.value"
              :class="[
                'filter-button',
                { active: taskFilter === filter.value },
              ]"
              type="button"
              role="tab"
              :aria-selected="taskFilter === filter.value"
              @click="taskFilter = filter.value"
            >
              {{ filter.label }}
            </button>
          </div>

          <p v-if="tasksLoading" class="state-message">
            正在加载任务……
          </p>

          <p v-else-if="taskError" class="state-message error-text">
            {{ taskError }}
          </p>

          <div
            v-else-if="filteredTasks.length"
            class="task-list"
          >
            <article
              v-for="task in filteredTasks"
              :key="task.id"
              :class="[
                'task-card',
                {
                  selected: task.id === selectedTaskId,
                },
              ]"
              role="button"
              tabindex="0"
              @click="loadTaskDetail(task.id)"
              @keydown.enter="loadTaskDetail(task.id)"
              @keydown.space.prevent="loadTaskDetail(task.id)"
            >
              <div class="task-card-topline">
                <span
                  :class="[
                    'status-marker',
                    `status-${task.status}`,
                  ]"
                ></span>
                <span class="task-status-label">
                  {{ statusLabel(task.status) }}
                </span>
                <span
                  :class="[
                    'priority-chip',
                    priorityClass(task.priority),
                  ]"
                >
                  {{ priorityLabel(task.priority) }}优先级
                </span>
              </div>

              <h3>{{ task.title }}</h3>
              <p class="task-description">
                {{ task.description }}
              </p>

              <div class="task-card-footer">
                <span>截止 {{ task.deadline }}</span>
                <span class="task-arrow">↗</span>
              </div>
            </article>
          </div>

          <div v-else class="empty-state">
            <span class="empty-mark">○</span>
            <strong>
              {{ taskFilter === "all" ? "还没有任务" : "没有匹配的任务" }}
            </strong>
            <p>
              {{ taskFilter === "all"
                ? "从一个小任务开始，把计划落到今天。"
                : "试试切换上方的筛选条件。" }}
            </p>
            <button
              v-if="taskFilter === 'all' && selectedCourse"
              class="button button-primary"
              type="button"
              @click="openCreate"
            >
              新建第一个任务
            </button>
          </div>
        </div>

        <aside class="detail-column">
          <div v-if="selectedTask" class="detail-card">
            <div class="detail-card-heading">
              <div>
                <span class="eyebrow">任务详情</span>
                <h2>{{ selectedTask.title }}</h2>
              </div>
              <span
                :class="[
                  'detail-status-badge',
                  `status-${selectedTask.status}`,
                ]"
              >
                {{ statusLabel(selectedTask.status) }}
              </span>
            </div>

            <div class="detail-facts">
              <div>
                <span>课程</span>
                <strong>{{ selectedTask.course_name }}</strong>
              </div>
              <div>
                <span>截止日期</span>
                <strong>{{ selectedTask.deadline }}</strong>
              </div>
              <div>
                <span>优先级</span>
                <strong>{{ priorityLabel(selectedTask.priority) }}</strong>
              </div>
              <div>
                <span>任务 ID</span>
                <strong class="mono-text">{{ selectedTask.id }}</strong>
              </div>
            </div>

            <div class="detail-requirement">
              <span>具体要求</span>
              <p>{{ selectedTask.description }}</p>
            </div>

            <section class="plan-panel">
              <div class="plan-heading">
                <div class="plan-heading-copy">
                  <span>学习计划</span>
                  <strong v-if="taskPlan">
                    {{ planStatusLabel(taskPlan.status) }}
                  </strong>
                  <p v-else-if="selectedTask.status === 'todo'" class="plan-heading-hint">
                    根据任务和课程资料，生成可确认的执行步骤
                  </p>
                </div>
                <button
                  v-if="!taskPlan && selectedTask.status === 'todo'"
                  class="button button-primary plan-generate-button"
                  type="button"
                  :disabled="planSaving"
                  @click="generateTaskPlan"
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
                    @click="changePlanState('confirm')"
                  >
                    确认并启动计划
                  </button>
                  <button
                    v-else-if="taskPlan.status === 'active'"
                    class="button button-secondary button-wide"
                    type="button"
                    :disabled="planSaving"
                    @click="changePlanState('pause')"
                  >
                    暂停计划
                  </button>
                  <button
                    v-else-if="taskPlan.status === 'paused'"
                    class="button button-primary button-wide"
                    type="button"
                    :disabled="planSaving"
                    @click="changePlanState('resume')"
                  >
                    恢复计划
                  </button>
                </div>
              </template>

              <p v-else class="plan-muted">
                生成计划后，确认才会启动；它不会修改任务状态。
              </p>
            </section>

            <div class="detail-actions">
              <button
                class="button button-primary button-wide"
                type="button"
                @click="updateTaskStatus(
                  selectedTask.id,
                  selectedTask.status === 'todo' ? 'done' : 'todo'
                )"
              >
                {{ selectedTask.status === "todo"
                  ? "标记为已完成"
                  : "恢复为未完成" }}
              </button>
              <button
                class="button button-secondary button-wide"
                type="button"
                @click="openEdit"
              >
                编辑任务
              </button>
              <button
                class="text-button danger-text"
                type="button"
                @click="openDeleteDialog"
              >
                删除任务
              </button>
            </div>
          </div>

          <div v-else class="detail-empty">
            <div class="empty-orbit">✦</div>
            <span class="eyebrow">Focus view</span>
            <h2>选择一项任务</h2>
            <p>
              点击左侧任务卡片，在这里查看完整要求并执行操作。
            </p>
          </div>
        </aside>
      </section>
    </main>

    <aside
      v-if="chatOpen"
      class="chat-drawer"
      aria-label="Agent 对话"
    >
      <div class="chat-header">
        <div>
          <span class="eyebrow">{{ selectedCourse?.id || "Course Agent" }}</span>
          <h2>{{ selectedCourse?.name || "课程 Agent" }}</h2>
          <p class="chat-scope">仅访问当前课程的任务与资料</p>
        </div>
        <button
          class="icon-button"
          type="button"
          aria-label="关闭对话"
          @click="toggleChat"
        >
          ×
        </button>
      </div>

      <div class="chat-messages" aria-live="polite">
        <div
          v-for="(message, index) in chatMessages"
          :key="`${message.role}-${index}`"
          :class="[
            'chat-message',
            `message-${message.role}`,
          ]"
        >
          <span class="message-role">
            {{ message.role === "user" ? "你" : "Agent" }}
          </span>
          <p>{{ message.content }}</p>
        </div>

        <div v-if="chatSending" class="chat-message message-assistant">
          <span class="message-role">Agent</span>
          <p class="typing-dots">正在思考……</p>
        </div>
      </div>

      <form class="chat-composer" @submit.prevent="sendChat">
        <textarea
          v-model="chatInput"
          rows="3"
          :placeholder="selectedCourse
            ? `例如：${selectedCourse.name}有哪些待完成任务？`
            : '请先选择课程'"
          :disabled="!selectedCourse"
          @keydown.enter.exact.prevent="sendChat"
        ></textarea>
        <button
          class="button button-primary"
          type="submit"
          :disabled="chatSending || !selectedCourse || !chatInput.trim()"
        >
          发送
        </button>
      </form>
    </aside>

    <div
      v-if="materialsOpen"
      class="modal-backdrop"
      @click.self="materialsOpen = false"
    >
      <section class="modal-card materials-modal" role="dialog" aria-modal="true">
        <div class="modal-header">
          <div>
            <span class="eyebrow">课程资料</span>
            <h2>{{ selectedCourse?.name || "课程资料库" }}</h2>
          </div>
          <button class="icon-button" type="button" @click="materialsOpen = false">
            ×
          </button>
        </div>

        <label class="file-upload-control">
          <span>{{ fileUploading ? "正在上传并解析…" : "上传 PDF、DOCX、TXT 或 MD（最大 20 MB）" }}</span>
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"
            :disabled="fileUploading || !selectedCourse"
            @change="uploadCourseFile"
          />
        </label>

        <p v-if="fileError" class="form-error">{{ fileError }}</p>
        <p v-else-if="filesLoading" class="plan-muted">正在读取课程资料…</p>
        <ul v-else-if="courseFiles.length" class="material-list">
          <li v-for="courseFile in courseFiles" :key="courseFile.id">
            <div>
              <strong>{{ courseFile.original_filename }}</strong>
              <small>
                {{ courseFile.file_type.toUpperCase() }} ·
                {{ fileSizeLabel(courseFile.file_size) }} ·
                {{ parseStatusLabel(courseFile.parse_status) }}
              </small>
              <p v-if="courseFile.parse_error" class="material-error">
                {{ courseFile.parse_error }}
              </p>
            </div>
            <button class="text-button danger-text" type="button" @click="deleteCourseFile(courseFile)">
              删除
            </button>
          </li>
        </ul>
        <p v-else class="plan-muted">
          还没有课程资料。上传后，Agent 会仅检索相关片段作为参考。
        </p>
      </section>
    </div>

    <div
      v-if="risksOpen"
      class="modal-backdrop"
      @click.self="risksOpen = false"
    >
      <section class="modal-card risks-modal" role="dialog" aria-modal="true">
        <div class="modal-header">
          <div>
            <span class="eyebrow">截止日期风险雷达</span>
            <h2>{{ selectedCourse?.name || "全部课程" }}</h2>
          </div>
          <button class="icon-button" type="button" @click="risksOpen = false">
            ×
          </button>
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
              <span v-if="risk.sources?.length" class="risk-source">
                关联资料：{{ risk.sources[0].file_name }}
              </span>
            </div>
          </li>
        </ul>
        <p v-else class="plan-muted">当前筛选范围内没有待办任务风险。</p>
      </section>
    </div>

    <div
      v-if="formMode"
      class="modal-backdrop"
      @click.self="closeForm"
    >
      <form
        class="modal-card"
        @submit.prevent="submitTaskForm"
      >
        <div class="modal-header">
          <div>
            <span class="eyebrow">任务管理</span>
            <h2>{{ formTitle }}</h2>
          </div>
          <button
            class="icon-button"
            type="button"
            aria-label="关闭表单"
            @click="closeForm"
          >
            ×
          </button>
        </div>

        <label v-if="formMode === 'create'" class="form-field">
          <span>任务 ID</span>
          <input
            v-model.trim="taskForm.task_id"
            required
            placeholder="例如：os-lab-2"
          />
        </label>

        <label v-if="formMode === 'create'" class="form-field">
          <span>所属课程</span>
          <select v-model="taskForm.course" required>
            <option value="" disabled>选择课程</option>
            <option
              v-for="course in courses"
              :key="course.id"
              :value="course.id"
            >
              {{ course.name }}
            </option>
          </select>
        </label>

        <label v-else class="form-field">
          <span>任务 ID</span>
          <input :value="taskForm.task_id" disabled />
        </label>

        <label class="form-field">
          <span>任务标题</span>
          <input
            v-model.trim="taskForm.title"
            required
            placeholder="例如：完成实验报告"
          />
        </label>

        <div class="form-row">
          <label class="form-field">
            <span>截止日期</span>
            <input
              v-model="taskForm.deadline"
              type="date"
              required
            />
          </label>

          <label class="form-field">
            <span>优先级</span>
            <select v-model="taskForm.priority" required>
              <option value="high">高</option>
              <option value="medium">中</option>
              <option value="low">低</option>
            </select>
          </label>
        </div>

        <label class="form-field">
          <span>具体要求</span>
          <textarea
            v-model.trim="taskForm.description"
            rows="5"
            required
            placeholder="写下完成标准或提交要求"
          ></textarea>
        </label>

        <p v-if="formError" class="form-error" role="alert">
          {{ formError }}
        </p>

        <div class="modal-actions">
          <button
            class="button button-secondary"
            type="button"
            :disabled="formSaving"
            @click="closeForm"
          >
            取消
          </button>
          <button
            class="button button-primary"
            type="submit"
            :disabled="formSaving"
          >
            {{ formSaving ? "正在保存……" : "保存任务" }}
          </button>
        </div>
      </form>
    </div>

    <div
      v-if="deleteDialogOpen"
      class="modal-backdrop"
      @click.self="closeDeleteDialog"
    >
      <section class="modal-card danger-modal" role="dialog" aria-modal="true">
        <div class="modal-header">
          <div>
            <span class="eyebrow danger-text">不可逆操作</span>
            <h2>删除任务？</h2>
          </div>
          <button
            class="icon-button"
            type="button"
            aria-label="关闭删除确认"
            @click="closeDeleteDialog"
          >
            ×
          </button>
        </div>

        <p class="danger-copy">
          删除前会自动备份业务数据库，但任务本身将从当前数据中移除。
        </p>

        <p class="confirmation-hint">
          请输入：
          <code>{{ deleteConfirmationText }}</code>
        </p>

        <input
          v-model="deleteInput"
          class="confirmation-input"
          autocomplete="off"
          placeholder="输入确认文本"
          @keyup.enter="confirmDelete"
        />

        <p v-if="deleteError" class="form-error" role="alert">
          {{ deleteError }}
        </p>

        <div class="modal-actions">
          <button
            class="button button-secondary"
            type="button"
            :disabled="deleteSaving"
            @click="closeDeleteDialog"
          >
            取消
          </button>
          <button
            class="button button-danger"
            type="button"
            :disabled="deleteSaving"
            @click="confirmDelete"
          >
            {{ deleteSaving ? "正在删除……" : "确认删除" }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.auth-shell {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at top left, #f8c9b9 0, transparent 34%),
    #f4efe6;
}

.auth-card {
  width: min(100%, 420px);
  padding: 42px;
  border: 1px solid rgb(31 42 56 / 10%);
  border-radius: 24px;
  background: rgb(255 252 247 / 92%);
  box-shadow: 0 24px 70px rgb(31 42 56 / 14%);
}

.auth-brand-mark {
  width: 52px;
  height: 52px;
  margin-bottom: 24px;
}

.auth-eyebrow {
  margin: 0 0 8px;
  color: #bd5f4b;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.16em;
}

.auth-card h1 {
  margin: 0;
  color: #1f2a38;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(2rem, 5vw, 2.7rem);
}

.auth-subtitle {
  margin: 12px 0 28px;
  color: #687585;
  line-height: 1.7;
}

.auth-success {
  margin: 0 0 18px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #e9f5ed;
  color: #2e7650;
  font-size: 0.88rem;
}

.auth-form {
  display: grid;
  gap: 18px;
}

.auth-form label {
  display: grid;
  gap: 8px;
  color: #344454;
  font-size: 0.86rem;
  font-weight: 700;
}

.auth-form input {
  width: 100%;
  box-sizing: border-box;
  padding: 12px 14px;
  border: 1px solid #d9d3c9;
  border-radius: 10px;
  background: #fffdf9;
  color: #1f2933;
  font: inherit;
}

.auth-form input:focus {
  border-color: #bd5f4b;
  outline: 3px solid rgb(189 95 75 / 16%);
}

.auth-submit {
  width: 100%;
  justify-content: center;
  margin-top: 4px;
}

.auth-switch {
  display: block;
  width: 100%;
  margin-top: 18px;
  border: 0;
  background: transparent;
  color: #bd5f4b;
  cursor: pointer;
  font: inherit;
  font-size: 0.88rem;
  font-weight: 700;
}

.auth-switch:hover,
.auth-switch:focus-visible {
  color: #8f4335;
  text-decoration: underline;
}

.app-shell {
  display: flex;
  min-height: 100vh;
  background: #f4efe6;
  color: #1f2933;
}

.sidebar {
  display: flex;
  width: 270px;
  flex: 0 0 270px;
  flex-direction: column;
  padding: 28px 18px 20px;
  background: #1f2a38;
  color: #f8f4eb;
}

.brand-lockup {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 10px;
}

.brand-mark {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 12px;
  background: #ed795f;
  color: #fff8ef;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.brand-lockup strong,
.brand-lockup span {
  display: block;
}

.brand-lockup strong {
  color: #fff8ef;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 1.12rem;
}

.brand-lockup span {
  margin-top: 2px;
  color: #aeb9c6;
  font-size: 0.75rem;
}

.sidebar-divider {
  height: 1px;
  margin: 30px 10px 22px;
  background: rgb(255 255 255 / 13%);
}

.sidebar-section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;
  color: #aeb9c6;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.course-total {
  display: grid;
  min-width: 22px;
  height: 22px;
  place-items: center;
  border: 1px solid rgb(255 255 255 / 17%);
  border-radius: 50%;
  color: #f8c9b9;
  font-size: 0.7rem;
}

.course-nav {
  display: grid;
  gap: 7px;
  margin-top: 14px;
}

.course-nav-item {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.course-nav-item:hover,
.course-nav-item:focus-visible,
.course-nav-item.active {
  border-color: rgb(255 255 255 / 13%);
  background: rgb(255 255 255 / 9%);
  outline: none;
}

.course-avatar {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  place-items: center;
  border-radius: 10px;
  background: #3c5266;
  color: #f8c9b9;
  font-size: 0.75rem;
  font-weight: 800;
}

.course-nav-item.active .course-avatar {
  background: #ed795f;
  color: #fff8ef;
}

.course-nav-copy {
  min-width: 0;
  flex: 1;
}

.course-nav-copy strong,
.course-nav-copy small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.course-nav-copy strong {
  color: #f8f4eb;
  font-size: 0.89rem;
}

.course-nav-copy small {
  margin-top: 3px;
  color: #97a5b5;
  font-size: 0.72rem;
}

.course-nav-count {
  color: #f8c9b9;
  font-size: 0.78rem;
  font-weight: 800;
}

.sidebar-muted,
.sidebar-error {
  padding: 20px 10px;
  color: #aeb9c6;
  font-size: 0.84rem;
}

.sidebar-error {
  color: #f8c9b9;
}

.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: auto;
  padding: 16px 10px 0;
  border-top: 1px solid rgb(255 255 255 / 13%);
  color: #aeb9c6;
  font-size: 0.74rem;
}

.connection-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #83b49a;
  box-shadow: 0 0 0 4px rgb(131 180 154 / 13%);
}

.workspace {
  min-width: 0;
  flex: 1;
  padding: 24px clamp(22px, 4vw, 64px) 64px;
}

.topbar,
.topbar-actions,
.breadcrumb,
.detail-actions,
.modal-actions {
  display: flex;
  align-items: center;
}

.topbar {
  justify-content: space-between;
  gap: 18px;
}

.breadcrumb {
  gap: 10px;
  color: #7f8992;
  font-size: 0.78rem;
}

.breadcrumb strong {
  color: #263442;
}

.breadcrumb-slash {
  color: #b8aa99;
}

.topbar-actions {
  gap: 10px;
}

.button,
.text-button,
.icon-button {
  border: 0;
  font: inherit;
}

.button {
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 16px;
  border-radius: 9px;
  cursor: pointer;
  font-size: 0.83rem;
  font-weight: 800;
  transition:
    background 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.button:focus-visible,
.text-button:focus-visible,
.icon-button:focus-visible {
  outline: 3px solid rgb(237 121 95 / 35%);
  outline-offset: 2px;
}

.button:disabled {
  cursor: not-allowed;
  opacity: 0.52;
}

.button-primary {
  background: #ed795f;
  color: #fff8ef;
  box-shadow: 0 7px 16px rgb(196 85 64 / 18%);
}

.button-primary:hover:not(:disabled) {
  background: #d9644d;
}

.button-secondary {
  border: 1px solid #d5c8b9;
  background: rgb(255 252 246 / 78%);
  color: #334355;
}

.button-secondary:hover:not(:disabled) {
  border-color: #b8a795;
  background: #fffaf1;
}

.button-danger {
  background: #b84e4e;
  color: white;
}

.button-wide {
  width: 100%;
}

.button-glyph {
  font-size: 1.1rem;
  line-height: 1;
}

.hero-panel {
  display: flex;
  min-height: 220px;
  align-items: flex-end;
  justify-content: space-between;
  gap: 32px;
  margin-top: 38px;
  padding: clamp(26px, 4vw, 48px);
  overflow: hidden;
  border-radius: 20px;
  background:
    radial-gradient(circle at 85% 18%, rgb(248 201 185 / 42%), transparent 28%),
    #dce6e5;
  position: relative;
}

.hero-panel::after {
  position: absolute;
  right: 8%;
  bottom: -48px;
  width: 190px;
  height: 190px;
  border: 1px solid rgb(52 91 135 / 21%);
  border-radius: 50%;
  content: "";
}

.hero-copy,
.hero-stat {
  position: relative;
  z-index: 1;
}

.eyebrow {
  color: #9d5c4e;
  font-size: 0.7rem;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.hero-copy h1 {
  max-width: 640px;
  margin: 8px 0 12px;
  color: #1e2d3a;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(2.4rem, 5vw, 4.6rem);
  font-weight: 400;
  letter-spacing: -0.055em;
  line-height: 0.98;
}

.hero-copy p {
  max-width: 480px;
  color: #556876;
  font-size: 0.95rem;
}

.hero-stat {
  min-width: 150px;
  padding: 16px 18px;
  border-left: 1px solid rgb(30 45 58 / 24%);
}

.hero-stat span,
.hero-stat small {
  display: block;
  color: #657986;
  font-size: 0.75rem;
}

.hero-stat strong {
  display: block;
  margin: 2px 0;
  color: #1e2d3a;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 3.5rem;
  font-weight: 400;
  line-height: 1;
}

.notice {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: 18px;
  padding: 11px 14px;
  border-radius: 9px;
  font-size: 0.82rem;
}

.notice-success {
  background: #e0efe5;
  color: #2d6b4a;
}

.notice-error {
  background: #f8e2dc;
  color: #994e40;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(280px, 0.65fr) minmax(0, 1.35fr);
  gap: 28px;
  margin-top: 32px;
}

.section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
}

.section-heading h2,
.detail-card-heading h2,
.chat-header h2,
.modal-header h2,
.detail-empty h2 {
  margin: 6px 0 0;
  color: #1e2d3a;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 1.65rem;
  font-weight: 400;
  letter-spacing: -0.035em;
}

.task-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #879096;
  font-size: 0.75rem;
}

.summary-divider {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #d5c8b9;
}

.filter-bar {
  display: flex;
  gap: 4px;
  margin: 22px 0 16px;
  padding-bottom: 9px;
  border-bottom: 1px solid #dfd5c8;
}

.filter-button {
  padding: 8px 12px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: #879096;
  cursor: pointer;
  font: inherit;
  font-size: 0.8rem;
}

.filter-button:hover,
.filter-button:focus-visible,
.filter-button.active {
  border-bottom-color: #ed795f;
  color: #263442;
  outline: none;
}

.task-list {
  display: grid;
  gap: 12px;
}

.task-card {
  padding: 19px 20px 16px;
  border: 1px solid #e2d9ce;
  border-radius: 13px;
  background: rgb(255 252 246 / 72%);
  cursor: pointer;
  transition:
    border-color 160ms ease,
    background 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.task-card:hover,
.task-card:focus-visible,
.task-card.selected {
  border-color: #d99b89;
  background: #fffaf1;
  box-shadow: 0 10px 24px rgb(112 86 67 / 10%);
  outline: none;
  transform: translateY(-2px);
}

.task-card-topline,
.task-card-footer,
.detail-card-heading,
.detail-actions,
.modal-actions,
.chat-header,
.modal-header {
  display: flex;
  align-items: center;
}

.task-card-topline {
  gap: 8px;
}

.status-marker {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-todo {
  background: #e1a05a;
}

.status-done {
  background: #77a38a;
}

.task-status-label {
  color: #879096;
  font-size: 0.74rem;
}

.priority-chip {
  margin-left: auto;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 800;
}

.priority-high {
  background: #f8dfd4;
  color: #a04e3d;
}

.priority-medium {
  background: #f5e8c8;
  color: #927021;
}

.priority-low {
  background: #dfeee3;
  color: #427253;
}

.task-card h3 {
  margin: 15px 0 8px;
  color: #263442;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 1.16rem;
  font-weight: 400;
}

.task-description {
  display: -webkit-box;
  overflow: hidden;
  color: #66747e;
  font-size: 0.84rem;
  line-height: 1.65;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.task-card-footer {
  justify-content: space-between;
  margin-top: 17px;
  padding-top: 12px;
  border-top: 1px solid #eee5da;
  color: #89939a;
  font-size: 0.73rem;
}

.task-arrow {
  color: #ed795f;
  font-size: 1rem;
}

.state-message,
.empty-state {
  padding: 42px 20px;
  color: #7f8992;
  text-align: center;
}

.empty-state {
  border: 1px dashed #d8cabc;
  border-radius: 14px;
}

.empty-mark,
.empty-orbit {
  display: block;
  margin: 0 auto 14px;
  color: #d99b89;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 2.8rem;
}

.empty-state strong {
  display: block;
  color: #45545f;
}

.empty-state p,
.detail-empty p {
  margin: 8px auto 20px;
  max-width: 280px;
  color: #89939a;
  font-size: 0.82rem;
  line-height: 1.65;
}

.detail-card,
.detail-empty {
  min-height: 330px;
  padding: 25px;
  border: 1px solid #d8e1df;
  border-radius: 16px;
  background: #edf3f0;
}

.detail-card-heading {
  align-items: flex-start;
  justify-content: space-between;
  gap: 15px;
}

.detail-card-heading h2 {
  max-width: 30ch;
  line-height: 1.1;
}

.detail-status-badge {
  padding: 6px 9px;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 800;
  white-space: nowrap;
}

.detail-status-badge.status-todo {
  background: #f5e8c8;
  color: #927021;
}

.detail-status-badge.status-done {
  background: #dfeee3;
  color: #427253;
}

.detail-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 28px;
  padding: 16px 0;
  border-top: 1px solid #d8e1df;
  border-bottom: 1px solid #d8e1df;
}

.detail-facts span,
.detail-requirement > span {
  display: block;
  color: #7f8e8c;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.detail-facts strong {
  display: block;
  margin-top: 4px;
  overflow: hidden;
  color: #263f42;
  font-size: 0.82rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mono-text {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 0.7rem !important;
}

.detail-requirement {
  margin-top: 20px;
}

.detail-requirement p {
  margin: 8px 0 0;
  color: #566c6c;
  font-size: 0.84rem;
  line-height: 1.7;
  white-space: pre-wrap;
}

.detail-actions {
  flex-direction: column;
  align-items: stretch;
  gap: 9px;
  margin-top: 24px;
}

.text-button {
  align-self: center;
  padding: 3px 8px;
  background: transparent;
  cursor: pointer;
  font-size: 0.76rem;
}

.danger-text {
  color: #a04e3d;
}

.detail-empty {
  display: grid;
  min-height: 330px;
  place-content: center;
  text-align: center;
}

.detail-empty h2 {
  margin-top: 4px;
}

.empty-orbit {
  color: #ed795f;
  font-size: 2.2rem;
}

.chat-drawer {
  position: fixed;
  z-index: 30;
  top: 18px;
  right: 18px;
  bottom: 18px;
  display: flex;
  width: min(390px, calc(100vw - 36px));
  flex-direction: column;
  padding: 22px;
  border: 1px solid #d8cabc;
  border-radius: 18px;
  background: #fffaf1;
  box-shadow: 0 24px 80px rgb(46 38 30 / 22%);
}

.chat-header,
.modal-header {
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.chat-header h2,
.modal-header h2 {
  font-size: 1.5rem;
}

.chat-scope {
  margin: 6px 0 0;
  color: #7b716c;
  font-size: 0.72rem;
  line-height: 1.45;
}

.icon-button {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 50%;
  background: #f0e8dc;
  color: #66747e;
  cursor: pointer;
  font-size: 1.3rem;
  line-height: 1;
}

.chat-messages {
  display: grid;
  flex: 1;
  align-content: start;
  gap: 14px;
  margin: 22px -4px 16px;
  padding: 4px;
  overflow-y: auto;
}

.chat-message {
  max-width: 88%;
  padding: 11px 13px;
  border-radius: 12px;
}

.message-assistant {
  justify-self: start;
  background: #edf3f0;
  color: #405858;
}

.message-user {
  justify-self: end;
  background: #f8dfd4;
  color: #75463c;
}

.message-role {
  display: block;
  margin-bottom: 4px;
  color: #8a918d;
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.chat-message p {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.65;
  white-space: pre-wrap;
}

.typing-dots {
  color: #8a918d;
}

.chat-composer {
  display: grid;
  gap: 10px;
}

.chat-composer textarea,
.form-field input,
.form-field select,
.form-field textarea,
.confirmation-input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #d8cabc;
  border-radius: 8px;
  background: #fffdf8;
  color: #263442;
  font: inherit;
  font-size: 0.84rem;
  outline: none;
}

.chat-composer textarea,
.form-field textarea {
  resize: vertical;
}

.chat-composer textarea {
  padding: 11px;
}

.chat-composer textarea:focus,
.form-field input:focus,
.form-field select:focus,
.form-field textarea:focus,
.confirmation-input:focus {
  border-color: #d99b89;
  box-shadow: 0 0 0 3px rgb(237 121 95 / 13%);
}

.modal-backdrop {
  position: fixed;
  z-index: 40;
  inset: 0;
  display: grid;
  overflow-y: auto;
  place-items: center;
  padding: 20px;
  background: rgb(27 35 43 / 46%);
}

.modal-card {
  width: min(520px, 100%);
  max-height: calc(100vh - 40px);
  overflow-y: auto;
  padding: 26px;
  border: 1px solid #dfd2c3;
  border-radius: 16px;
  background: #fffaf1;
  box-shadow: 0 24px 80px rgb(30 38 44 / 24%);
}

.form-field {
  display: grid;
  gap: 7px;
  margin-top: 17px;
  color: #5f706f;
  font-size: 0.76rem;
  font-weight: 800;
}

.form-field input,
.form-field select,
.form-field textarea,
.confirmation-input {
  padding: 10px 11px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.modal-actions {
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}

.form-error {
  margin: 14px 0 0;
  color: #a04e3d;
  font-size: 0.8rem;
  line-height: 1.5;
}

.danger-modal {
  max-width: 470px;
}

.danger-copy {
  margin: 22px 0 14px;
  color: #6c7473;
  font-size: 0.86rem;
  line-height: 1.7;
}

.confirmation-hint {
  color: #596867;
  font-size: 0.78rem;
  line-height: 1.6;
}

.confirmation-hint code {
  display: block;
  margin-top: 8px;
  padding: 10px;
  overflow-x: auto;
  border-radius: 7px;
  background: #f0e8dc;
  color: #75463c;
  font-family: ui-monospace, Consolas, monospace;
  font-size: 0.75rem;
  white-space: nowrap;
}

.confirmation-input {
  margin-top: 10px;
}

.plan-panel {
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid #d8e1df;
}

.plan-heading {
  align-items: center;
  padding: 12px 13px;
  border: 1px solid #efd2c6;
  border-radius: 12px;
  background:
    linear-gradient(135deg, rgb(255 247 239 / 96%), rgb(255 252 246 / 86%));
}

.plan-heading,
.plan-actions,
.material-list li,
.risk-list li {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.plan-heading-copy > span,
.plan-heading strong {
  display: block;
}

.plan-heading-copy > span {
  color: #7f8e8c;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.plan-heading strong {
  margin-top: 4px;
  color: #405858;
  font-size: 0.82rem;
}

.plan-heading-copy {
  min-width: 0;
}

.plan-heading-hint {
  margin: 5px 0 0;
  color: #7b716c;
  font-size: 0.74rem;
  line-height: 1.45;
}

.plan-generate-button {
  min-height: 46px;
  flex: 0 0 auto;
  padding: 0 14px;
  border-radius: 10px;
  box-shadow: 0 9px 18px rgb(196 85 64 / 24%);
}

.plan-generate-button:hover:not(:disabled) {
  box-shadow: 0 12px 22px rgb(196 85 64 / 31%);
}

.plan-generate-arrow {
  margin-left: 1px;
  font-size: 1.05rem;
  line-height: 1;
}

.plan-goal,
.plan-prerequisite,
.plan-muted,
.plan-sources {
  color: #566c6c;
  font-size: 0.79rem;
  line-height: 1.65;
}

.plan-goal {
  margin: 12px 0 6px;
}

.plan-heading + .plan-muted,
.plan-heading + .form-error {
  margin-top: 13px;
  padding: 10px 12px;
  border-radius: 9px;
  background: rgb(255 255 255 / 48%);
}

.plan-heading + .form-error {
  border: 1px solid rgb(160 78 61 / 20%);
}

.plan-prerequisite,
.plan-sources {
  margin: 5px 0 0;
}

.plan-sources span:not(:last-child)::after {
  content: "；";
}

.plan-step-list {
  display: grid;
  gap: 10px;
  margin: 14px 0 0;
  padding: 0;
  list-style: none;
}

.plan-step-list li {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 11px 12px;
  border: 1px solid #f0d4c2;
  border-radius: 9px;
  background: #fff2e7;
}

.plan-step-list strong,
.plan-step-list small {
  display: block;
}

.plan-step-list strong {
  color: #344f50;
  font-size: 0.78rem;
}

.plan-step-list small {
  margin-top: 3px;
  color: #82908e;
  font-size: 0.68rem;
}

.plan-step-list p {
  margin: 5px 0 0;
  color: #637674;
  font-size: 0.75rem;
  line-height: 1.55;
}

.plan-actions {
  margin-top: 13px;
}

.materials-modal,
.risks-modal {
  max-width: 680px;
}

.file-upload-control {
  display: grid;
  gap: 8px;
  margin-top: 22px;
  padding: 14px;
  border: 1px dashed #cba998;
  border-radius: 10px;
  background: #fffdf8;
  color: #5f706f;
  font-size: 0.82rem;
  font-weight: 700;
}

.file-upload-control input {
  max-width: 100%;
  color: #66747e;
  font-size: 0.78rem;
}

.material-list,
.risk-list {
  display: grid;
  gap: 10px;
  margin: 20px 0 0;
  padding: 0;
  list-style: none;
}

.material-list li,
.risk-list li {
  padding: 13px;
  border: 1px solid #e2d9ce;
  border-radius: 10px;
  background: #fffdf8;
}

.material-list strong,
.material-list small,
.risk-list strong,
.risk-list small {
  display: block;
}

.material-list strong,
.risk-list strong {
  color: #334355;
  font-size: 0.84rem;
}

.material-list small,
.risk-list small {
  margin-top: 4px;
  color: #7f8992;
  font-size: 0.73rem;
}

.material-error {
  margin: 6px 0 0;
  color: #a04e3d;
  font-size: 0.74rem;
}

.risk-level {
  min-width: 45px;
  padding-top: 2px;
  color: #8a918d;
  font-size: 0.7rem;
  font-weight: 800;
}

.risk-list p {
  margin: 7px 0 0;
  color: #65727c;
  font-size: 0.78rem;
  line-height: 1.6;
}

.risk-source {
  display: block;
  margin-top: 6px;
  color: #8b675a;
  font-size: 0.72rem;
}

.risk-critical {
  border-left: 4px solid #b84e4e !important;
}

.risk-high {
  border-left: 4px solid #d27b48 !important;
}

.risk-medium {
  border-left: 4px solid #d2a247 !important;
}

.risk-low {
  border-left: 4px solid #77a38a !important;
}

@media (max-width: 980px) {
  .sidebar {
    width: 220px;
    flex-basis: 220px;
  }

  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .detail-column {
    order: -1;
  }

  .detail-card,
  .detail-empty {
    min-height: auto;
  }
}

@media (max-width: 700px) {
  .app-shell {
    display: block;
  }

  .sidebar {
    width: auto;
    min-height: auto;
    padding: 18px 16px;
  }

  .sidebar-divider,
  .sidebar-footer {
    display: none;
  }

  .course-nav {
    display: flex;
    margin-top: 12px;
    overflow-x: auto;
    padding-bottom: 4px;
  }

  .course-nav-item {
    min-width: 180px;
  }

  .workspace {
    padding: 20px 16px 42px;
  }

  .topbar,
  .hero-panel,
  .section-heading,
  .plan-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .plan-generate-button {
    width: 100%;
  }

  .topbar-actions {
    width: 100%;
  }

  .topbar-actions .button {
    flex: 1;
  }

  .hero-panel {
    min-height: auto;
    margin-top: 26px;
  }

  .hero-stat {
    width: 100%;
    box-sizing: border-box;
    border-top: 1px solid rgb(30 45 58 / 18%);
    border-left: 0;
  }

  .task-summary {
    margin-top: 4px;
  }

  .form-row {
    grid-template-columns: 1fr;
    gap: 0;
  }
}
</style>
