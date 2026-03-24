<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from './i18n'
import { changePassword } from './api'

const route = useRoute()
const router = useRouter()
const { t, locale, setLocale } = useI18n()
const sidebarCollapsed = ref(false)
const mobileMenuOpen = ref(false)

// Change password dialog
const showChangePwd = ref(false)
const pwdForm = ref({ oldPassword: '', newPassword: '', confirmPassword: '' })
const pwdLoading = ref(false)
const pwdError = ref('')
const pwdSuccess = ref('')

const navKeys = [
  { path: '/', key: 'nav.dashboard', icon: '▦' },
  { path: '/instances', key: 'nav.instances', icon: '▣' },
  { path: '/agents', key: 'nav.agents', icon: '◎' },
  { path: '/ranks', key: 'nav.ranks', icon: '◉' },
  { path: '/tokens', key: 'nav.tokens', icon: '◈' },
]

const isActive = (path: string) => {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

const navigateTo = (path: string) => {
  router.push(path)
  mobileMenuOpen.value = false
}

const handleNavKeydown = (e: KeyboardEvent, path: string) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    navigateTo(path)
  }
}

const toggleLocale = () => {
  setLocale(locale.value === 'zh' ? 'en' : 'zh')
}

const handleLogout = () => {
  localStorage.removeItem('token')
  router.push('/login')
}

const openChangePwd = () => {
  pwdForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
  pwdError.value = ''
  pwdSuccess.value = ''
  showChangePwd.value = true
}

const handleChangePwd = async () => {
  pwdError.value = ''
  pwdSuccess.value = ''
  if (pwdForm.value.newPassword.length < 6) {
    pwdError.value = t('auth.passwordTooShort')
    return
  }
  if (pwdForm.value.newPassword !== pwdForm.value.confirmPassword) {
    pwdError.value = t('auth.passwordMismatch')
    return
  }
  pwdLoading.value = true
  try {
    await changePassword(pwdForm.value.oldPassword, pwdForm.value.newPassword)
    pwdSuccess.value = t('auth.passwordChanged')
    setTimeout(() => { showChangePwd.value = false }, 1500)
  } catch (e: any) {
    pwdError.value = e.response?.data?.detail || t('auth.oldPasswordWrong')
  } finally {
    pwdLoading.value = false
  }
}
</script>

<template>
  <!-- Public layout (login page) -->
  <router-view v-if="route.meta.public" />

  <!-- Authenticated layout -->
  <div v-else class="app-shell">
    <!-- Skip link -->
    <a href="#main-content" class="skip-link">{{ t('skipLink') }}</a>

    <!-- Dot-matrix background -->
    <div class="dot-bg" aria-hidden="true"></div>

    <!-- Mobile header -->
    <header class="mobile-header">
      <button
        class="mobile-menu-btn"
        :aria-expanded="mobileMenuOpen"
        aria-controls="sidebar-nav"
        :aria-label="t('toggleNav')"
        @click="mobileMenuOpen = !mobileMenuOpen"
      >
        <span class="pixel-hamburger">
          <span v-if="!mobileMenuOpen">☰</span>
          <span v-else>✕</span>
        </span>
      </button>
      <div class="mobile-logo">
        <span class="mobile-logo-icon">◉</span>
        <span class="mobile-logo-text">OPENCLAW</span>
      </div>
      <button class="mobile-lang-btn" @click="toggleLocale">
        {{ locale === 'zh' ? 'EN' : '中文' }}
      </button>
    </header>

    <!-- Sidebar overlay -->
    <div
      v-if="mobileMenuOpen"
      class="sidebar-overlay"
      @click="mobileMenuOpen = false"
    ></div>

    <!-- Sidebar -->
    <aside
      class="sidebar"
      :class="{ collapsed: sidebarCollapsed, 'mobile-open': mobileMenuOpen }"
      role="navigation"
      aria-label="主导航"
    >
      <div class="pixel-corner tl" aria-hidden="true"></div>
      <div class="pixel-corner tr" aria-hidden="true"></div>

      <div class="sidebar-header">
        <div class="logo-block" aria-hidden="true">
          <div class="logo-pixel-grid">
            <span></span><span></span><span class="on"></span><span></span><span></span>
            <span></span><span class="on"></span><span class="on"></span><span class="on"></span><span></span>
            <span class="on"></span><span class="on"></span><span class="accent"></span><span class="on"></span><span class="on"></span>
            <span></span><span class="on"></span><span class="on"></span><span class="on"></span><span></span>
            <span></span><span></span><span class="on"></span><span></span><span></span>
          </div>
        </div>
        <transition name="fade">
          <div v-if="!sidebarCollapsed" class="logo-text">
            <span class="logo-title">OPENCLAW</span>
            <span class="logo-sub">MONITOR</span>
          </div>
        </transition>
      </div>

      <nav id="sidebar-nav" class="sidebar-nav" aria-label="主菜单">
        <a
          v-for="item in navKeys"
          :key="item.path"
          role="link"
          tabindex="0"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
          :aria-current="isActive(item.path) ? 'page' : undefined"
          @click="navigateTo(item.path)"
          @keydown="handleNavKeydown($event, item.path)"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <transition name="fade">
            <span v-if="!sidebarCollapsed" class="nav-label">{{ t(item.key) }}</span>
          </transition>
          <span v-if="isActive(item.path)" class="nav-active-dot" aria-hidden="true">●</span>
        </a>
      </nav>

      <div class="sidebar-footer">
        <div class="pixel-divider" aria-hidden="true"></div>

        <!-- Language switcher -->
        <button
          v-if="!sidebarCollapsed"
          class="lang-switch-btn"
          :aria-label="t('lang.label')"
          @click="toggleLocale"
        >
          <span class="lang-icon" aria-hidden="true">⌘</span>
          <span class="lang-text">{{ locale === 'zh' ? 'EN' : '中文' }}</span>
        </button>
        <button
          v-else
          class="lang-switch-btn collapsed"
          :aria-label="t('lang.label')"
          @click="toggleLocale"
        >
          {{ locale === 'zh' ? 'En' : '中' }}
        </button>

        <!-- Change password -->
        <button
          v-if="!sidebarCollapsed"
          class="sidebar-action-btn"
          @click="openChangePwd"
        >
          <span class="action-icon" aria-hidden="true">✎</span>
          <span>{{ t('auth.changePassword') }}</span>
        </button>
        <button v-else class="sidebar-action-btn collapsed" @click="openChangePwd" :title="t('auth.changePassword')">✎</button>

        <!-- Logout -->
        <button
          v-if="!sidebarCollapsed"
          class="sidebar-action-btn logout"
          @click="handleLogout"
        >
          <span class="action-icon" aria-hidden="true">⏻</span>
          <span>{{ t('auth.logout') }}</span>
        </button>
        <button v-else class="sidebar-action-btn collapsed logout" @click="handleLogout" :title="t('auth.logout')">⏻</button>

        <button
          class="collapse-btn"
          :aria-label="sidebarCollapsed ? t('expandSidebar') : t('collapseSidebar')"
          @click="sidebarCollapsed = !sidebarCollapsed"
        >
          <span>{{ sidebarCollapsed ? '»' : '«' }}</span>
        </button>
      </div>
    </aside>

    <!-- Main -->
    <main id="main-content" class="main-content" role="main">
      <div class="content-inner">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>

    <!-- Change password dialog -->
    <div v-if="showChangePwd" class="dialog-overlay" @click.self="showChangePwd = false">
      <div class="dialog-card">
        <div class="pixel-corner tl" aria-hidden="true"></div>
        <div class="pixel-corner tr" aria-hidden="true"></div>
        <div class="dialog-header">{{ t('auth.changePassword') }}</div>
        <form class="dialog-form" @submit.prevent="handleChangePwd">
          <div class="form-group">
            <label class="form-label">{{ t('auth.oldPassword') }}</label>
            <input v-model="pwdForm.oldPassword" type="password" class="form-input" autocomplete="current-password" />
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('auth.newPassword') }}</label>
            <input v-model="pwdForm.newPassword" type="password" class="form-input" autocomplete="new-password" />
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('auth.confirmPassword') }}</label>
            <input v-model="pwdForm.confirmPassword" type="password" class="form-input" autocomplete="new-password" />
          </div>
          <div v-if="pwdError" class="form-error" role="alert">{{ pwdError }}</div>
          <div v-if="pwdSuccess" class="form-success" role="status">{{ pwdSuccess }}</div>
          <div class="dialog-actions">
            <button type="button" class="dialog-btn cancel" @click="showChangePwd = false">{{ t('auth.cancel') }}</button>
            <button type="submit" class="dialog-btn confirm" :disabled="pwdLoading">{{ t('auth.confirm') }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style>
:root {
  /* Light palette — Nothing inspired */
  --bg-base: #F5F3EF;
  --bg-surface: #FFFFFF;
  --bg-elevated: #F0EDE8;
  --bg-hover: #EBE8E3;
  --bg-active: #E5E1DB;

  /* Accent — Nothing red */
  --accent: #D71921;
  --accent-light: rgba(215, 25, 33, 0.08);
  --accent-medium: rgba(215, 25, 33, 0.15);

  /* Semantic */
  --green: #1B873F;
  --green-light: rgba(27, 135, 63, 0.1);
  --amber: #C27803;
  --amber-light: rgba(194, 120, 3, 0.1);
  --red: #D71921;
  --red-light: rgba(215, 25, 33, 0.08);

  /* Text */
  --text-primary: #1A1A1A;
  --text-secondary: #555555;
  --text-muted: #888888;

  /* Borders */
  --border: #D9D5CF;
  --border-strong: #1A1A1A;
  --border-accent: var(--accent);

  /* Spacing (8px grid) */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;

  /* Sidebar */
  --sidebar-width: 220px;
  --sidebar-collapsed-width: 56px;

  /* Fonts */
  --font-pixel: 'Silkscreen', cursive;
  --font-body: 'DM Sans', 'Noto Sans SC', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  /* Radius — pixel-block */
  --radius-sm: 2px;
  --radius-md: 4px;
  --radius-lg: 6px;

  /* Transitions */
  --duration-fast: 0.12s;
  --duration-normal: 0.2s;
  --duration-slow: 0.3s;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  overflow: hidden;
}

#app {
  height: 100%;
}

/*
 * Title font strategy:
 * - zh locale: use --font-body (DM Sans + Noto Sans SC) for Chinese support
 * - en locale: use --font-pixel (Silkscreen) for pixel aesthetic
 */
.page-title {
  font-family: var(--font-body);
  font-weight: 700;
}
[data-locale="en"] .page-title {
  font-family: var(--font-pixel);
}

.panel-title,
.section-title {
  font-family: var(--font-body);
  font-weight: 600;
}
[data-locale="en"] .panel-title,
[data-locale="en"] .section-title {
  font-family: var(--font-pixel);
  font-weight: 400;
}

/* Global focus-visible */
*:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

*:focus:not(:focus-visible) {
  outline: none;
}

/* Scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: var(--bg-elevated);
}
::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 0;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

/* Element Plus loading override */
.el-loading-mask {
  background-color: rgba(245, 243, 239, 0.85) !important;
}
.el-loading-spinner .circular {
  stroke: var(--accent) !important;
}

/* Element Plus MessageBox override — pixel-art style */
.el-overlay {
  background-color: rgba(26, 26, 26, 0.4) !important;
}
.el-message-box {
  border: 2px solid var(--border-strong) !important;
  border-radius: 0 !important;
  padding: 0 !important;
  background: var(--bg-surface) !important;
  box-shadow: 6px 6px 0 rgba(26, 26, 26, 0.08) !important;
  max-width: 420px !important;
  width: 90vw !important;
}
.el-message-box__header {
  background: var(--bg-elevated) !important;
  border-bottom: 2px dashed var(--border) !important;
  padding: var(--space-3) var(--space-4) !important;
}
.el-message-box__title {
  font-family: var(--font-body) !important;
  font-size: 14px !important;
  font-weight: 700 !important;
  color: var(--text-primary) !important;
}
.el-message-box__headerbtn {
  top: 12px !important;
  right: 12px !important;
  width: 24px !important;
  height: 24px !important;
  font-size: 14px !important;
}
.el-message-box__headerbtn .el-message-box__close {
  color: var(--text-muted) !important;
}
.el-message-box__headerbtn:hover .el-message-box__close {
  color: var(--accent) !important;
}
.el-message-box__content {
  padding: var(--space-4) !important;
  font-family: var(--font-body) !important;
  font-size: 13px !important;
  color: var(--text-secondary) !important;
}
.el-message-box__status {
  font-size: 20px !important;
}
.el-message-box__status.el-icon--warning {
  color: var(--amber) !important;
}
.el-message-box__btns {
  padding: 0 var(--space-4) var(--space-4) !important;
  display: flex !important;
  justify-content: flex-end !important;
  gap: var(--space-2) !important;
}
.el-message-box__btns .el-button {
  border-radius: 0 !important;
  font-family: var(--font-body) !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  padding: var(--space-2) var(--space-4) !important;
  border: 2px solid var(--border) !important;
  background: var(--bg-surface) !important;
  color: var(--text-secondary) !important;
  transition: all var(--duration-fast) ease !important;
}
.el-message-box__btns .el-button:hover {
  color: var(--text-primary) !important;
  border-color: var(--border-strong) !important;
  background: var(--bg-hover) !important;
}
.el-message-box__btns .el-button--primary {
  border-color: var(--accent) !important;
  background: var(--accent) !important;
  color: white !important;
}
.el-message-box__btns .el-button--primary:hover {
  background: #C01620 !important;
  border-color: #C01620 !important;
  color: white !important;
}

/* Element Plus Message override — pixel-art style */
.el-message {
  border: 2px solid var(--border-strong) !important;
  border-radius: 0 !important;
  background: var(--bg-surface) !important;
  box-shadow: 4px 4px 0 rgba(26, 26, 26, 0.06) !important;
  padding: var(--space-2) var(--space-4) !important;
}
.el-message .el-message__content {
  font-family: var(--font-body) !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  color: var(--text-primary) !important;
}
.el-message--success {
  border-color: var(--green) !important;
}
.el-message--success .el-message__icon {
  color: var(--green) !important;
}
.el-message--error {
  border-color: var(--red) !important;
}
.el-message--error .el-message__icon {
  color: var(--red) !important;
}
.el-message--warning {
  border-color: var(--amber) !important;
}
.el-message--warning .el-message__icon {
  color: var(--amber) !important;
}

/* Transitions */
.page-enter-active,
.page-leave-active {
  transition: opacity var(--duration-normal) ease;
}
.page-enter-from,
.page-leave-to {
  opacity: 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-fast) ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  position: relative;
  overflow: hidden;
}

/* Skip link */
.skip-link {
  position: absolute;
  top: -100px;
  left: var(--space-4);
  z-index: 100;
  padding: var(--space-2) var(--space-4);
  background: var(--accent);
  color: white;
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  transition: top var(--duration-fast) ease;
}

.skip-link:focus {
  top: var(--space-4);
}

/* Mobile header */
.mobile-header {
  display: none;
}

/* Dot-matrix bg */
.dot-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  background-image: radial-gradient(circle, #D9D5CF 1px, transparent 1px);
  background-size: 24px 24px;
  opacity: 0.4;
  pointer-events: none;
}

/* Sidebar overlay */
.sidebar-overlay {
  display: none;
}

/* Sidebar */
.sidebar {
  position: relative;
  z-index: 20;
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  height: 100vh;
  background: var(--bg-surface);
  border-right: 2px solid var(--border-strong);
  display: flex;
  flex-direction: column;
  transition: width var(--duration-slow) ease, min-width var(--duration-slow) ease;
  overflow: hidden;
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed-width);
  min-width: var(--sidebar-collapsed-width);
}

.pixel-corner {
  position: absolute;
  width: 6px;
  height: 6px;
  background: var(--accent);
  z-index: 2;
}
.pixel-corner.tl { top: 0; left: 0; }
.pixel-corner.tr { top: 0; right: 0; }

.sidebar-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-4);
  min-height: 72px;
  border-bottom: 1px dashed var(--border);
}

.logo-block {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
}

.logo-pixel-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 1px;
  width: 100%;
  height: 100%;
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
  white-space: nowrap;
}

.logo-title {
  font-family: var(--font-pixel);
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 1px;
}

.logo-sub {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 3px;
  color: var(--accent);
}

/* Nav */
.sidebar-nav {
  flex: 1;
  padding: var(--space-3) var(--space-2);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  color: var(--text-secondary);
  text-decoration: none;
  transition: all var(--duration-fast) ease;
  border: 2px solid transparent;
  font-family: var(--font-body);
}

.nav-item:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
  border-color: var(--border);
}

.nav-item:active {
  background: var(--bg-active);
}

.nav-item.active {
  color: var(--text-primary);
  background: var(--accent-light);
  border-color: var(--accent);
  font-weight: 600;
}

.nav-icon {
  font-size: 16px;
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}

.nav-label {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}

.nav-active-dot {
  position: absolute;
  right: var(--space-2);
  font-size: 8px;
  color: var(--accent);
}

/* Sidebar footer */
.sidebar-footer {
  padding: var(--space-2);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.pixel-divider {
  height: 2px;
  background: repeating-linear-gradient(
    to right,
    var(--border) 0px,
    var(--border) 4px,
    transparent 4px,
    transparent 8px
  );
}

/* Language switch */
.lang-switch-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-2);
  border: 2px solid var(--border);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast) ease;
}

.lang-switch-btn:hover {
  color: var(--text-primary);
  border-color: var(--border-strong);
  background: var(--bg-hover);
}

.lang-switch-btn:active {
  background: var(--bg-active);
}

.lang-switch-btn.collapsed {
  justify-content: center;
  font-size: 11px;
}

.lang-icon {
  font-size: 14px;
}

.lang-text {
  font-size: 12px;
}

.collapse-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-2);
  border: 2px solid var(--border);
  background: var(--bg-surface);
  color: var(--text-muted);
  font-family: var(--font-pixel);
  font-size: 14px;
  cursor: pointer;
  transition: all var(--duration-fast) ease;
}

.collapse-btn:hover {
  color: var(--text-primary);
  border-color: var(--text-primary);
  background: var(--bg-hover);
}

.collapse-btn:active {
  background: var(--bg-active);
}

/* Main */
.main-content {
  flex: 1;
  height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  z-index: 1;
}

.content-inner {
  padding: var(--space-8);
  min-height: 100%;
}

/* ===== RESPONSIVE ===== */
@media (max-width: 768px) {
  .mobile-header {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 30;
    height: 48px;
    padding: 0 var(--space-4);
    background: var(--bg-surface);
    border-bottom: 2px solid var(--border-strong);
  }

  .mobile-menu-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: 2px solid var(--border-strong);
    background: var(--bg-surface);
    cursor: pointer;
    font-family: var(--font-pixel);
    font-size: 16px;
  }

  .pixel-hamburger {
    line-height: 1;
  }

  .mobile-logo {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex: 1;
  }

  .mobile-logo-icon {
    font-size: 14px;
    color: var(--accent);
  }

  .mobile-logo-text {
    font-family: var(--font-pixel);
    font-size: 12px;
    letter-spacing: 1px;
  }

  .mobile-lang-btn {
    padding: var(--space-1) var(--space-2);
    border: 2px solid var(--border-strong);
    background: var(--bg-surface);
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
  }

  .sidebar-overlay {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 15;
    background: rgba(0, 0, 0, 0.3);
  }

  .sidebar {
    position: fixed;
    left: -240px;
    top: 0;
    z-index: 20;
    transition: left var(--duration-slow) ease;
  }

  .sidebar.mobile-open {
    left: 0;
  }

  .sidebar.collapsed {
    width: var(--sidebar-width);
    min-width: var(--sidebar-width);
  }

  .collapse-btn {
    display: none;
  }

  .main-content {
    margin-top: 48px;
    height: calc(100vh - 48px);
  }

  .content-inner {
    padding: var(--space-4);
  }
}

@media (max-width: 576px) {
  .content-inner {
    padding: var(--space-3);
  }
}

/* Sidebar action buttons (change password, logout) */
.sidebar-action-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-2);
  border: 2px solid var(--border);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast) ease;
}

.sidebar-action-btn:hover {
  color: var(--text-primary);
  border-color: var(--border-strong);
  background: var(--bg-hover);
}

.sidebar-action-btn:active {
  background: var(--bg-active);
}

.sidebar-action-btn.collapsed {
  justify-content: center;
  font-size: 14px;
}

.sidebar-action-btn.logout:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.action-icon {
  font-size: 14px;
}

/* Dialog */
.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
}

.dialog-card {
  position: relative;
  width: 380px;
  max-width: 90vw;
  background: var(--bg-surface);
  border: 2px solid var(--border-strong);
  padding: var(--space-6);
}

.dialog-card .pixel-corner {
  position: absolute;
  width: 6px;
  height: 6px;
  background: var(--accent);
}
.dialog-card .pixel-corner.tl { top: -2px; left: -2px; }
.dialog-card .pixel-corner.tr { top: -2px; right: -2px; }

.dialog-header {
  font-family: var(--font-pixel);
  font-size: 13px;
  color: var(--text-primary);
  margin-bottom: var(--space-5);
  padding-bottom: var(--space-3);
  border-bottom: 2px dashed var(--border);
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.dialog-form .form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.dialog-form .form-label {
  font-family: var(--font-pixel);
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 1px;
  text-transform: uppercase;
}

.dialog-form .form-input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 2px solid var(--border);
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 14px;
}

.dialog-form .form-input:focus {
  outline: none;
  border-color: var(--border-strong);
}

.form-error {
  padding: var(--space-2) var(--space-3);
  background: var(--red-light);
  border: 2px solid var(--accent);
  color: var(--accent);
  font-family: var(--font-mono);
  font-size: 12px;
}

.form-success {
  padding: var(--space-2) var(--space-3);
  background: var(--green-light);
  border: 2px solid var(--green);
  color: var(--green);
  font-family: var(--font-mono);
  font-size: 12px;
}

.dialog-actions {
  display: flex;
  gap: var(--space-3);
  justify-content: flex-end;
}

.dialog-btn {
  padding: var(--space-2) var(--space-4);
  border: 2px solid var(--border);
  background: var(--bg-surface);
  font-family: var(--font-pixel);
  font-size: 11px;
  cursor: pointer;
  transition: all var(--duration-fast) ease;
}

.dialog-btn.cancel {
  color: var(--text-secondary);
}

.dialog-btn.cancel:hover {
  background: var(--bg-hover);
  border-color: var(--border-strong);
}

.dialog-btn.confirm {
  color: var(--bg-surface);
  background: var(--text-primary);
  border-color: var(--border-strong);
}

.dialog-btn.confirm:hover:not(:disabled) {
  background: var(--accent);
  border-color: var(--accent);
}

.dialog-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
