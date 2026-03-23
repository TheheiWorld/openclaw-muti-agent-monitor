<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '../api'
import { useI18n } from '../i18n'

const router = useRouter()
const { t, locale, setLocale } = useI18n()

const form = ref({ username: 'monitor', password: '' })
const loading = ref(false)
const errorMsg = ref('')

const handleLogin = async () => {
  errorMsg.value = ''
  loading.value = true
  try {
    const res = await login(form.value.username, form.value.password)
    localStorage.setItem('token', res.data.access_token)
    router.push('/')
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || t('auth.loginError')
  } finally {
    loading.value = false
  }
}

const toggleLocale = () => {
  setLocale(locale.value === 'zh' ? 'en' : 'zh')
}
</script>

<template>
  <div class="login-page">
    <div class="dot-bg" aria-hidden="true"></div>

    <div class="login-card">
      <div class="pixel-corner tl" aria-hidden="true"></div>
      <div class="pixel-corner tr" aria-hidden="true"></div>
      <div class="pixel-corner bl" aria-hidden="true"></div>
      <div class="pixel-corner br" aria-hidden="true"></div>

      <!-- Logo -->
      <div class="login-logo">
        <div class="logo-pixel-grid" aria-hidden="true">
          <span></span><span></span><span class="on"></span><span></span><span></span>
          <span></span><span class="on"></span><span class="on"></span><span class="on"></span><span></span>
          <span class="on"></span><span class="on"></span><span class="accent"></span><span class="on"></span><span class="on"></span>
          <span></span><span class="on"></span><span class="on"></span><span class="on"></span><span></span>
          <span></span><span></span><span class="on"></span><span></span><span></span>
        </div>
        <div class="logo-text">
          <span class="logo-title">OPENCLAW</span>
          <span class="logo-sub">MONITOR</span>
        </div>
      </div>

      <div class="login-divider" aria-hidden="true"></div>

      <!-- Form -->
      <form class="login-form" @submit.prevent="handleLogin">
        <div class="form-group">
          <label class="form-label">{{ t('auth.username') }}</label>
          <input
            v-model="form.username"
            type="text"
            class="form-input"
            autocomplete="username"
            readonly
          />
        </div>
        <div class="form-group">
          <label class="form-label">{{ t('auth.password') }}</label>
          <input
            v-model="form.password"
            type="password"
            class="form-input"
            autocomplete="current-password"
            :placeholder="t('auth.password')"
            autofocus
          />
        </div>

        <div v-if="errorMsg" class="form-error" role="alert">{{ errorMsg }}</div>

        <button type="submit" class="login-btn" :disabled="loading">
          <span v-if="loading">...</span>
          <span v-else>{{ t('auth.login') }}</span>
        </button>
      </form>

      <div class="login-footer">
        <button class="lang-btn" @click="toggleLocale">
          {{ locale === 'zh' ? 'EN' : '中文' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--bg-base);
  position: relative;
}

.dot-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  background-image: radial-gradient(circle, #D9D5CF 1px, transparent 1px);
  background-size: 24px 24px;
  opacity: 0.4;
  pointer-events: none;
}

.login-card {
  position: relative;
  z-index: 1;
  width: 360px;
  background: var(--bg-surface);
  border: 2px solid var(--border-strong);
  padding: var(--space-8);
}

.pixel-corner {
  position: absolute;
  width: 6px;
  height: 6px;
  background: var(--accent);
}
.pixel-corner.tl { top: -2px; left: -2px; }
.pixel-corner.tr { top: -2px; right: -2px; }
.pixel-corner.bl { bottom: -2px; left: -2px; }
.pixel-corner.br { bottom: -2px; right: -2px; }

/* Logo */
.login-logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}

.logo-pixel-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 1px;
  width: 35px;
  height: 35px;
  flex-shrink: 0;
}

.logo-pixel-grid span {
  background: var(--bg-elevated);
}
.logo-pixel-grid span.on {
  background: var(--text-primary);
}
.logo-pixel-grid span.accent {
  background: var(--accent);
}

.logo-text {
  display: flex;
  flex-direction: column;
}
.logo-title {
  font-family: var(--font-pixel);
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 1px;
}
.logo-sub {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 3px;
  color: var(--accent);
}

.login-divider {
  height: 2px;
  margin-bottom: var(--space-5);
  background: repeating-linear-gradient(
    to right,
    var(--border) 0px,
    var(--border) 4px,
    transparent 4px,
    transparent 8px
  );
}

/* Form */
.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.form-label {
  font-family: var(--font-pixel);
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 1px;
  text-transform: uppercase;
}

.form-input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 2px solid var(--border);
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 14px;
  transition: border-color var(--duration-fast) ease;
}

.form-input:focus {
  outline: none;
  border-color: var(--border-strong);
}

.form-input[readonly] {
  color: var(--text-muted);
  cursor: default;
}

.form-error {
  padding: var(--space-2) var(--space-3);
  background: var(--red-light);
  border: 2px solid var(--accent);
  color: var(--accent);
  font-family: var(--font-mono);
  font-size: 12px;
}

.login-btn {
  width: 100%;
  padding: var(--space-3);
  border: 2px solid var(--border-strong);
  background: var(--text-primary);
  color: var(--bg-surface);
  font-family: var(--font-pixel);
  font-size: 12px;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all var(--duration-fast) ease;
}

.login-btn:hover:not(:disabled) {
  background: var(--accent);
  border-color: var(--accent);
}

.login-btn:active:not(:disabled) {
  transform: scale(0.98);
}

.login-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Footer */
.login-footer {
  display: flex;
  justify-content: center;
  margin-top: var(--space-5);
}

.lang-btn {
  padding: var(--space-1) var(--space-3);
  border: 2px solid var(--border);
  background: var(--bg-surface);
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast) ease;
}

.lang-btn:hover {
  color: var(--text-primary);
  border-color: var(--border-strong);
}

@media (max-width: 420px) {
  .login-card {
    width: calc(100vw - var(--space-8));
    padding: var(--space-5);
  }
}
</style>
