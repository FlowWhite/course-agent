<script setup>
import AuthScreen from "./components/AuthScreen.vue"
import AgentChatDrawer from "./components/AgentChatDrawer.vue"
import CourseMaterialsModal from "./components/CourseMaterialsModal.vue"
import CourseSidebar from "./components/CourseSidebar.vue"
import RiskRadarModal from "./components/RiskRadarModal.vue"
import TaskDetailPanel from "./components/TaskDetailPanel.vue"
import TaskList from "./components/TaskList.vue"
import TaskManagementModals from "./components/TaskManagementModals.vue"
import WorkspaceTopbar from "./components/WorkspaceTopbar.vue"
import { useCourseWorkspace } from "./composables/useCourseWorkspace"

const {
  accessToken, loginForm, authMode, loginLoading, loginError, registerLoading,
  registerError, authNotice, courses, selectedCourseId, tasks, selectedTaskId,
  taskFilter, loading, tasksLoading, error, taskError, notice, formMode,
  formSaving, formError, taskForm, deleteDialogOpen, deleteInput, deleteError,
  deleteSaving, chatOpen, chatInput, chatSending, chatMessages, materialsOpen,
  courseFiles, filesLoading, fileUploading, fileError, risksOpen, risks,
  risksLoading, risksError, taskPlan, plansLoading, planSaving, planError,
  selectedCourse, selectedTask, filteredTasks, todoCount, doneCount, formTitle,
  deleteConfirmationText, activateCourseAgentChat, login, switchAuthMode,
  register, logout, selectCourse, loadTaskDetail, loadCourseFiles, uploadCourseFile,
  deleteCourseFile, loadRisks, generateTaskPlan, changePlanState,
  updateTaskStatus, openCreate, openEdit, closeForm, submitTaskForm,
  openDeleteDialog, closeDeleteDialog, confirmDelete, toggleChat, sendChat,
  statusLabel, priorityLabel, courseInitials, priorityClass, fileSizeLabel,
  parseStatusLabel, planStatusLabel, riskLevelLabel,
} = useCourseWorkspace()
</script>

<template>
  <AuthScreen
    v-if="!accessToken"
    :login-form="loginForm"
    :auth-mode="authMode"
    :login-loading="loginLoading"
    :login-error="loginError"
    :register-loading="registerLoading"
    :register-error="registerError"
    :auth-notice="authNotice"
    @login="login"
    @register="register"
    @switch-mode="switchAuthMode"
  />

  <div v-else class="app-shell">
    <CourseSidebar
      :courses="courses"
      :selected-course-id="selectedCourseId"
      :loading="loading"
      :error="error"
      :course-initials="courseInitials"
      @select="selectCourse"
    />

    <main class="workspace">
      <WorkspaceTopbar
        :selected-course="selectedCourse"
        @materials="materialsOpen = true"
        @risks="risksOpen = true"
        @chat="toggleChat"
        @create="openCreate"
        @logout="logout"
      />

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
        <TaskList
          :selected-course="selectedCourse"
          :tasks="tasks"
          :filtered-tasks="filteredTasks"
          :selected-task-id="selectedTaskId"
          v-model:task-filter="taskFilter"
          :done-count="doneCount"
          :tasks-loading="tasksLoading"
          :task-error="taskError"
          :status-label="statusLabel"
          :priority-label="priorityLabel"
          :priority-class="priorityClass"
          @select="loadTaskDetail"
          @create="openCreate"
        />

        <TaskDetailPanel
          :selected-task="selectedTask"
          :task-plan="taskPlan"
          :plans-loading="plansLoading"
          :plan-saving="planSaving"
          :plan-error="planError"
          :status-label="statusLabel"
          :priority-label="priorityLabel"
          :plan-status-label="planStatusLabel"
          @generate-plan="generateTaskPlan"
          @plan-action="changePlanState"
          @toggle-status="updateTaskStatus"
          @edit="openEdit"
          @delete="openDeleteDialog"
        />
      </section>
    </main>

    <AgentChatDrawer
      v-if="chatOpen"
      :selected-course="selectedCourse"
      :chat-messages="chatMessages"
      :chat-sending="chatSending"
      v-model="chatInput"
      @close="toggleChat"
      @send="sendChat"
    />

    <CourseMaterialsModal
      v-if="materialsOpen"
      :selected-course="selectedCourse"
      :course-files="courseFiles"
      :files-loading="filesLoading"
      :file-uploading="fileUploading"
      :file-error="fileError"
      :file-size-label="fileSizeLabel"
      :parse-status-label="parseStatusLabel"
      @close="materialsOpen = false"
      @upload="uploadCourseFile"
      @delete="deleteCourseFile"
    />

    <RiskRadarModal
      v-if="risksOpen"
      :selected-course="selectedCourse"
      :risks="risks"
      :risks-loading="risksLoading"
      :risks-error="risksError"
      :risk-level-label="riskLevelLabel"
      @close="risksOpen = false"
    />

    <TaskManagementModals
      :form-mode="formMode"
      :form-title="formTitle"
      :task-form="taskForm"
      :courses="courses"
      :form-saving="formSaving"
      :form-error="formError"
      :delete-dialog-open="deleteDialogOpen"
      :delete-confirmation-text="deleteConfirmationText"
      v-model:delete-input="deleteInput"
      :delete-error="deleteError"
      :delete-saving="deleteSaving"
      @close-form="closeForm"
      @submit-form="submitTaskForm"
      @close-delete="closeDeleteDialog"
      @confirm-delete="confirmDelete"
    />
  </div>
</template>

<style>
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
