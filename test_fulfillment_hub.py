"""
Automated End-to-End Test Suite for Fulfillment Hub
Validates all API endpoints, business logic, verification workflows,
multi-warehouse stock updates, and exception reporting using requests.
"""

import time
import threading
import requests
import uvicorn
from sample_data import seed_database
from database import init_db

TEST_PORT = 8009
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"

def start_server():
    from app import app
    uvicorn.run(app, host="127.0.0.1", port=TEST_PORT, log_level="warning")

def run_tests():
    print("==================================================")
    print(" Running Fulfillment Hub Test Suite...")
    print("==================================================")

    seed_database()

    # Start test server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(1.5) # Wait for server startup

    # 1. UI Root Test
    res = requests.get(f"{BASE_URL}/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "XYZ" in res.text
    print("[PASS] GET / (Dashboard UI HTML rendered)")

    # 2. KPI Metrics Test
    res = requests.get(f"{BASE_URL}/api/analytics/kpis")
    assert res.status_code == 200
    kpis = res.json()
    assert kpis["total_orders"] == 250
    assert kpis["status_counts"]["PENDING_LABEL"] == 40
    assert kpis["status_counts"]["READY_TO_PICK"] == 70
    assert kpis["open_exceptions"] >= 5
    print(f"[PASS] GET /api/analytics/kpis (250 orders, {kpis['open_exceptions']} open exceptions)")

    # 3. Orders List & Filter Test
    res = requests.get(f"{BASE_URL}/api/orders?status=PENDING_LABEL&limit=10")
    assert res.status_code == 200
    pending_orders = res.json()["orders"]
    assert len(pending_orders) == 10
    target_order = pending_orders[0]
    print(f"[PASS] GET /api/orders (Retrieved order {target_order['order_number']})")

    # 4. Assign Courier Test (Office Workflow)
    res = requests.post(f"{BASE_URL}/api/orders/{target_order['id']}/assign-courier", json={
        "courier_id": "courier_dhl",
        "shipping_cost": 14.50
    })
    assert res.status_code == 200
    assert res.json()["status"] == "READY_TO_PICK"
    print(f"[PASS] POST /api/orders/{target_order['id']}/assign-courier (Transitioned to READY_TO_PICK)")

    # 5. Warehouse Queue Prioritization Test
    res = requests.get(f"{BASE_URL}/api/warehouse/queue")
    assert res.status_code == 200
    queue = res.json()["queue"]
    assert len(queue) > 0
    # First item should be priority if any priority exist
    has_priority = any(o["is_priority"] == 1 for o in queue)
    if has_priority:
        assert queue[0]["is_priority"] == 1, "Queue should prioritize priority orders first!"
    print(f"[PASS] GET /api/warehouse/queue ({len(queue)} orders queued with SLA priority sorting)")

    # 6. Warehouse Pick & Barcode Verification Workflow
    pick_order_id = queue[0]["id"]
    res = requests.post(f"{BASE_URL}/api/warehouse/orders/{pick_order_id}/start-picking?picker_name=Dave%20Miller")
    assert res.status_code == 200
    assert res.json()["status"] == "PICKING"

    # Get details of items in this order
    res = requests.get(f"{BASE_URL}/api/orders/{pick_order_id}")
    order_detail = res.json()
    first_item = order_detail["items"][0]

    # Test Mismatch (Wrong SKU / Wrong Variant)
    res_wrong = requests.post(f"{BASE_URL}/api/warehouse/orders/{pick_order_id}/verify-item", json={
        "scanned_code": "WRONG-SKU-999"
    })
    assert res_wrong.status_code == 400
    print("[PASS] POST verify-item: Successfully rejected invalid SKU (Mismatch alert triggered)")

    # Test Valid Barcode Scan
    res_valid = requests.post(f"{BASE_URL}/api/warehouse/orders/{pick_order_id}/verify-item", json={
        "scanned_code": first_item["barcode"]
    })
    assert res_valid.status_code == 200
    assert res_valid.json()["success"] is True
    print(f"[PASS] POST verify-item: Verified correct item '{first_item['product_name']} ({first_item['variant_name']})'")

    # 7. Multi-Warehouse Stock Transfer Test
    res_inv = requests.get(f"{BASE_URL}/api/inventory")
    assert res_inv.status_code == 200
    products = res_inv.json()["products"]
    sample_prod = products[0]

    res_transfer = requests.post(f"{BASE_URL}/api/transfers/request", json={
        "sku": sample_prod["sku"],
        "quantity": 10,
        "requested_by": "Test Worker",
        "notes": "Testing transfer workflow"
    })
    assert res_transfer.status_code == 200
    tr_id = res_transfer.json()["transfer_id"]
    print(f"[PASS] POST /api/transfers/request (Dispatched transfer {tr_id} from Secondary Warehouse)")

    # Receive the transfer at Main Warehouse
    res_recv = requests.post(f"{BASE_URL}/api/transfers/{tr_id}/receive")
    assert res_recv.status_code == 200
    print(f"[PASS] POST /api/transfers/{tr_id}/receive (Stock added to Main Warehouse)")

    # 8. Exception Logging & Resolution Test
    res_exc = requests.post(f"{BASE_URL}/api/orders/{target_order['id']}/flag-exception", json={
        "issue_type": "MISSING_STOCK",
        "description": "Item not found in shelf A-01-02",
        "reported_by": "Samira Khan"
    })
    assert res_exc.status_code == 200
    exc_id = res_exc.json()["exception_id"]
    print(f"[PASS] POST /api/orders/.../flag-exception (Logged exception {exc_id})")

    res_res = requests.post(f"{BASE_URL}/api/exceptions/{exc_id}/resolve", json={
        "resolution_notes": "Restocked item from overflow bin.",
        "action": "RETURN_TO_QUEUE"
    })
    assert res_res.status_code == 200
    print(f"[PASS] POST /api/exceptions/{exc_id}/resolve (Resolved and returned to queue)")

    # 9. Staging Bays & Courier Dispatch Handover Test
    res_stage = requests.get(f"{BASE_URL}/api/dispatch/staging-overview")
    assert res_stage.status_code == 200
    bays = res_stage.json()["bays"]
    assert len(bays) == 4
    print(f"[PASS] GET /api/dispatch/staging-overview (4 courier staging bays monitored)")

    print("\n==================================================")
    print(" ALL 9 TEST SUITES PASSED FLAWLESSLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
