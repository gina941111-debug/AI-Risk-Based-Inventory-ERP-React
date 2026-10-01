export interface User { username: string; name: string; role: string; capabilities: string[]; organization_id?: string }
export interface RiskEvent { id: number; event_type: string; region: string; country: string | null; impact_days: number; description: string; created_at: string }
export interface HeatmapItem { region_key: string; display_name: string; risk_pct: number; ai_summary?: string | null; updated_at?: string | null }
export interface Dashboard { kpis: { event_count: number; supplier_count: number; order_count: number }; heatmap: HeatmapItem[]; events: RiskEvent[]; region_procurement_share: Record<string, unknown> }
export interface Impact { event: RiskEvent; suppliers: Record<string, unknown>[]; orders: Record<string, unknown>[]; stockout_alerts: Record<string, unknown>[] }
