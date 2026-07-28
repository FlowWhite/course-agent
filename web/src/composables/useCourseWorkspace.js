import { computed, onMounted, ref } from "vue"

export function useCourseWorkspace() {
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
  const taskAssessment = ref(null)
  const assessmentSaving = ref(false)
  const assessmentError = ref("")

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
    taskAssessment.value = null
    assessmentError.value = ""
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
    taskAssessment.value = null
    assessmentError.value = ""
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
    taskAssessment.value = null
    assessmentError.value = ""

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

  async function confirmTaskPlan() {
    if (!taskPlan.value || planSaving.value) {
      return
    }
    planSaving.value = true
    planError.value = ""
    try {
      taskPlan.value = await requestJson(
        `/api/v1/plans/${encodeURIComponent(taskPlan.value.id)}/confirm`,
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

  async function assessTaskSubmission(file) {
    if (!selectedTask.value || !file || assessmentSaving.value) {
      return
    }

    const formData = new FormData()
    formData.append("file", file)
    assessmentSaving.value = true
    assessmentError.value = ""
    try {
      taskAssessment.value = await requestJson(
        `/api/v1/tasks/${encodeURIComponent(selectedTask.value.id)}/assessment`,
        { method: "POST", body: formData },
        "作业评估失败",
      )
      showNotice("success", "作业已完成评估，请根据建议自行修改。")
    } catch (exception) {
      assessmentError.value = exception.message
    } finally {
      assessmentSaving.value = false
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
  return {
    accessToken, loginForm, authMode, loginLoading, loginError, registerLoading,
    registerError, authNotice, courses, selectedCourseId, tasks, selectedTaskId,
    taskFilter, loading, tasksLoading, error, taskError, notice, formMode,
    formSaving, formError, taskForm, deleteDialogOpen, deleteInput, deleteError,
    deleteSaving, chatOpen, chatInput, chatSending, chatMessages, materialsOpen,
    courseFiles, filesLoading, fileUploading, fileError, risksOpen, risks,
    risksLoading, risksError, taskPlan, plansLoading, planSaving, planError,
    taskAssessment, assessmentSaving, assessmentError,
    selectedCourse, selectedTask, filteredTasks, todoCount, doneCount, formTitle,
    deleteConfirmationText, activateCourseAgentChat, login, switchAuthMode,
    register, logout, loadCourses, selectCourse, loadTasks, loadTaskDetail,
    loadCourseFiles, uploadCourseFile, deleteCourseFile, loadRisks, loadTaskPlans,
    generateTaskPlan, confirmTaskPlan, assessTaskSubmission, updateTaskStatus, openCreate, openEdit,
    closeForm, submitTaskForm, openDeleteDialog, closeDeleteDialog, confirmDelete,
    toggleChat, sendChat, statusLabel, priorityLabel, courseInitials, priorityClass,
    fileSizeLabel, parseStatusLabel, planStatusLabel, riskLevelLabel,
  }
}
