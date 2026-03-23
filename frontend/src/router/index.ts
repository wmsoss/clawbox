// frontend/src/router/index.ts
// 路由及守卫配置 — 基于 AdminUser 是否存在的三段判断
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSetupStore } from '@/stores/setup'

import WizardView from '@/views/WizardView.vue'
import LoginView from '@/views/LoginView.vue'
import DashboardView from '@/views/DashboardView.vue'
import SkillsRegistryView from '@/views/SkillsRegistryView.vue'
import TerminalView from '@/views/TerminalView.vue'
import LLMSettingsView from '@/views/LLMSettingsView.vue'
import OpenClawConfigView from '@/views/OpenClawConfigView.vue'
import AccountSettingsView from '@/views/AccountSettingsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'root',
      // 由 beforeEach 动态决定跳转目标
      redirect: '/dashboard'
    },
    {
      path: '/wizard',
      name: 'wizard',
      component: WizardView
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: DashboardView
    },
    {
      path: '/settings/llm',
      name: 'settings-llm',
      component: LLMSettingsView
    },
    {
      path: '/skills',
      name: 'skills',
      component: SkillsRegistryView
    },
    {
      path: '/settings/openclaw',
      name: 'settings-openclaw',
      component: OpenClawConfigView
    },
    {
      path: '/settings/account',
      name: 'settings-account',
      component: AccountSettingsView
    },
    {
      path: '/terminal',
      name: 'terminal',
      component: TerminalView
    }
  ]
})

// 路由守卫：基于 AdminUser 是否存在的三段跳转
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  const setup = useSetupStore()

  // 首次加载时从后端拉取 userExists 状态
  if (!setup.isLoaded) {
    await setup.fetchState()
  }

  const isPublicWizard = to.name === 'wizard'
  const isLogin = to.name === 'login'

  // 1. 无用户 → 强制跳 wizard（排除 wizard 本身，避免循环）
  if (!setup.userExists && !isPublicWizard) {
    return { name: 'wizard' }
  }

  // 2. 有用户 + 无 token → 跳 login（排除 login 本身，避免循环）
  if (setup.userExists && !auth.token && !isLogin) {
    return { name: 'login' }
  }

  // 3. 有用户 + 有 token + 访问 wizard → 跳 dashboard（向导已完成）
  if (setup.userExists && auth.token && isPublicWizard) {
    return { name: 'dashboard' }
  }

  // 4. 有用户 + 有 token + 访问 login → 跳 dashboard（已登录）
  if (setup.userExists && auth.token && isLogin) {
    return { name: 'dashboard' }
  }

  // 5. 其余放行
})

export default router
