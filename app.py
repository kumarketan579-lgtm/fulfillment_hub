"""
Fulfillment Hub - FastAPI Application
Backend REST API providing order management, warehouse picking & packing verification,
multi-warehouse inventory transfers, courier manifests, and exception resolution.
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import os

from database import get_db, init_db, log_activity
from sample_data import seed_database, COURIERS

app = FastAPI(title="Fulfillment Hub - XYZ E-Commerce", version="1.0.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Ensure DB initialized
init_db()


# ---------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------
class AssignCourierRequest(BaseModel):
    courier_id: str
    shipping_cost: Optional[float] = None

class VerifyItemRequest(BaseModel):
    scanned_code: str # SKU or Barcode

class PackAndStageRequest(BaseModel):
    packer_name: str
    box_size: Optional[str] = "Standard Box M"
    notes: Optional[str] = None

class CreateTransferRequest(BaseModel):
    sku: str
    quantity: int
    requested_by: str
    notes: Optional[str] = ""

class UpdateTransferStatusRequest(BaseModel):
    status: str # IN_TRANSIT, RECEIVED, CANCELLED

class FlagExceptionRequest(BaseModel):
    issue_type: str # MISSING_STOCK, DAMAGED_ITEM, WRONG_VARIANT, ADDRESS_ERROR, OTHER
    description: str
    reported_by: str
    sku: Optional[str] = None

class ResolveExceptionRequest(BaseModel):
    resolution_notes: str
    action: str # RETURN_TO_QUEUE, CANCEL_ORDER


# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def dict_from_row(row):
    return dict(row) if row else None


# ---------------------------------------------------------
# UI Route
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


# ---------------------------------------------------------
# Analytics & KPI Endpoints
# ---------------------------------------------------------
@app.get("/api/analytics/kpis")
async def get_kpis():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]

    cursor.execute("SELECT status, COUNT(*) FROM orders GROUP BY status")
    status_counts = dict(cursor.fetchall())

    cursor.execute("SELECT COUNT(*) FROM orders WHERE is_priority = 1 AND status != 'DISPATCHED'")
    priority_active = cursor.fetchone()[0]

    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        SELECT COUNT(*) FROM orders 
        WHERE status NOT IN ('DISPATCHED') AND sla_deadline < ?
    """, (now_iso,))
    overdue_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM exceptions WHERE status = 'OPEN'")
    open_exceptions = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM products 
        WHERE main_warehouse_stock <= reorder_threshold
    """)
    low_stock_alerts = cursor.fetchone()[0]

    # Staging bays breakdown
    cursor.execute("""
        SELECT staging_bay, COUNT(*) as count 
        FROM orders 
        WHERE status = 'STAGED' AND staging_bay IS NOT NULL 
        GROUP BY staging_bay
    """)
    staging_breakdown = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "total_orders": total_orders,
        "status_counts": {
            "PENDING_LABEL": status_counts.get("PENDING_LABEL", 0),
            "READY_TO_PICK": status_counts.get("READY_TO_PICK", 0),
            "PICKING": status_counts.get("PICKING", 0),
            "PACKING": status_counts.get("PACKING", 0),
            "STAGED": status_counts.get("STAGED", 0),
            "DISPATCHED": status_counts.get("DISPATCHED", 0),
            "EXCEPTION": status_counts.get("EXCEPTION", 0)
        },
        "priority_active": priority_active,
        "overdue_count": overdue_count,
        "open_exceptions": open_exceptions,
        "low_stock_alerts": low_stock_alerts,
        "staging_breakdown": staging_breakdown
    }


# ---------------------------------------------------------
# Orders Management Endpoints
# ---------------------------------------------------------
@app.get("/api/orders")
async def list_orders(
    status: Optional[str] = None,
    channel: Optional[str] = None,
    priority_only: Optional[bool] = False,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT o.*, c.name as courier_name, c.service_type as courier_service, c.cutoff_time as courier_cutoff,
               (SELECT COUNT(*) FROM order_items WHERE order_id = o.id) as item_count,
               (SELECT SUM(quantity) FROM order_items WHERE order_id = o.id) as total_units
        FROM orders o
        LEFT JOIN couriers c ON o.courier_id = c.id
        WHERE 1=1
    """
    params = []

    if status and status != "ALL":
        query += " AND o.status = ?"
        params.append(status)

    if channel and channel != "ALL":
        query += " AND o.channel = ?"
        params.append(channel)

    if priority_only:
        query += " AND o.is_priority = 1"

    if search:
        s = f"%{search}%"
        query += " AND (o.order_number LIKE ? OR o.customer_name LIKE ? OR o.shipping_city LIKE ? OR o.tracking_number LIKE ?)"
        params.extend([s, s, s, s])

    # Sort orders: Priority orders first, then nearest SLA deadline, then created_at
    query += " ORDER BY o.is_priority DESC, o.sla_deadline ASC, o.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {"orders": orders, "count": len(orders)}


@app.get("/api/orders/{order_id}")
async def get_order_detail(order_id: str):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT o.*, c.name as courier_name, c.service_type as courier_service,
               c.base_rate as courier_base_rate, c.cutoff_time as courier_cutoff,
               c.staging_bay as courier_bay
        FROM orders o
        LEFT JOIN couriers c ON o.courier_id = c.id
        WHERE o.id = ?
    """, (order_id,))
    order_row = cursor.fetchone()

    if not order_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    order = dict(order_row)

    # Get items with product details
    cursor.execute("""
        SELECT oi.*, p.name as product_name, p.variant_name, p.barcode,
               p.location_aisle, p.location_bay, p.location_shelf,
               p.main_warehouse_stock, p.secondary_warehouse_stock,
               p.unit_price, p.weight_kg
        FROM order_items oi
        JOIN products p ON oi.sku = p.sku
        WHERE oi.order_id = ?
    """, (order_id,))
    items = [dict(row) for row in cursor.fetchall()]
    order["items"] = items

    # Get exceptions if any
    cursor.execute("SELECT * FROM exceptions WHERE order_id = ? ORDER BY reported_at DESC", (order_id,))
    order["exceptions"] = [dict(row) for row in cursor.fetchall()]

    # Get activity logs
    cursor.execute("SELECT * FROM activity_logs WHERE order_id = ? ORDER BY timestamp DESC", (order_id,))
    order["activity_logs"] = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return order


@app.post("/api/orders/{order_id}/assign-courier")
async def assign_courier(order_id: str, req: AssignCourierRequest):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM couriers WHERE id = ?", (req.courier_id,))
    courier = cursor.fetchone()
    if not courier:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid courier ID")

    shipping_cost = req.shipping_cost or courier["base_rate"]
    tracking_num = f"{courier['name'][:3].upper()}{datetime.now().strftime('%y%m%d%H%M')}"
    staging_bay = courier["staging_bay"]
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
        UPDATE orders 
        SET courier_id = ?, shipping_cost = ?, tracking_number = ?, staging_bay = ?,
            status = 'READY_TO_PICK', updated_at = ?
        WHERE id = ?
    """, (req.courier_id, shipping_cost, tracking_num, staging_bay, now_iso, order_id))

    conn.commit()
    conn.close()

    log_activity(order_id, "LABEL_CREATED", "Office Team", f"Assigned {courier['name']} with tracking #{tracking_num}. Ready to pick.")
    return {"success": True, "tracking_number": tracking_num, "status": "READY_TO_PICK"}


@app.post("/api/orders/{order_id}/toggle-priority")
async def toggle_priority(order_id: str):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT is_priority, order_number FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    new_val = 0 if row["is_priority"] == 1 else 1
    cursor.execute("UPDATE orders SET is_priority = ?, updated_at = ? WHERE id = ?", 
                   (new_val, datetime.now(timezone.utc).isoformat(), order_id))
    conn.commit()
    conn.close()

    log_activity(order_id, "PRIORITY_CHANGED", "Office Team", f"Priority set to {'HIGH' if new_val == 1 else 'REGULAR'}")
    return {"success": True, "is_priority": new_val}


# ---------------------------------------------------------
# Warehouse Floor & Verification Endpoints
# ---------------------------------------------------------
@app.get("/api/warehouse/queue")
async def get_warehouse_queue():
    """
    Returns prioritized picking queue for warehouse floor workers.
    Sorted by Priority first, then nearest SLA deadline, ensuring no missed cutoffs.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT o.id, o.order_number, o.is_priority, o.sla_deadline, o.status,
               o.assigned_picker, o.staging_bay, c.name as courier_name, c.cutoff_time as courier_cutoff,
               (SELECT COUNT(*) FROM order_items WHERE order_id = o.id) as item_count,
               (SELECT SUM(quantity) FROM order_items WHERE order_id = o.id) as total_units
        FROM orders o
        LEFT JOIN couriers c ON o.courier_id = c.id
        WHERE o.status IN ('READY_TO_PICK', 'PICKING', 'PACKING')
        ORDER BY o.is_priority DESC, o.sla_deadline ASC, o.created_at ASC
    """)
    queue = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"queue": queue, "count": len(queue)}


@app.post("/api/warehouse/orders/{order_id}/start-picking")
async def start_picking(order_id: str, picker_name: str = Query("Dave Miller")):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE orders 
        SET status = 'PICKING', assigned_picker = ?, updated_at = ?
        WHERE id = ? AND status IN ('READY_TO_PICK', 'PICKING')
    """, (picker_name, datetime.now(timezone.utc).isoformat(), order_id))

    conn.commit()
    conn.close()

    log_activity(order_id, "PICKING_STARTED", picker_name, f"Assigned to {picker_name}. Item collection commenced.")
    return {"success": True, "status": "PICKING", "picker": picker_name}


@app.post("/api/warehouse/orders/{order_id}/verify-item")
async def verify_item(order_id: str, req: VerifyItemRequest):
    """
    Critical verification endpoint:
    Checks if scanned barcode or typed SKU matches an unverified item in the order.
    Prevents shipping wrong products or variants.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Find the product associated with this barcode or SKU
    scanned = req.scanned_code.strip().upper()
    cursor.execute("SELECT * FROM products WHERE UPPER(sku) = ? OR barcode = ?", (scanned, scanned))
    matched_product = cursor.fetchone()

    if not matched_product:
        conn.close()
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error_code": "UNKNOWN_CODE",
                "message": f"Scanned code '{scanned}' does not match any registered product in inventory."
            }
        )

    # Check if this SKU belongs to the order
    cursor.execute("""
        SELECT oi.*, p.name as product_name, p.variant_name
        FROM order_items oi
        JOIN products p ON oi.sku = p.sku
        WHERE oi.order_id = ? AND oi.sku = ?
    """, (order_id, matched_product["sku"]))
    order_item = cursor.fetchone()

    if not order_item:
        conn.close()
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error_code": "WRONG_PRODUCT",
                "message": f"MISMATCH ALERT! You scanned '{matched_product['name']} - {matched_product['variant_name']}' ({matched_product['sku']}), which is NOT in this order!"
            }
        )

    # Check if already fully picked
    if order_item["picked_quantity"] >= order_item["quantity"]:
        conn.close()
        return {
            "success": True,
            "already_verified": True,
            "message": f"Item '{matched_product['name']} ({matched_product['variant_name']})' has already been fully picked and verified."
        }

    # Increment picked quantity
    new_picked = order_item["picked_quantity"] + 1
    new_is_verified = 1 if new_picked == order_item["quantity"] else 0

    cursor.execute("""
        UPDATE order_items 
        SET picked_quantity = ?, is_verified = ?
        WHERE id = ?
    """, (new_picked, new_is_verified, order_item["id"]))

    # Also decrement stock from Main Warehouse to maintain live accuracy!
    cursor.execute("""
        UPDATE products
        SET main_warehouse_stock = MAX(0, main_warehouse_stock - 1)
        WHERE sku = ?
    """, (matched_product["sku"],))

    # Check if all items in order are now fully verified
    cursor.execute("""
        SELECT COUNT(*) as unverified_count
        FROM order_items
        WHERE order_id = ? AND is_verified = 0
    """, (order_id,))
    unverified = cursor.fetchone()["unverified_count"]

    if unverified == 0:
        cursor.execute("UPDATE orders SET status = 'PACKING', updated_at = ? WHERE id = ?",
                       (datetime.now(timezone.utc).isoformat(), order_id))
        all_done = True
    else:
        all_done = False

    conn.commit()
    conn.close()

    log_activity(order_id, "ITEM_VERIFIED", "Scanner", f"Verified 1x {matched_product['name']} ({matched_product['sku']}).")
    return {
        "success": True,
        "all_items_verified": all_done,
        "item": {
            "sku": matched_product["sku"],
            "name": matched_product["name"],
            "variant": matched_product["variant_name"],
            "picked_quantity": new_picked,
            "total_quantity": order_item["quantity"]
        },
        "message": f"MATCH! Verified {matched_product['name']} ({matched_product['variant_name']})."
    }


@app.post("/api/warehouse/orders/{order_id}/pack-and-stage")
async def pack_and_stage(order_id: str, req: PackAndStageRequest):
    """
    Packs the verified order and directs the worker to place it in the correct Staging Bay.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT o.*, c.staging_bay as courier_bay FROM orders o LEFT JOIN couriers c ON o.courier_id = c.id WHERE o.id = ?", (order_id,))
    order = cursor.fetchone()
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    target_bay = order["staging_bay"] or order["courier_bay"] or "Bay A - General"
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
        UPDATE orders 
        SET status = 'STAGED', assigned_packer = ?, staging_bay = ?, updated_at = ?
        WHERE id = ?
    """, (req.packer_name, target_bay, now_iso, order_id))

    conn.commit()
    conn.close()

    log_activity(order_id, "PACKED_AND_STAGED", req.packer_name, f"Packed into {req.box_size}. Placed in {target_bay}.")
    return {
        "success": True,
        "status": "STAGED",
        "staging_bay": target_bay,
        "message": f"Order {order['order_number']} successfully packed. Placed in {target_bay}."
    }


# ---------------------------------------------------------
# Exceptions & Issues Management Endpoints
# ---------------------------------------------------------
@app.get("/api/exceptions")
async def list_exceptions(status: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT e.*, o.order_number, o.customer_name, o.is_priority, o.status as order_status,
               p.name as product_name, p.variant_name, p.location_aisle, p.location_bay, p.location_shelf
        FROM exceptions e
        JOIN orders o ON e.order_id = o.id
        LEFT JOIN products p ON e.sku = p.sku
        WHERE 1=1
    """
    params = []
    if status and status != "ALL":
        query += " AND e.status = ?"
        params.append(status)

    query += " ORDER BY e.reported_at DESC"
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"exceptions": rows}


@app.post("/api/orders/{order_id}/flag-exception")
async def flag_exception(order_id: str, req: FlagExceptionRequest):
    conn = get_db()
    cursor = conn.cursor()

    exc_id = f"exc_{int(datetime.now().timestamp())}"
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
        INSERT INTO exceptions (id, order_id, sku, issue_type, description, reported_by, status, reported_at)
        VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?)
    """, (exc_id, order_id, req.sku, req.issue_type, req.description, req.reported_by, now_iso))

    cursor.execute("UPDATE orders SET status = 'EXCEPTION', updated_at = ? WHERE id = ?", (now_iso, order_id))

    conn.commit()
    conn.close()

    log_activity(order_id, "EXCEPTION_FLAGGED", req.reported_by, f"Issue ({req.issue_type}): {req.description}")
    return {"success": True, "exception_id": exc_id}


@app.post("/api/exceptions/{exception_id}/resolve")
async def resolve_exception(exception_id: str, req: ResolveExceptionRequest):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM exceptions WHERE id = ?", (exception_id,))
    exc = cursor.fetchone()
    if not exc:
        conn.close()
        raise HTTPException(status_code=404, detail="Exception not found")

    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        UPDATE exceptions 
        SET status = 'RESOLVED', resolved_at = ?, resolution_notes = ?
        WHERE id = ?
    """, (now_iso, req.resolution_notes, exception_id))

    # Return order to READY_TO_PICK or keep as resolved
    new_order_status = "READY_TO_PICK" if req.action == "RETURN_TO_QUEUE" else "EXCEPTION"
    cursor.execute("UPDATE orders SET status = ?, updated_at = ? WHERE id = ?", (new_order_status, now_iso, exc["order_id"]))

    conn.commit()
    conn.close()

    log_activity(exc["order_id"], "EXCEPTION_RESOLVED", "Office Team", f"Resolved: {req.resolution_notes}. Returned to pick queue.")
    return {"success": True, "message": "Exception resolved successfully"}


# ---------------------------------------------------------
# Inventory & Warehouse 2 Transfers Endpoints
# ---------------------------------------------------------
@app.get("/api/inventory")
async def get_inventory(search: Optional[str] = None, low_stock_only: Optional[bool] = False):
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if search:
        s = f"%{search}%"
        query += " AND (sku LIKE ? OR name LIKE ? OR variant_name LIKE ? OR barcode LIKE ?)"
        params.extend([s, s, s, s])

    if low_stock_only:
        query += " AND main_warehouse_stock <= reorder_threshold"

    query += " ORDER BY main_warehouse_stock ASC"
    cursor.execute(query, params)
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"products": products}


@app.get("/api/transfers")
async def get_transfers():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.*, p.name as product_name, p.variant_name, p.location_aisle, p.location_bay, p.location_shelf
        FROM stock_transfers t
        JOIN products p ON t.sku = p.sku
        ORDER BY t.requested_at DESC
    """)
    transfers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"transfers": transfers}


@app.post("/api/transfers/request")
async def request_stock_transfer(req: CreateTransferRequest):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE sku = ?", (req.sku,))
    prod = cursor.fetchone()
    if not prod:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")

    if prod["secondary_warehouse_stock"] < req.quantity:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Insufficient stock in Secondary Warehouse (Available: {prod['secondary_warehouse_stock']})")

    tr_id = f"tr_{int(datetime.now().timestamp())}"
    now_iso = datetime.now(timezone.utc).isoformat()

    # Deduct from secondary warehouse immediately
    cursor.execute("UPDATE products SET secondary_warehouse_stock = secondary_warehouse_stock - ? WHERE sku = ?",
                   (req.quantity, req.sku))

    cursor.execute("""
        INSERT INTO stock_transfers (id, sku, quantity, status, requested_by, requested_at, notes)
        VALUES (?, ?, ?, 'IN_TRANSIT', ?, ?, ?)
    """, (tr_id, req.sku, req.quantity, req.requested_by, now_iso, req.notes))

    conn.commit()
    conn.close()
    return {"success": True, "transfer_id": tr_id, "message": f"Transfer of {req.quantity} units requested from Secondary Warehouse."}


@app.post("/api/transfers/{transfer_id}/receive")
async def receive_stock_transfer(transfer_id: str):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM stock_transfers WHERE id = ?", (transfer_id,))
    tr = cursor.fetchone()
    if not tr:
        conn.close()
        raise HTTPException(status_code=404, detail="Transfer not found")

    if tr["status"] == "RECEIVED":
        conn.close()
        return {"success": True, "message": "Already received"}

    now_iso = datetime.now(timezone.utc).isoformat()

    # Add to main warehouse stock
    cursor.execute("UPDATE products SET main_warehouse_stock = main_warehouse_stock + ? WHERE sku = ?",
                   (tr["quantity"], tr["sku"]))

    cursor.execute("UPDATE stock_transfers SET status = 'RECEIVED', received_at = ? WHERE id = ?",
                   (now_iso, transfer_id))

    conn.commit()
    conn.close()
    return {"success": True, "message": f"Successfully received {tr['quantity']} units into Main Warehouse shelves."}


# ---------------------------------------------------------
# Staging Bays & Courier Handover Dispatch Endpoints
# ---------------------------------------------------------
@app.get("/api/couriers")
async def list_couriers():
    return {"couriers": COURIERS}


@app.get("/api/dispatch/staging-overview")
async def get_staging_overview():
    conn = get_db()
    cursor = conn.cursor()

    overview = []
    for c in COURIERS:
        cursor.execute("""
            SELECT o.id, o.order_number, o.customer_name, o.tracking_number, o.is_priority,
                   o.shipping_address, o.shipping_city, o.shipping_cost,
                   (SELECT SUM(quantity) FROM order_items WHERE order_id = o.id) as total_units
            FROM orders o
            WHERE o.status = 'STAGED' AND o.courier_id = ?
            ORDER BY o.is_priority DESC, o.order_number ASC
        """, (c["id"],))
        orders = [dict(row) for row in cursor.fetchall()]

        overview.append({
            "courier": c,
            "staging_bay": c["staging_bay"],
            "cutoff_time": c["cutoff_time"],
            "orders": orders,
            "package_count": len(orders)
        })

    conn.close()
    return {"bays": overview}


@app.post("/api/dispatch/courier-handover/{courier_id}")
async def courier_handover(courier_id: str, driver_name: str = Query("Carrier Driver")):
    """
    Courier pickup handover: marks all staged packages for this courier as DISPATCHED.
    Generates handover log and timestamps dispatch.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, order_number FROM orders WHERE status = 'STAGED' AND courier_id = ?", (courier_id,))
    staged_orders = cursor.fetchall()

    if not staged_orders:
        conn.close()
        return {"success": False, "message": "No staged packages found for this courier."}

    now_iso = datetime.now(timezone.utc).isoformat()
    order_ids = [row["id"] for row in staged_orders]

    cursor.execute(f"""
        UPDATE orders 
        SET status = 'DISPATCHED', dispatched_at = ?, updated_at = ?
        WHERE id IN ({','.join(['?']*len(order_ids))})
    """, [now_iso, now_iso] + order_ids)

    conn.commit()
    conn.close()

    for row in staged_orders:
        log_activity(row["id"], "DISPATCHED", driver_name, f"Collected by {courier_id} driver.")

    return {
        "success": True,
        "dispatched_count": len(order_ids),
        "message": f"Successfully handed over {len(order_ids)} packages to courier driver ({driver_name})."
    }


# ---------------------------------------------------------
# System Utilities
# ---------------------------------------------------------
@app.post("/api/system/reset-demo-data")
async def reset_demo_data():
    seed_database()
    return {"success": True, "message": "Database reset to 250 realistic demo orders and inventory."}
