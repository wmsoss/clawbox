<template>
  <div class="skills-registry-view">
    <!-- Shared Navigation Bar -->
    <NavBar />

    <div class="header">
      <div class="header-left">
        <h2>Skills Registry</h2>
        <span class="skill-count">{{ totalSkills }} skills</span>
      </div>
      <div class="header-right">
        <div class="search-box">
          <el-input
            v-model="searchQuery"
            placeholder="Search skills..."
            clearable
            :prefix-icon="Search"
            @input="filterSkills"
          />
        </div>
        <el-button @click="refreshSkills" :loading="loading" circle>
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- Category Navigation Tabs -->
    <div class="category-tabs">
      <el-tabs v-model="activeCategory" type="card" @tab-click="handleTabClick">
        <el-tab-pane label="All" name="all">
          <template #label>
            <span>All ({{ totalSkills }})</span>
          </template>
        </el-tab-pane>
        <el-tab-pane
          v-for="cat in categories"
          :key="cat.name"
          :label="cat.name"
          :name="cat.name"
        >
          <template #label>
            <span>{{ cat.name }} ({{ cat.count }})</span>
          </template>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- Error state -->
    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />

    <!-- Skills Grid -->
    <div class="skills-content" v-loading="loading">
      <el-scrollbar>
        <div v-if="filteredSkills.length === 0" class="empty-state">
          <el-empty description="No skills found matching your criteria" />
        </div>
        <div v-else class="skills-grid">
          <el-card
            v-for="skill in filteredSkills"
            :key="skill.repo_url"
            class="skill-card"
            shadow="hover"
          >
            <template #header>
              <div class="card-header">
                <span class="skill-name">{{ skill.name }}</span>
                <span class="category-tag">{{ skill.category }}</span>
                <el-button
                  v-if="skill.is_installed"
                  type="danger"
                  size="small"
                  plain
                  :loading="skill.uninstalling"
                  @click="uninstallSkill(skill)"
                >
                  卸载
                </el-button>
                <el-button
                  v-else
                  type="primary"
                  size="small"
                  plain
                  :loading="skill.installing"
                  @click="installSkill(skill)"
                >
                  安装
                </el-button>
              </div>
            </template>
            <div class="card-body">
              <p class="skill-desc">{{ skill.description || 'No description available' }}</p>
              <a :href="skill.repo_url" target="_blank" class="repo-link">
                <el-icon><Link /></el-icon> GitHub Repo
              </a>
            </div>
          </el-card>
        </div>
      </el-scrollbar>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Link } from '@element-plus/icons-vue'
import { Search } from '@element-plus/icons-vue'
import { apiFetch } from '@/utils/api'
import NavBar from '@/components/common/NavBar.vue'


interface SkillItem {
  name: string
  category: string
  repo_url: string
  description: string
  is_installed: boolean
  installing?: boolean
  uninstalling?: boolean
}

interface CategoryInfo {
  name: string
  count: number
}

const loading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const activeCategory = ref('all')
const allSkills = ref<SkillItem[]>([])
const filteredSkills = ref<SkillItem[]>([])

const totalSkills = computed(() => allSkills.value.length)

const categories = computed<CategoryInfo[]>(() => {
  const categoryMap = new Map<string, number>()
  allSkills.value.forEach(skill => {
    categoryMap.set(skill.category, (categoryMap.get(skill.category) || 0) + 1)
  })
  return Array.from(categoryMap.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
})

async function fetchSkills() {
  loading.value = true
  error.value = null
  try {
    const res = await apiFetch('/api/v1/skills/list')
    if (res && res.sections) {
      allSkills.value = res.sections.flatMap((section: any) =>
        section.skills.map((s: any) => ({
          ...s,
          category: section.name,
          installing: false,
          uninstalling: false
        }))
      )
      filterSkills()
    }
  } catch (err: any) {
    error.value = err.message || 'Failed to fetch skills'
    if (error.value) {
      ElMessage.error(error.value)
    }
  } finally {
    loading.value = false
  }
}

function filterSkills() {
  let skills = allSkills.value

  // Filter by category
  if (activeCategory.value !== 'all') {
    skills = skills.filter(s => s.category === activeCategory.value)
  }

  // Filter by search query
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    skills = skills.filter(s =>
      s.name.toLowerCase().includes(query) ||
      s.description?.toLowerCase().includes(query) ||
      s.category.toLowerCase().includes(query)
    )
  }

  filteredSkills.value = skills
}

function handleTabClick() {
  filterSkills()
}

function refreshSkills() {
  fetchSkills()
}

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
    ElMessage.success(`Skill "${skill.name}" installed successfully!`)
  } catch (err: any) {
    ElMessage.error(`Installation failed: ${err.message}`)
  } finally {
    skill.installing = false
  }
}

async function uninstallSkill(skill: SkillItem) {
  skill.uninstalling = true
  try {
    const urlParts = skill.repo_url.replace(/\/$/, '').split('/')
    const targetName = urlParts[urlParts.length - 1] || skill.name
    await apiFetch(`/api/v1/skills/${encodeURIComponent(targetName)}`, {
      method: 'DELETE'
    })
    skill.is_installed = false
    ElMessage.success(`Skill "${skill.name}" uninstalled!`)
  } catch (err: any) {
    ElMessage.error(`Uninstallation failed: ${err.message}`)
  } finally {
    skill.uninstalling = false
  }
}

onMounted(() => {
  if (allSkills.value.length === 0) {
    fetchSkills()
  }
})
</script>

<style scoped>
.skills-registry-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 1rem;
  background-color: #f5f7fa;
}

/* Shared Top Navigation Bar */
.top-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #fff;
  border-radius: 8px;
  margin-bottom: 1rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}
.nav-brand { font-size: 18px; font-weight: 600; color: var(--el-text-color-primary); }
.nav-links { display: flex; gap: 1rem; }
.nav-link { font-size: 14px; color: var(--el-text-color-regular); text-decoration: none; padding: 6px 12px; border-radius: 4px; transition: all 0.2s; }
.nav-link:hover { background: #f5f7fa; color: var(--el-color-primary); }
.nav-link.active { background: var(--el-color-primary-light-9); color: var(--el-color-primary); font-weight: 500; }
.nav-actions { display: flex; align-items: center; }

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 0 1rem 0;
  background: #fff;
  border-radius: 8px;
  padding: 1rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.skill-count {
  font-size: 14px;
  color: #909399;
  background: #f0f2f5;
  padding: 4px 12px;
  border-radius: 12px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-box {
  width: 300px;
}

.category-tabs {
  margin-top: 1rem;
  background: #fff;
  border-radius: 8px;
  padding: 0 1rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.skills-content {
  flex: 1;
  margin-top: 1rem;
  background: #fff;
  border-radius: 8px;
  padding: 1rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.skills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}

.skill-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.skill-name {
  font-weight: 600;
  font-size: 15px;
  flex: 1;
}

.category-tag {
  font-size: 12px;
  color: #606266;
  background: #f0f2f5;
  padding: 2px 8px;
  border-radius: 4px;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.skill-desc {
  font-size: 13px;
  color: #606266;
  margin: 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.repo-link {
  font-size: 12px;
  color: var(--el-color-primary);
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: auto;
}

.repo-link:hover {
  text-decoration: underline;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}
</style>
