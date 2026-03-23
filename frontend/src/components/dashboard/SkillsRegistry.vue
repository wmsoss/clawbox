<template>
  <div class="skills-registry">
    <div class="header">
      <h3>Skills Registry</h3>
      <el-button @click="refreshSkills" :loading="skillStore.loading" circle>
        <el-icon><Refresh /></el-icon>
      </el-button>
    </div>

    <!-- Error state -->
    <el-alert v-if="skillStore.error" :title="skillStore.error" type="error" show-icon />

    <el-scrollbar class="skills-list" v-loading="skillStore.loading">
      <div v-for="section in skillStore.sections" :key="section.name" class="skill-section">
        <h4 class="section-title">{{ section.name }}</h4>
        <p v-if="section.description" class="section-desc">{{ section.description }}</p>

        <div class="cards-container">
          <el-card v-for="skill in section.skills" :key="skill.repo_url" class="skill-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span class="skill-name">{{ skill.name }}</span>
                
                <el-button 
                  v-if="skill.is_installed"
                  type="danger" 
                  size="small"
                  plain
                  :loading="skill.uninstalling"
                  @click="skillStore.uninstallSkill(skill)"
                >
                  卸载
                </el-button>
                <el-button 
                  v-else
                  type="primary" 
                  size="small"
                  plain
                  :loading="skill.installing"
                  @click="skillStore.installSkill(skill)"
                >
                  安装
                </el-button>
              </div>
            </template>
            <div class="card-body">
              <p class="skill-desc">{{ skill.description }}</p>
              <a :href="skill.repo_url" target="_blank" class="repo-link">
                <el-icon><Link /></el-icon> GitHub
              </a>
            </div>
          </el-card>
        </div>
      </div>
      
      <el-empty v-if="!skillStore.loading && skillStore.sections.length === 0" description="No skills found" />
    </el-scrollbar>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useSkillStore } from '@/stores/skill'
import { Refresh, Link } from '@element-plus/icons-vue'

const skillStore = useSkillStore()

onMounted(() => {
  if (skillStore.sections.length === 0) {
    skillStore.fetchSkills()
  }
})

function refreshSkills() {
  skillStore.fetchSkills()
}
</script>

<style scoped>
.skills-registry {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color-light);
  margin-bottom: 12px;
}
.header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.skills-list {
  flex: 1;
  padding-right: 12px;
}
.skill-section {
  margin-bottom: 24px;
}
.section-title {
  font-size: 15px;
  margin: 0 0 4px 0;
  color: var(--el-text-color-primary);
}
.section-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin: 0 0 12px 0;
}
.cards-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.skill-card {
  --el-card-padding: 12px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.skill-name {
  font-weight: 600;
  font-size: 14px;
}
.card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.skill-desc {
  font-size: 13px;
  color: var(--el-text-color-regular);
  margin: 0;
  line-height: 1.4;
}
.repo-link {
  font-size: 12px;
  color: var(--el-color-primary);
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 4px;
}
.repo-link:hover {
  text-decoration: underline;
}
</style>
