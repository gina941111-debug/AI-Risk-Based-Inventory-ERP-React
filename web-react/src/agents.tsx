import { useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Col, Form, Input, InputNumber, Row, Select,
  Space, Spin, Statistic, Switch, Table, Tag, Typography, message,
} from 'antd'
import type { TableColumnsType } from 'antd'
import {
  ApartmentOutlined, CheckCircleOutlined, ClockCircleOutlined, DeploymentUnitOutlined,
  ExclamationCircleOutlined, MessageOutlined, SafetyCertificateOutlined, SendOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import { api, getErrorMessage } from './api'
import type { User } from './types'

const { Title, Text, Paragraph } = Typography

type Props = { user: User }

function HeaderBlock() {
  return <div className="hero-row"><div><Text className="eyebrow">AGENT OPERATIONS / GOVERNANCE</Text><Title>Agent Dashboard</Title><Paragraph>查看 8 個 Agent 的責任邊界、派工決策、工具呼叫、審批治理與製造證據。</Paragraph></div><Tag color="purple" icon={<DeploymentUnitOutlined />}>ORCHESTRATOR CONNECTED</Tag></div>
}

export function AgentDashboardWorkspace({ user }: Props) {
  const [agents, setAgents] = useState<any[]>([]); const [dispatches, setDispatches] = useState<any[]>([]); const [actions, setActions] = useState<any[]>([])
  const [approvals, setApprovals] = useState<any[]>([]); const [proposals, setProposals] = useState<any[]>([]); const [options, setOptions] = useState<any[]>([])
  const [manufacturing, setManufacturing] = useState<any>({ bom: [], work_orders: [] }); const [loading, setLoading] = useState(true)
  const canPropose = user.capabilities.includes('erp.exchange.propose'); const canApprove = user.capabilities.includes('approval.decide'); const canReadQueue = user.capabilities.includes('approval.queue.read')
  const load = async () => {
    setLoading(true)
    try {
      const base = await Promise.all([api.get('/agents/overview'), api.get('/agents/dispatch-logs'), api.get('/agents/action-logs'), api.get('/agents/manufacturing'), api.get('/agents/proposals')])
      setAgents(base[0].data.agents || []); setDispatches(base[1].data.items || []); setActions(base[2].data.items || []); setManufacturing(base[3].data); setProposals(base[4].data.items || [])
      if (canReadQueue) { const res = await api.get('/agents/approvals', { params: { status: 'pending' } }); setApprovals(res.data.items || []) }
      if (canPropose) { const res = await api.get('/agents/proposals/options'); setOptions(res.data.items || []) }
    } catch (e) { message.error(getErrorMessage(e)) } finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [])

  const decide = async (approvalId: string, outcome: 'approve' | 'reject') => {
    const reason = outcome === 'reject' ? window.prompt('請輸入拒絕原因') || '' : ''
    if (outcome === 'reject' && !reason.trim()) return
    try { await api.post(`/agents/approvals/${approvalId}/decision`, { outcome, reason }); message.success(outcome === 'approve' ? '已核准並執行' : '已拒絕'); await load() } catch (e) { message.error(getErrorMessage(e)) }
  }

  const agentColumns: TableColumnsType<any> = [{ title: 'Agent', dataIndex: 'name_zh', render: (v, row) => <div><b>{v}</b><small className="cell-secondary">{row.id}</small></div> }, { title: '負責模組', dataIndex: 'modules', render: (v: string[]) => v.length ? v.map((item) => <Tag key={item}>{item}</Tag>) : <Tag>fallback</Tag> }, { title: '工具數', render: (_, row) => <BadgeValue value={row.tools?.length || 0} /> }, { title: '寫入能力', dataIndex: 'can_write', render: (v) => v ? <Tag color="orange">需治理</Tag> : <Tag color="green">唯讀</Tag> }, { title: '工具白名單', dataIndex: 'tools', render: (v: string[]) => <Text ellipsis={{ tooltip: v.join(', ') }}>{v.join(', ') || '—'}</Text> }]
  const dispatchColumns: TableColumnsType<any> = [{ title: '時間', dataIndex: 'timestamp' }, { title: '任務', dataIndex: 'task', ellipsis: true }, { title: '主責 Agent', dataIndex: 'primary_agent' }, { title: '派工鏈', dataIndex: 'agent_chain', render: (v: string[]) => v?.join(' → ') }, { title: '來源', dataIndex: 'routed_by' }, { title: '審批', dataIndex: 'needs_approval', render: (v) => v ? <Tag color="orange">需要</Tag> : <Tag color="green">不需要</Tag> }]
  const actionColumns: TableColumnsType<any> = [{ title: '時間', dataIndex: 'timestamp' }, { title: 'Agent', dataIndex: 'agent' }, { title: '工具', dataIndex: 'tool_name' }, { title: '呼叫者', dataIndex: 'caller' }, { title: '結果', dataIndex: 'success', render: (v) => v ? <Tag color="green">成功</Tag> : <Tag color="red">失敗</Tag> }]
  const approvalColumns: TableColumnsType<any> = [{ title: '審批單', dataIndex: 'approval_id', ellipsis: true }, { title: '工具', dataIndex: 'tool_name' }, { title: '請求者', dataIndex: 'requester_username' }, { title: '時間', dataIndex: 'created_at' }, { title: '操作', render: (_, row) => canApprove ? <Space><Button size="small" type="primary" icon={<CheckCircleOutlined />} onClick={() => void decide(row.approval_id, 'approve')}>核准</Button><Button size="small" danger onClick={() => void decide(row.approval_id, 'reject')}>拒絕</Button></Space> : <Tag>唯讀</Tag> }]

  return <><HeaderBlock /><Spin spinning={loading}><Row gutter={[16, 16]} className="stat-row"><Col xs={24} md={6}><Card className="stat-card stat-blue" bordered={false}><Statistic title="Agent 數" value={agents.length} prefix={<ApartmentOutlined />} /></Card></Col><Col xs={24} md={6}><Card className="stat-card stat-purple" bordered={false}><Statistic title="派工紀錄" value={dispatches.length} prefix={<DeploymentUnitOutlined />} /></Card></Col><Col xs={24} md={6}><Card className="stat-card stat-orange" bordered={false}><Statistic title="工具呼叫" value={actions.length} prefix={<ToolOutlined />} /></Card></Col><Col xs={24} md={6}><Card className="stat-card stat-red" bordered={false}><Statistic title="待審批" value={approvals.length} prefix={<ClockCircleOutlined />} /></Card></Col></Row>
    <Card className="surface-card" title={<span><ApartmentOutlined /> 8 個 Agent 的狀態與工具清單</span>} style={{ marginBottom: 18 }}><Table rowKey="id" columns={agentColumns} dataSource={agents} pagination={{ pageSize: 8 }} /></Card>
    <Row gutter={[18, 18]}><Col xs={24} xl={14}><Card className="surface-card" title={<span><DeploymentUnitOutlined /> Agent Orchestrator 派工紀錄</span>}><Table rowKey="id" size="small" columns={dispatchColumns} dataSource={dispatches} pagination={{ pageSize: 6 }} /></Card></Col><Col xs={24} xl={10}><Card className="surface-card" title={<span><ToolOutlined /> Agent 工具呼叫紀錄</span>}><Table rowKey="id" size="small" columns={actionColumns} dataSource={actions} pagination={{ pageSize: 6 }} /></Card></Col></Row>
    <Row gutter={[18, 18]} style={{ marginTop: 18 }}><Col xs={24} xl={15}><Card className="surface-card" title={<span><SafetyCertificateOutlined /> 待審批清單</span>} extra={!canReadQueue && <Tag>此帳號無審批讀取權限</Tag>}><Table rowKey="approval_id" columns={approvalColumns} dataSource={approvals} pagination={{ pageSize: 6 }} locale={{ emptyText: canReadQueue ? '目前沒有待審批項目' : '請使用採購審批者或管理者帳號' }} /></Card></Col><Col xs={24} xl={9}><ProposalPanel canPropose={canPropose} options={options} proposals={proposals} onChanged={load} /></Col></Row>
    <Row gutter={[18, 18]} style={{ marginTop: 18 }}><Col xs={24} xl={12}><Card className="surface-card" title={<span><DeploymentUnitOutlined /> Manufacturing Agent · BOM</span>}><Table rowKey="id" size="small" dataSource={manufacturing.bom} columns={[{ title: '成品', dataIndex: 'product_id' }, { title: '組成料件', dataIndex: 'component_id' }, { title: '用量', dataIndex: 'qty_per' }]} pagination={{ pageSize: 6 }} /></Card></Col><Col xs={24} xl={12}><Card className="surface-card" title={<span><ClockCircleOutlined /> Manufacturing Agent · 工單</span>}><Table rowKey="wo_id" size="small" dataSource={manufacturing.work_orders} columns={[{ title: '工單', dataIndex: 'wo_id' }, { title: '品項', dataIndex: 'product_id' }, { title: '進度', render: (_: unknown, row: any) => `${row.qty_done || 0} / ${row.qty_plan || 0}` }, { title: '狀態', dataIndex: 'status', render: (v) => <Tag color={v === '已完成' ? 'green' : 'blue'}>{v || '—'}</Tag> }]} pagination={{ pageSize: 6 }} /></Card></Col></Row>
    <CrossAgentChat />
  </Spin></>
}

function BadgeValue({ value }: { value: number }) { return <Tag color="blue">{value} tools</Tag> }

function ProposalPanel({ canPropose, options, proposals, onChanged }: { canPropose: boolean; options: any[]; proposals: any[]; onChanged: () => Promise<void> }) {
  const [form] = Form.useForm(); const [submitting, setSubmitting] = useState(false); const selected = Form.useWatch('source_po_item_id', form); const option = useMemo(() => options.find((item) => String(item.source_po_item_id) === String(selected)), [options, selected])
  const submit = async (values: any) => { setSubmitting(true); try { await api.post('/agents/proposals', { ...values, source_po_item_id: Number(values.source_po_item_id), affected_po_id: option.po_id, product_id: option.product_id, qty: undefined }); message.success('替代採購 Proposal 已送審'); form.resetFields(); await onChanged() } catch (e) { message.error(getErrorMessage(e)) } finally { setSubmitting(false) } }
  return <Card className="surface-card" title={<span><ExclamationCircleOutlined /> Purchase Proposal 證據頁</span>}><Table size="small" rowKey="proposal_id" dataSource={proposals} columns={[{ title: 'Proposal', dataIndex: 'proposal_id', ellipsis: true }, { title: '原 PO', dataIndex: 'affected_po_id' }, { title: '替代供應商', dataIndex: 'alternative_supplier_id' }, { title: '狀態', dataIndex: 'proposed_status', render: (v) => <Tag>{v || '待審'}</Tag> }]} pagination={{ pageSize: 4 }} locale={{ emptyText: '尚無 Proposal' }} />{canPropose && <><Text strong>建立替代供應 Proposal</Text><Form form={form} layout="vertical" onFinish={submit} style={{ marginTop: 12 }}><Form.Item name="source_po_item_id" label="受影響採購品項" rules={[{ required: true }]}><Select placeholder="選擇有延遲風險的採購品項" options={options.map((item) => ({ value: String(item.source_po_item_id), label: `${item.po_id} · ${item.product_id} · ${item.supplier_name}` }))} /></Form.Item><Form.Item name="alternative_supplier_id" label="替代供應商" rules={[{ required: true }]}><Input placeholder="輸入正式供應商 ID" /></Form.Item><Form.Item name="proposal_id" label="Proposal ID" rules={[{ required: true }]}><Input placeholder="例如 ALT-PO-001" /></Form.Item><Form.Item name="reason" label="替代原因" rules={[{ required: true }]}><Input.TextArea rows={2} placeholder="說明風險證據與替代理由" /></Form.Item><Form.Item name="estimated_delay_days" label="預估延遲天數"><InputNumber min={0} max={365} style={{ width: '100%' }} /></Form.Item><Button type="primary" htmlType="submit" loading={submitting} disabled={!option} icon={<SendOutlined />}>建立並送審</Button></Form></>}</Card>
}

function CrossAgentChat() {
  const [question, setQuestion] = useState('請彙整目前供應鏈風險、庫存與採購優先順序'); const [answer, setAnswer] = useState<any>(null); const [useLlm, setUseLlm] = useState(true); const [loading, setLoading] = useState(false)
  const run = async () => { setLoading(true); try { setAnswer((await api.post('/agents/chat', { message: question, use_llm: useLlm })).data) } catch (e) { setAnswer({ reply: getErrorMessage(e) }) } finally { setLoading(false) } }
  return <Card className="scenario-card" bordered={false} style={{ marginTop: 18 }}><div className="scenario-heading"><div className="scenario-icon"><MessageOutlined /></div><div><Title level={4}>客服 Agent 的跨 Agent 彙整介面</Title><Text type="secondary">由 Orchestrator 決定單一或多 Agent 派工；財務／人資不會出現為獨立工作區。</Text></div></div><Input.TextArea value={question} onChange={(e) => setQuestion(e.target.value)} autoSize={{ minRows: 3, maxRows: 6 }} /><Space style={{ marginTop: 12 }}><Switch checked={useLlm} onChange={setUseLlm} /><Text type="secondary">使用 LLM 實際執行（關閉可離線驗證路由）</Text><Button type="primary" icon={<MessageOutlined />} loading={loading} onClick={() => void run()} disabled={question.trim().length < 2}>送出任務</Button></Space>{answer && <Alert style={{ marginTop: 16 }} type="info" showIcon message={answer.routing ? `派工：${answer.routing.agent_chain?.join(' → ')}` : 'Agent 回覆'} description={<><pre style={{ whiteSpace: 'pre-wrap' }}>{answer.reply}</pre>{answer.pending?.length ? <Tag color="orange">有 {answer.pending.length} 筆操作等待審批</Tag> : null}</>} />}</Card>
}
