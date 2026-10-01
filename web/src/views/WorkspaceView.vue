<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api, errorMessage } from '../api'
import { useAuthStore } from '../stores/auth'
import type { Dashboard, RiskEvent, HeatmapItem } from '../types'

const auth = useAuthStore(); const router = useRouter()
const dashboard = ref<Dashboard | null>(null); const loading = ref(false); const active = ref('overview'); const selectedEvent = ref<RiskEvent | null>(null); const dialogVisible = ref(false); const impact = ref<any>(null)
const question = ref('如果中東航線延遲 14 天，哪些供應商、採購單與庫存會受到影響？'); const answer = ref(''); const creating = ref(false)
const eventForm = ref({ event_type: '航運中斷', region: '中東', country: '', impact_days: 14, description: '模擬航線中斷情境' })
const canWrite = computed(() => auth.user?.capabilities.includes('risk.workspace.write'))
const canWhatIf = computed(() => auth.user?.capabilities.includes('risk.what_if.run'))
async function load() { loading.value = true; try { dashboard.value = (await api.get('/risk/dashboard')).data } catch (e) { ElMessage.error(errorMessage(e)) } finally { loading.value = false } }
async function showImpact(event: RiskEvent) { selectedEvent.value = event; impact.value = null; dialogVisible.value = true; try { impact.value = (await api.get(`/risk/events/${event.id}/impact`)).data } catch (e) { ElMessage.error(errorMessage(e)) } }
async function createEvent() { creating.value = true; try { await api.post('/risk/events', eventForm.value); ElMessage.success('風險事件已建立'); await load() } catch (e) { ElMessage.error(errorMessage(e)) } finally { creating.value = false } }
async function runWhatIf() { try { answer.value = (await api.post('/risk/what-if', { question: question.value })).data.answer } catch (e) { answer.value = errorMessage(e) } }
async function logout() { await auth.logout(); router.push('/login') }
function riskType(item: HeatmapItem) { return item.risk_pct >= 70 ? 'exception' : item.risk_pct >= 40 ? 'warning' : 'success' }
onMounted(async () => { if (!auth.user) await auth.restore(); if (!auth.user) { router.push('/login'); return }; await load() })
</script>

<template>
  <el-container class="app-shell" v-if="auth.user">
    <el-aside width="250px" class="sidebar"><div class="side-brand"><span class="brand-mark small">AI</span><div><b>RiskOps</b><small>Supply Chain Intelligence</small></div></div>
      <el-menu :default-active="active" @select="(key: string) => active = key" class="side-menu"><el-menu-item index="overview">風險總覽</el-menu-item><el-menu-item index="events">風險事件</el-menu-item><el-menu-item index="whatif">情境模擬</el-menu-item><el-menu-item index="data">ERP 證據資料</el-menu-item></el-menu>
      <div class="side-foot"><span>{{ auth.user.name }} · {{ auth.user.role }}</span><el-button link @click="logout">登出</el-button></div>
    </el-aside>
    <el-container><el-header class="topbar"><div><span class="eyebrow">AI SUPPLY CHAIN RISK</span><h2>{{ active === 'overview' ? '風險指揮中心' : active === 'events' ? '風險事件工作區' : active === 'whatif' ? 'What-if 情境模擬' : 'ERP 證據資料' }}</h2></div><el-tag type="success" effect="light">Demo data</el-tag></el-header>
      <el-main class="main-content">
        <template v-if="active === 'overview'"><div class="page-intro"><div><h1>先看風險，再做決策</h1><p>把事件、供應商、訂單與庫存串成可追蹤的影響鏈。</p></div><el-button :loading="loading" @click="load">重新整理</el-button></div>
          <div class="kpi-grid"><el-card><span class="kpi-label">近 30 日風險事件</span><strong>{{ dashboard?.kpis.event_count ?? '-' }}</strong><span class="kpi-note">事件訊號</span></el-card><el-card><span class="kpi-label">受影響供應商</span><strong>{{ dashboard?.kpis.supplier_count ?? '-' }}</strong><span class="kpi-note">去重後估算</span></el-card><el-card><span class="kpi-label">受影響銷售訂單</span><strong>{{ dashboard?.kpis.order_count ?? '-' }}</strong><span class="kpi-note">待處理訂單</span></el-card></div>
          <div class="two-col"><el-card class="panel"><template #header><div class="panel-title"><span>地區風險熱點</span><el-tag size="small">資料驅動</el-tag></div></template><el-table :data="dashboard?.heatmap || []" stripe><el-table-column prop="display_name" label="地區" min-width="150"/><el-table-column label="風險" width="170"><template #default="{ row }"><el-progress :percentage="Math.round(row.risk_pct || 0)" :status="riskType(row)" :stroke-width="10"/></template></el-table-column><el-table-column label="等級" width="80"><template #default="{ row }">{{ row.risk_pct >= 70 ? '高' : row.risk_pct >= 40 ? '中' : '低' }}</template></el-table-column></el-table></el-card>
            <el-card class="panel"><template #header><div class="panel-title"><span>最近風險事件</span><el-button link @click="active = 'events'">查看全部</el-button></div></template><div v-if="dashboard?.events?.length" class="event-list"><button v-for="event in dashboard.events" :key="event.id" class="event-row" @click="showImpact(event)"><span class="event-dot"></span><span class="event-main"><b>{{ event.event_type }}</b><small>{{ event.region }} {{ event.country }} · {{ event.created_at }}</small></span><el-tag size="small" type="warning">+{{ event.impact_days }} 天</el-tag></button></div><el-empty v-else description="目前沒有事件"/></el-card></div>
        </template>
        <template v-else-if="active === 'events'"><div class="page-intro"><div><h1>風險事件</h1><p>建立可追蹤的事件訊號，並分析其對供應鏈的影響。</p></div></div><el-card class="panel" v-if="canWrite"><template #header><span>新增事件（Demo）</span></template><el-form :model="eventForm" inline><el-form-item label="類型"><el-input v-model="eventForm.event_type"/></el-form-item><el-form-item label="地區"><el-input v-model="eventForm.region"/></el-form-item><el-form-item label="延遲天數"><el-input-number v-model="eventForm.impact_days" :min="0" :max="365"/></el-form-item><el-form-item><el-button type="primary" :loading="creating" @click="createEvent">建立事件</el-button></el-form-item></el-form></el-card><el-card class="panel"><el-table :data="dashboard?.events || []"><el-table-column prop="event_type" label="事件"/><el-table-column prop="region" label="地區"/><el-table-column prop="country" label="國家"/><el-table-column prop="impact_days" label="預估延遲"/><el-table-column label="影響分析"><template #default="{ row }"><el-button link type="primary" @click="showImpact(row)">查看影響鏈</el-button></template></el-table-column></el-table></el-card></template>
        <template v-else-if="active === 'whatif'"><div class="page-intro"><div><h1>What-if 情境模擬</h1><p>用自然語言詢問供應鏈中斷的影響與應對優先順序。</p></div></div><el-card class="panel"><el-alert title="AI 分析會讀取供應商、採購單與庫存等 ERP 證據；目前未設定模型金鑰時會回傳清楚的不可用狀態。" type="info" show-icon :closable="false"/><el-input v-model="question" type="textarea" :rows="5" class="whatif-input"/><el-button type="primary" :disabled="!canWhatIf" @click="runWhatIf">開始分析</el-button><el-alert v-if="answer" class="answer" :title="answer" type="success" show-icon :closable="false"/></el-card></template>
        <template v-else><div class="page-intro"><div><h1>ERP 證據資料</h1><p>ERP 在本系統是風險分析的資料底座，不是主要決策介面。</p></div></div><el-card class="panel"><el-alert title="此頁預留供應商、庫存、採購單明細；下一階段會補上篩選、匯出與治理流程。" type="info" show-icon :closable="false"/></el-card></template>
      </el-main>
    </el-container>
    <el-dialog v-model="dialogVisible" title="事件影響鏈" width="760px"><template v-if="impact"><p><b>{{ impact.event.event_type }}</b> · {{ impact.event.region }} {{ impact.event.country }} · 延遲 {{ impact.event.impact_days }} 天</p><el-tabs><el-tab-pane label="供應商"><el-table :data="impact.suppliers"><el-table-column prop="name" label="供應商"/><el-table-column prop="country" label="國家"/><el-table-column prop="risk_level" label="風險"/></el-table></el-tab-pane><el-tab-pane label="銷售訂單"><el-table :data="impact.orders"><el-table-column prop="order_id" label="訂單"/><el-table-column prop="customer_name" label="客戶"/><el-table-column prop="new_delivery" label="預估交期"/></el-table></el-tab-pane><el-tab-pane label="庫存警示"><el-table :data="impact.stockout_alerts"><el-table-column prop="product_name" label="商品"/><el-table-column prop="stock" label="現有庫存"/><el-table-column prop="risk_level" label="警示"/></el-table></el-tab-pane></el-tabs></template><el-skeleton v-else :rows="4" animated/></el-dialog>
  </el-container>
</template>
