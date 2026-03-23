import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiFetch } from '@/utils/api'
import { ElMessage } from 'element-plus'

export interface SkillItem {
  name: string
  repo_url: string
  description: string
  is_installed: boolean
  installing?: boolean
  uninstalling?: boolean
}

export interface SkillSection {
  name: string
  description: string
  skills: SkillItem[]
}

export const useSkillStore = defineStore('skill', () => {
  const sections = ref<SkillSection[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 获取所有技能列表及安装状态
  async function fetchSkills() {
    loading.value = true
    error.value = null
    try {
      const res = await apiFetch('/api/v1/skills/list')
      if (res && res.sections) {
        sections.value = res.sections.map((sec: any) => ({
          ...sec,
          skills: sec.skills.map((s: any) => ({
            ...s,
            installing: false,
            uninstalling: false
          }))
        }))
      }
    } catch (err: any) {
      error.value = err.message || '获取技能列表失败'
      if (error.value) {
        ElMessage.error(error.value)
      }
    } finally {
      loading.value = false
    }
  }

  // 安装技能
  async function installSkill(skill: SkillItem) {
    skill.installing = true
    try {
      await apiFetch('/api/v1/skills/install', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: skill.repo_url,
          name: skill.name
        })
      })
      skill.is_installed = true
      ElMessage.success(`技能 ${skill.name} 安装成功！`)
    } catch (err: any) {
      ElMessage.error(`安装失败: ${err.message}`)
    } finally {
      skill.installing = false
    }
  }

  // 卸载技能
  async function uninstallSkill(skill: SkillItem) {
    skill.uninstalling = true
    try {
      // url param encoding for the repo base name we stored
      // in skills.py we expect the last part of repo_url as name
      const urlParts = skill.repo_url.replace(/\/$/, '').split('/')
      const targetName = urlParts[urlParts.length - 1] || skill.name
      await apiFetch(`/api/v1/skills/${encodeURIComponent(targetName)}`, {
        method: 'DELETE'
      })
      skill.is_installed = false
      ElMessage.success(`技能 ${skill.name} 已卸载。`)
    } catch (err: any) {
      ElMessage.error(`卸载失败: ${err.message}`)
    } finally {
      skill.uninstalling = false
    }
  }

  return {
    sections,
    loading,
    error,
    fetchSkills,
    installSkill,
    uninstallSkill
  }
})
