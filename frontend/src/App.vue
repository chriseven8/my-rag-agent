<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <el-container class="app-shell">
    <el-header class="app-header">
      <div class="brand">my-rag-agent</div>
      <el-menu mode="horizontal" :default-active="route.path" router :ellipsis="false" class="nav-menu">
        <el-menu-item index="/">对话问答</el-menu-item>
        <el-menu-item index="/documents">文档管理</el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
}
.app-header {
  display: flex;
  align-items: center;
  gap: 28px;
  border-bottom: 1px solid var(--el-border-color-light);
}
.brand {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-color-primary);
  white-space: nowrap;
}
.nav-menu {
  flex: 1;
  border-bottom: none;
}
.app-main {
  background: var(--el-bg-color-page);
}
</style>
