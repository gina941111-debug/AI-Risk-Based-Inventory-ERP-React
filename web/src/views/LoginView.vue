<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter(); const auth = useAuthStore()
const form = reactive({ username: 'planner', password: 'planner' })
async function submit() { if (await auth.login(form.username, form.password)) { ElMessage.success('登入成功'); router.push('/') } }
</script>

<template>
  <main class="login-page"><el-card class="login-card" shadow="always">
    <div class="brand-mark">AI</div><h1>供應鏈風險指揮中心</h1><p class="muted">AI 先行的風險監控、影響分析與決策工作台</p>
    <el-form :model="form" @submit.prevent="submit" label-position="top">
      <el-form-item label="帳號"><el-input v-model="form.username" autocomplete="username" /></el-form-item>
      <el-form-item label="密碼"><el-input v-model="form.password" type="password" show-password autocomplete="current-password" /></el-form-item>
      <el-alert v-if="auth.error" :title="auth.error" type="error" show-icon :closable="false" />
      <el-button class="full-width" type="primary" native-type="submit" :loading="auth.loading">進入風險工作台</el-button>
    </el-form>
    <p class="hint">Demo：planner / planner（可執行 What-if 與風險事件操作）</p>
  </el-card></main>
</template>
