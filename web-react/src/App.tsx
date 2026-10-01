import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import {
  Alert, Avatar, Badge, Button, Card, Col, Descriptions, Divider, Drawer, Empty, Form, Input,
  InputNumber, Layout, List, Menu, Progress, Row, Space, Spin, Statistic, Table, Tag, Typography,
  message,
} from 'antd'
import type { MenuProps, TableColumnsType } from 'antd'
import {
  AlertOutlined, ApartmentOutlined, ArrowRightOutlined, BarChartOutlined, DatabaseOutlined,
  InboxOutlined, LogoutOutlined, RadarChartOutlined, RobotOutlined,
  SafetyCertificateOutlined, SendOutlined, ShoppingCartOutlined, ThunderboltOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import { api, getErrorMessage } from './api'
import type { Dashboard, HeatmapItem, Impact, RiskEvent, User } from './types'
import { AssistantWorkspace, InventoryWorkspace, ProcurementWorkspace, SalesWorkspace, SustainabilityWorkspace } from './erp'
import { AgentDashboardWorkspace } from './agents'

const { Header, Sider, Content } = Layout
const { Title, Text, Paragraph } = Typography

type PageKey = 'overview' | 'events' | 'whatif' | 'assistant' | 'inventory' | 'procurement' | 'sales' | 'sustainability' | 'agents' | 'data'

function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [form] = Form.useForm(); const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const submit = async (values: { username: string; password: string }) => {
    setLoading(true); setError('')
    try { const { data } = await api.post('/auth/login', values); onLogin(data); message.success('登入成功') }
    catch (e) { setError(getErrorMessage(e)) } finally { setLoading(false) }
  }
  return <div className="login-screen">
    <div className="login-orbit orbit-one" /><div className="login-orbit orbit-two" />
    <Card className="login-panel" bordered={false}>
      <div className="login-logo"><span>AI</span><div><b>RiskOps</b><small>Supply Chain Intelligence</small></div></div>
      <Tag color="blue" bordered={false} className="login-tag">AI-FIRST OPERATIONS</Tag>
      <Title level={1}>讓風險先被看見，<br /><span>再做供應鏈決策。</span></Title>
      <Paragraph className="login-copy">用事件訊號、影響鏈與 AI 情境分析，把複雜的供應鏈風險轉成下一步行動。</Paragraph>
      <Form form={form} layout="vertical" initialValues={{ username: 'planner', password: 'planner' }} onFinish={submit}>
        <Form.Item name="username" label="帳號" rules={[{ required: true, message: '請輸入帳號' }]}><Input size="large" prefix={<ApartmentOutlined />} /></Form.Item>
        <Form.Item name="password" label="密碼" rules={[{ required: true, message: '請輸入密碼' }]}><Input.Password size="large" prefix={<SafetyCertificateOutlined />} /></Form.Item>
        {error && <Alert className="login-error" message={error} type="error" showIcon />}
        <Button type="primary" htmlType="submit" size="large" block loading={loading} icon={<ArrowRightOutlined />} iconPosition="end">進入風險工作台</Button>
      </Form>
      <div className="demo-hint"><span className="live-dot" /> Demo account <code>planner / planner</code></div>
    </Card>
  </div>
}

function RiskProgress({ value }: { value: number }) {
  const level = value >= 70 ? '高' : value >= 40 ? '中' : '低'
  const color = value >= 70 ? '#f04438' : value >= 40 ? '#f79009' : '#12b76a'
  return <div className="risk-progress"><Progress percent={Math.round(value)} showInfo={false} strokeColor={color} trailColor="#eef2f6" size="small" /><Tag color={value >= 70 ? 'red' : value >= 40 ? 'orange' : 'green'} bordered={false}>{level}</Tag></div>
}

function Overview({ dashboard, loading, onReload, onInspect }: { dashboard: Dashboard | null; loading: boolean; onReload: () => void; onInspect: (event: RiskEvent) => void }) {
  const heatmapColumns: TableColumnsType<HeatmapItem> = [
    { title: '風險熱點', dataIndex: 'display_name', render: (value: string, item) => <div className="region-cell"><span className="region-pulse" style={{ background: item.risk_pct >= 70 ? '#f04438' : item.risk_pct >= 40 ? '#f79009' : '#12b76a' }} />{value}</div> },
    { title: '風險指數', dataIndex: 'risk_pct', width: 190, render: (value: number) => <RiskProgress value={value} /> },
    { title: 'AI 摘要', dataIndex: 'ai_summary', ellipsis: true, render: (value: string | null) => value || <Text type="secondary">等待事件分析</Text> },
  ]
  return <>
    <div className="hero-row"><div><Text className="eyebrow">AI SUPPLY CHAIN RISK / COMMAND CENTER</Text><Title>先看風險，再做決策。</Title><Paragraph>把事件、供應商、訂單與庫存串成可追蹤的影響鏈。</Paragraph></div><Button icon={<ThunderboltOutlined />} onClick={onReload} loading={loading}>重新整理</Button></div>
    <Row gutter={[16, 16]} className="stat-row">
      <Col xs={24} md={8}><Card className="stat-card stat-blue" bordered={false}><Statistic title="近 30 日風險事件" value={dashboard?.kpis.event_count ?? 0} prefix={<AlertOutlined />} /><Text type="secondary">事件訊號</Text></Card></Col>
      <Col xs={24} md={8}><Card className="stat-card stat-orange" bordered={false}><Statistic title="受影響供應商" value={dashboard?.kpis.supplier_count ?? 0} prefix={<ApartmentOutlined />} /><Text type="secondary">去重後估算</Text></Card></Col>
      <Col xs={24} md={8}><Card className="stat-card stat-purple" bordered={false}><Statistic title="受影響銷售訂單" value={dashboard?.kpis.order_count ?? 0} prefix={<WarningOutlined />} /><Text type="secondary">待處理訂單</Text></Card></Col>
    </Row>
    <Row gutter={[18, 18]}>
      <Col xs={24} xl={15}><Card className="surface-card" title={<span><RadarChartOutlined /> 地區風險熱點</span>} extra={<Tag color="blue">資料驅動</Tag>}><Table rowKey="region_key" columns={heatmapColumns} dataSource={dashboard?.heatmap || []} loading={loading} pagination={{ pageSize: 6, hideOnSinglePage: true }} /></Card></Col>
      <Col xs={24} xl={9}><Card className="surface-card event-card" title={<span><WarningOutlined /> 最近風險事件</span>} extra={<Badge count={dashboard?.events.length || 0} showZero color="#f79009" />}>
        {dashboard?.events.length ? <List dataSource={dashboard.events} renderItem={(event) => <List.Item className="event-item" onClick={() => onInspect(event)}><span className="event-icon"><AlertOutlined /></span><div className="event-copy"><b>{event.event_type}</b><small>{event.region} {event.country || ''}</small><small>{event.created_at}</small></div><Tag color="orange">+{event.impact_days}天</Tag></List.Item>} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="目前沒有事件" />}
      </Card></Col>
    </Row>
  </>
}

function EventWorkspace({ dashboard, canWrite, onCreated, onInspect }: { dashboard: Dashboard | null; canWrite: boolean; onCreated: () => void; onInspect: (event: RiskEvent) => void }) {
  const [form] = Form.useForm(); const [loading, setLoading] = useState(false)
  const create = async (values: Record<string, unknown>) => { setLoading(true); try { await api.post('/risk/events', values); message.success('風險事件已建立'); form.resetFields(); onCreated() } catch (e) { message.error(getErrorMessage(e)) } finally { setLoading(false) } }
  return <><div className="hero-row"><div><Text className="eyebrow">SIGNAL WORKSPACE</Text><Title>風險事件工作區</Title><Paragraph>把外部訊號轉成可分析、可追蹤的風險事件。</Paragraph></div></div>
    {canWrite && <Card className="surface-card create-card" title={<span><ThunderboltOutlined /> 新增 Demo 風險事件</span>}><Form form={form} layout="vertical" onFinish={create}><Row gutter={12}><Col xs={24} md={7}><Form.Item name="event_type" label="事件類型" initialValue="航運中斷" rules={[{ required: true }]}><Input /></Form.Item></Col><Col xs={24} md={5}><Form.Item name="region" label="地區" initialValue="中東" rules={[{ required: true }]}><Input /></Form.Item></Col><Col xs={24} md={5}><Form.Item name="impact_days" label="預估延遲天數" initialValue={14} rules={[{ required: true }]}><InputNumber min={0} max={365} className="full-input" /></Form.Item></Col><Col xs={24} md={7}><Form.Item name="description" label="描述" initialValue="模擬航線中斷情境"><Input /></Form.Item></Col></Row><Button type="primary" htmlType="submit" loading={loading} icon={<SendOutlined />}>建立事件</Button></Form></Card>}
    <Card className="surface-card" title="事件列表"><Table rowKey="id" dataSource={dashboard?.events || []} columns={[{ title: '事件', dataIndex: 'event_type' }, { title: '地區', dataIndex: 'region' }, { title: '國家', dataIndex: 'country', render: (v: string | null) => v || '—' }, { title: '預估延遲', dataIndex: 'impact_days', render: (v: number) => <Tag color="orange">+{v} 天</Tag> }, { title: '操作', render: (_: unknown, event: RiskEvent) => <Button type="link" onClick={() => onInspect(event)}>查看影響鏈 <ArrowRightOutlined /></Button> }]} pagination={{ pageSize: 8 }} /></Card>
  </>
}

function ScenarioWorkspace({ canRun }: { canRun: boolean }) {
  const [question, setQuestion] = useState('如果中東航線延遲 14 天，哪些供應商、採購單與庫存會受到影響？'); const [answer, setAnswer] = useState(''); const [loading, setLoading] = useState(false)
  const run = async () => { setLoading(true); try { const { data } = await api.post('/risk/what-if', { question }); setAnswer(data.answer) } catch (e) { setAnswer(getErrorMessage(e)) } finally { setLoading(false) } }
  return <><div className="hero-row"><div><Text className="eyebrow">DECISION SIMULATOR</Text><Title>What-if 情境模擬</Title><Paragraph>用自然語言詢問中斷情境的影響與應對優先順序。</Paragraph></div><Tag color="purple" icon={<RobotOutlined />}>AI ANALYSIS</Tag></div><Card className="scenario-card" bordered={false}><div className="scenario-heading"><div className="scenario-icon"><RobotOutlined /></div><div><Title level={4}>問問你的供應鏈</Title><Text type="secondary">AI 會讀取供應商、採購單與庫存等 ERP 證據。</Text></div></div><Input.TextArea value={question} onChange={(event) => setQuestion(event.target.value)} autoSize={{ minRows: 4, maxRows: 8 }} /><div className="scenario-actions"><Text type="secondary">目前使用虛擬資料</Text><Button type="primary" onClick={run} loading={loading} disabled={!canRun || question.length < 5} icon={<ThunderboltOutlined />}>開始分析</Button></div>{answer && <Alert className="scenario-answer" message="分析結果" description={<pre>{answer}</pre>} type="success" showIcon />}{!canRun && <Alert className="scenario-permission" message="此帳號沒有 What-if 分析權限" type="warning" showIcon />}</Card></>
}

function ImpactDrawer({ event, impact, open, onClose }: { event: RiskEvent | null; impact: Impact | null; open: boolean; onClose: () => void }) {
  return <Drawer title="事件影響鏈" open={open} onClose={onClose} width={780}><Alert className="drawer-summary" type="warning" showIcon message={event ? `${event.event_type} · ${event.region} ${event.country || ''} · 延遲 ${event.impact_days} 天` : '載入中'} /><Divider /><Descriptions column={2} size="small" bordered><Descriptions.Item label="受影響供應商">{impact?.suppliers.length ?? 0}</Descriptions.Item><Descriptions.Item label="受影響訂單">{impact?.orders.length ?? 0}</Descriptions.Item><Descriptions.Item label="庫存警示">{impact?.stockout_alerts.length ?? 0}</Descriptions.Item><Descriptions.Item label="事件描述">{event?.description || '—'}</Descriptions.Item></Descriptions><Divider /><Title level={5}>供應商</Title><Table size="small" rowKey={(row) => String(row.supplier_id)} dataSource={impact?.suppliers || []} columns={[{ title: '名稱', dataIndex: 'name' }, { title: '國家', dataIndex: 'country' }, { title: '風險', dataIndex: 'risk_level' }]} pagination={false} locale={{ emptyText: '沒有受影響供應商' }} /><Title level={5} className="drawer-subtitle">庫存警示</Title><Table size="small" rowKey={(row) => String(row.product_id)} dataSource={impact?.stockout_alerts || []} columns={[{ title: '商品', dataIndex: 'product_name' }, { title: '現有庫存', dataIndex: 'stock' }, { title: '警示', dataIndex: 'risk_level' }]} pagination={false} locale={{ emptyText: '沒有庫存警示' }} /></Drawer>
}

function Shell({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [page, setPage] = useState<PageKey>('overview'); const [dashboard, setDashboard] = useState<Dashboard | null>(null); const [loading, setLoading] = useState(false); const [drawer, setDrawer] = useState(false); const [selected, setSelected] = useState<RiskEvent | null>(null); const [impact, setImpact] = useState<Impact | null>(null)
  const load = async () => { setLoading(true); try { setDashboard((await api.get('/risk/dashboard')).data) } catch (e) { message.error(getErrorMessage(e)) } finally { setLoading(false) } }
  useEffect(() => { void load() }, [])
  const inspect = async (event: RiskEvent) => { setSelected(event); setImpact(null); setDrawer(true); try { setImpact((await api.get(`/risk/events/${event.id}/impact`)).data) } catch (e) { message.error(getErrorMessage(e)) } }
  const items: MenuProps['items'] = [
    { key: 'overview', icon: <BarChartOutlined />, label: '風險總覽' }, { key: 'events', icon: <AlertOutlined />, label: '風險事件' }, { key: 'whatif', icon: <RobotOutlined />, label: '情境模擬' }, { key: 'assistant', icon: <RobotOutlined />, label: 'AI 助理' },
    { type: 'divider' }, { key: 'inventory', icon: <InboxOutlined />, label: '庫存作業' }, { key: 'procurement', icon: <ShoppingCartOutlined />, label: '採購作業' }, { key: 'sales', icon: <ArrowRightOutlined />, label: '銷售作業' },
    { key: 'sustainability', icon: <RadarChartOutlined />, label: '碳排與供應鏈' }, { key: 'agents', icon: <RobotOutlined />, label: 'Agent Dashboard' }, { key: 'data', icon: <DatabaseOutlined />, label: 'ERP 資料入口' },
  ]
  const title = { overview: '風險指揮中心', events: '風險事件工作區', whatif: 'What-if 情境模擬', assistant: 'AI 供應鏈助理', inventory: '庫存作業', procurement: '採購作業', sales: '銷售作業', sustainability: '碳排與供應鏈', agents: 'Agent Dashboard', data: 'ERP 資料入口' }[page]
  return <Layout className="app-layout"><Sider className="app-sider" width={260} breakpoint="lg" collapsedWidth={0}><div className="sider-brand"><div className="brand-square">AI</div><div><b>RiskOps</b><small>Supply Chain Intelligence</small></div></div><div className="sider-context"><span className="status-dot" /> LIVE DEMO ENVIRONMENT</div><Menu theme="dark" mode="inline" selectedKeys={[page]} items={items} onClick={({ key }) => setPage(key as PageKey)} /><div className="sider-bottom"><div className="user-chip"><Avatar size={34} style={{ background: '#315efb' }}>{user.name.slice(0, 1)}</Avatar><div><b>{user.name}</b><small>{user.role}</small></div></div><Button type="text" icon={<LogoutOutlined />} onClick={onLogout} className="logout-button">登出</Button></div></Sider><Layout><Header className="app-header"><div><Text className="header-kicker">AI SUPPLY CHAIN RISK</Text><Title level={3}>{title}</Title></div><Space><Tag color="green" bordered={false}><span className="small-dot" /> Demo data</Tag><Avatar icon={<SafetyCertificateOutlined />} /></Space></Header><Content className="app-content">{page === 'overview' && <Overview dashboard={dashboard} loading={loading} onReload={() => void load()} onInspect={inspect} />}{page === 'events' && <EventWorkspace dashboard={dashboard} canWrite={user.capabilities.includes('risk.workspace.write')} onCreated={() => void load()} onInspect={inspect} />}{page === 'whatif' && <ScenarioWorkspace canRun={user.capabilities.includes('risk.what_if.run')} />}{page === 'assistant' && <AssistantWorkspace canRun={user.capabilities.includes('risk.analysis.read')} />}{page === 'inventory' && <InventoryWorkspace />}{page === 'procurement' && <ProcurementWorkspace />}{page === 'sales' && <SalesWorkspace />}{page === 'sustainability' && <SustainabilityWorkspace />}{page === 'agents' && <AgentDashboardWorkspace user={user} />}{page === 'data' && <><div className="hero-row"><div><Text className="eyebrow">EVIDENCE LAYER</Text><Title>ERP 資料入口</Title><Paragraph>ERP 是風險分析的資料底座，不是主要決策介面。</Paragraph></div></div><Card className="surface-card"><Alert message="已將庫存、採購、銷售、AI 助理與碳排／供應鏈資料接入 React；財務與人資仍保留在 Streamlit。" type="info" showIcon /></Card></>}</Content></Layout><ImpactDrawer event={selected} impact={impact} open={drawer} onClose={() => setDrawer(false)} /></Layout>
}

export default function App() {
  const [user, setUser] = useState<User | null>(null); const [checking, setChecking] = useState(true)
  useEffect(() => { api.get('/auth/me').then(({ data }) => setUser(data)).catch(() => undefined).finally(() => setChecking(false)) }, [])
  const logout = async () => { await api.post('/auth/logout').catch(() => undefined); setUser(null) }
  if (checking) return <div className="loading-screen"><Spin size="large" /><Text>載入風險工作台…</Text></div>
  return user ? <Shell user={user} onLogout={logout} /> : <Login onLogin={setUser} />
}
