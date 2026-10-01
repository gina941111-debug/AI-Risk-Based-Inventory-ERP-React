export interface User { username: string; name: string; role: string; capabilities: string[]; organization_id?: string }
export interface RiskEvent { id: number; event_type: string; region: string; country: string; impact_days: number; description: string; created_at: string; news_id?: number }
export interface HeatmapItem { region_key: string; display_name: string; risk_pct: number; ai_summary?: string; updated_at?: string }
export interface Dashboard { kpis: { event_count: number; supplier_count: number; order_count: number }; heatmap: HeatmapItem[]; events: RiskEvent[]; region_procurement_share: Record<string, any> }
