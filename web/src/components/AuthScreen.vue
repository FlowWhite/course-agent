<script setup>
defineProps({
  loginForm: { type: Object, required: true },
  authMode: { type: String, required: true },
  loginLoading: { type: Boolean, required: true },
  loginError: { type: String, required: true },
  registerLoading: { type: Boolean, required: true },
  registerError: { type: String, required: true },
  authNotice: { type: String, required: true },
})

const emit = defineEmits(["login", "register", "switch-mode"])

function toggleAuthMode(authMode) {
  emit("switch-mode", authMode === "login" ? "register" : "login")
}
</script>

<template>
  <div class="auth-shell">
    <section class="auth-card">
      <div class="brand-mark auth-brand-mark">CA</div>
      <p class="auth-eyebrow">COURSE AGENT</p>
      <h1>登录课程工作台</h1>
      <p class="auth-subtitle">登录后查看课程、任务和 Agent 对话。</p>

      <p v-if="authNotice" class="auth-success" role="status">
        {{ authNotice }}
      </p>

      <form v-if="authMode === 'login'" class="auth-form" @submit.prevent="emit('login')">
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
        <p v-if="loginError" class="form-error" role="alert">{{ loginError }}</p>
        <button class="button button-primary auth-submit" type="submit" :disabled="loginLoading">
          {{ loginLoading ? "登录中..." : "登录" }}
        </button>
      </form>

      <form v-else class="auth-form" @submit.prevent="emit('register')">
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
        <p v-if="registerError" class="form-error" role="alert">{{ registerError }}</p>
        <button class="button button-primary auth-submit" type="submit" :disabled="registerLoading">
          {{ registerLoading ? "注册中..." : "注册" }}
        </button>
      </form>

      <button class="auth-switch" type="button" @click="toggleAuthMode(authMode)">
        {{ authMode === "login" ? "还没有账号？去注册" : "已有账号？返回登录" }}
      </button>
    </section>
  </div>
</template>
