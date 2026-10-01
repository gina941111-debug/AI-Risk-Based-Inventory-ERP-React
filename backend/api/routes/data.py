from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.access_control import ERP_EXCHANGE_PROPOSE, RISK_OVERVIEW_READ, RISK_WORKSPACE_WRITE, AccessContext
from backend.api.dependencies import require
from backend.api.serializers import records
from backend.database import DB_FILE
from backend.orders import InsufficientStockError, OrderValidationError, create_sales_order, transition_order_status
from backend.tool_gateway import gateway
from backend import supply_chain_risk as risk


router = APIRouter(prefix="/data", tags=["data"])


class InventoryMoveRequest(BaseModel):
    product_id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(gt=0, le=1_000_000)
    move_type: str = Field(pattern="^(入庫|出庫)$")
    ref_no: str = Field(default="", max_length=120)
    note: str = Field(default="", max_length=500)


class SalesOrderRequest(BaseModel):
    order_id: str = Field(min_length=1, max_length=120)
    customer_id: str = Field(default="", max_length=80)
    product_id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(gt=0, le=1_000_000)
    status: str = Field(default="處理中", pattern="^(處理中|已出貨|已取消)$")


class OrderStatusRequest(BaseModel):
    status: str = Field(pattern="^(處理中|已出貨|已取消)$")


class PurchaseOrderRequest(BaseModel):
    po_id: str = Field(min_length=1, max_length=120)
    supplier_id: str = Field(min_length=1, max_length=80)
    product_id: str = Field(min_length=1, max_length=80)
    qty: int = Field(gt=0, le=1_000_000)
    unit_price: float = Field(ge=0)
    note: str = Field(default="", max_length=500)


def _query(sql: str, params=()):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
    conn.close()
    return records(rows)


@router.get("/suppliers", dependencies=[Depends(require(RISK_OVERVIEW_READ))])
def suppliers(limit: int = Query(default=100, ge=1, le=500)):
    return {"items": _query("SELECT supplier_id, name, country, region, risk_level FROM suppliers WHERE is_official=1 ORDER BY name LIMIT ?", (limit,))}


@router.get("/inventory", dependencies=[Depends(require(RISK_OVERVIEW_READ))])
def inventory(limit: int = Query(default=100, ge=1, le=500)):
    return {"items": _query("SELECT product_id, name, stock, reorder_point, daily_sales FROM inventory ORDER BY name LIMIT ?", (limit,))}


@router.post("/inventory/moves", status_code=201)
def create_inventory_move(payload: InventoryMoveRequest, principal: AccessContext = Depends(require(RISK_WORKSPACE_WRITE))):
    signed_qty = payload.quantity if payload.move_type == "入庫" else -payload.quantity
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_FILE, timeout=5.0)
    try:
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT name, stock, warehouse_id FROM inventory WHERE product_id = ?", (payload.product_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="找不到商品")
        name, current_stock, warehouse_id = row
        new_stock = int(current_stock or 0) + signed_qty
        if new_stock < 0:
            raise HTTPException(status_code=409, detail=f"庫存不足，目前只有 {current_stock} 件")
        conn.execute("UPDATE inventory SET stock = ? WHERE product_id = ?", (new_stock, payload.product_id))
        conn.execute(
            "INSERT INTO stock_moves (product_id, warehouse_id, qty, move_type, ref_no, move_date, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (payload.product_id, warehouse_id, signed_qty, payload.move_type, payload.ref_no.strip() or None, now, payload.note.strip() or f"React ERP by {principal.username}"),
        )
        conn.commit()
        return {"product_id": payload.product_id, "product_name": name, "stock": new_stock, "quantity": payload.quantity, "move_type": payload.move_type}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        conn.close()


@router.get("/purchase-orders", dependencies=[Depends(require(RISK_OVERVIEW_READ))])
def purchase_orders(limit: int = Query(default=100, ge=1, le=500)):
    return {"items": _query("SELECT po_id, supplier_id, status, total_amount, estimated_delay_days FROM purchase_orders ORDER BY po_id DESC LIMIT ?", (limit,))}


@router.get("/orders", dependencies=[Depends(require(RISK_OVERVIEW_READ))])
def orders(limit: int = Query(default=100, ge=1, le=500)):
    return {"items": _query(
        """SELECT o.order_id, o.customer_id, c.name AS customer_name,
                  o.product_id, i.name AS product_name, o.quantity,
                  o.status, o.order_date, o.total_amount
           FROM orders o
           LEFT JOIN customers c ON c.customer_id = o.customer_id
           LEFT JOIN inventory i ON i.product_id = o.product_id
           ORDER BY o.order_date DESC LIMIT ?""",
        (limit,),
    )}


@router.post("/orders", status_code=201)
def create_order(payload: SalesOrderRequest, principal: AccessContext = Depends(require(RISK_WORKSPACE_WRITE))):
    try:
        return create_sales_order(
            order_id=payload.order_id,
            customer_id=payload.customer_id or None,
            product_id=payload.product_id,
            quantity=payload.quantity,
            status=payload.status,
        )
    except InsufficientStockError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (OrderValidationError, sqlite3.IntegrityError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/orders/{order_id}/status")
def update_order_status(order_id: str, payload: OrderStatusRequest, principal: AccessContext = Depends(require(RISK_WORKSPACE_WRITE))):
    try:
        return transition_order_status(order_id, payload.status)
    except InsufficientStockError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (OrderValidationError, sqlite3.IntegrityError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/purchase-orders", status_code=202)
def submit_purchase_order(payload: PurchaseOrderRequest, principal: AccessContext = Depends(require(ERP_EXCHANGE_PROPOSE))):
    result = gateway.call(
        "create_purchase_order",
        {
            "po_id": payload.po_id.strip(),
            "supplier_id": payload.supplier_id,
            "product_id": payload.product_id,
            "qty": payload.qty,
            "unit_price": payload.unit_price,
            "order_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "待入庫",
            "note": payload.note.strip(),
        },
        role=principal.role,
        actor=principal.username,
        agent_name="procurement_agent",
        operation_id=uuid4().hex,
    )
    return {"status": result.status, "message": result.message, "approval_id": result.approval_id}


@router.get("/customers", dependencies=[Depends(require(RISK_OVERVIEW_READ))])
def customers(limit: int = Query(default=100, ge=1, le=500)):
    return {"items": _query(
        "SELECT customer_id, name, phone, email, country, region FROM customers ORDER BY name LIMIT ?",
        (limit,),
    )}


@router.get("/finance/summary", dependencies=[Depends(require(RISK_OVERVIEW_READ))])
def finance_summary():
    conn = sqlite3.connect(DB_FILE)
    row = conn.execute(
        """SELECT
             (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status NOT IN ('已取消')) AS receivable_total,
             (SELECT COALESCE(SUM(total_amount), 0) FROM purchase_orders WHERE status NOT IN ('已取消')) AS payable_total,
             (SELECT COALESCE(SUM(stock * COALESCE(cost, 0)), 0) FROM inventory) AS inventory_value,
             (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status = '已出貨') AS shipped_revenue"""
    ).fetchone()
    ledger = conn.execute(
        "SELECT COUNT(*) AS count, COALESCE(SUM(debit), 0) AS debit, COALESCE(SUM(credit), 0) AS credit FROM general_ledger"
    ).fetchone()
    conn.close()
    return {"summary": records({
        "receivable_total": row[0], "payable_total": row[1], "inventory_value": row[2],
        "shipped_revenue": row[3], "ledger_count": ledger[0], "ledger_debit": ledger[1],
        "ledger_credit": ledger[2],
    })}


@router.get("/supply-chain/map", dependencies=[Depends(require(RISK_OVERVIEW_READ))])
def supply_chain_map():
    suppliers_df = risk.get_suppliers_for_map()
    events_df = risk.get_recent_events_for_delay(20)
    return {
        "suppliers": records(suppliers_df.to_dict(orient="records")),
        "heatmap": records(risk.get_risk_heatmap_data()),
        "events": records(events_df.to_dict(orient="records")),
    }


@router.get("/esg/carbon", dependencies=[Depends(require(RISK_OVERVIEW_READ))])
def carbon_summary(year_month: str = Query(default="", pattern=r"^$|^\d{4}-\d{2}$")):
    conn = sqlite3.connect(DB_FILE)
    params = (year_month,) if year_month else ()
    where = "WHERE strftime('%Y-%m', o.order_date) = ? AND o.status != '已取消'" if year_month else "WHERE o.status != '已取消'"
    rows = conn.execute(
        f"""SELECT cf.scope, COALESCE(SUM(o.quantity * cf.kg_co2_per_unit), 0) AS carbon_kg
            FROM orders o JOIN carbon_factors cf ON cf.product_id = o.product_id {where}
            GROUP BY cf.scope ORDER BY cf.scope""", params,
    ).fetchall()
    detail = conn.execute(
        f"""SELECT o.product_id, i.name, COALESCE(SUM(o.quantity), 0) AS quantity,
                   COALESCE(MAX(cf.kg_co2_per_unit), 0) AS factor,
                   COALESCE(SUM(o.quantity * cf.kg_co2_per_unit), 0) AS carbon_kg
            FROM orders o JOIN inventory i ON i.product_id = o.product_id
            LEFT JOIN carbon_factors cf ON cf.product_id = o.product_id
            {where} GROUP BY o.product_id, i.name ORDER BY carbon_kg DESC""", params,
    ).fetchall()
    conn.close()
    return {
        "period": year_month or "全部",
        "by_scope": records([{"scope": r[0], "carbon_kg": r[1]} for r in rows]),
        "by_product": records([{"product_id": r[0], "name": r[1], "quantity": r[2], "factor": r[3], "carbon_kg": r[4]} for r in detail]),
    }


@router.get("/esg/targets", dependencies=[Depends(require(RISK_OVERVIEW_READ))])
def esg_targets():
    return {"items": _query("SELECT id, target_year, scope, baseline_kg_co2, target_kg_co2, note FROM esg_targets ORDER BY target_year DESC, scope")}


@router.get("/hr", dependencies=[Depends(require(RISK_OVERVIEW_READ))])
def hr(limit: int = Query(default=100, ge=1, le=500)):
    return {"items": _query("SELECT employee_id, name, department, role, salary FROM hr ORDER BY name LIMIT ?", (limit,))}


@router.get("/hr/payroll-summary", dependencies=[Depends(require(RISK_OVERVIEW_READ))])
def payroll_summary():
    return {"items": _query(
        """SELECT p.period, COUNT(*) AS employee_count,
                  COALESCE(SUM(p.base_salary + p.bonus - p.deduction), 0) AS net_payroll
           FROM payroll p GROUP BY p.period ORDER BY p.period DESC LIMIT 12"""
    )}
