"""
Database models and storage engine for Fulfillment Hub (XYZ E-Commerce).
Uses Python built-in sqlite3 with clean connection handling and dict rows.
"""

import sqlite3
import json
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fulfillment_hub.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Couriers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS couriers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        service_type TEXT NOT NULL,
        base_rate REAL NOT NULL,
        cutoff_time TEXT NOT NULL,
        staging_bay TEXT NOT NULL,
        color_badge TEXT NOT NULL
    )
    """)

    # Products & Inventory table (Tracking Main Warehouse & Secondary Warehouse)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        sku TEXT PRIMARY KEY,
        barcode TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        variant_name TEXT NOT NULL,
        category TEXT NOT NULL,
        unit_price REAL NOT NULL,
        weight_kg REAL NOT NULL,
        main_warehouse_stock INTEGER NOT NULL DEFAULT 0,
        secondary_warehouse_stock INTEGER NOT NULL DEFAULT 0,
        location_aisle TEXT NOT NULL,
        location_bay TEXT NOT NULL,
        location_shelf TEXT NOT NULL,
        reorder_threshold INTEGER NOT NULL DEFAULT 10,
        image_url TEXT
    )
    """)

    # Orders table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        order_number TEXT UNIQUE NOT NULL,
        channel TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        customer_email TEXT NOT NULL,
        shipping_address TEXT NOT NULL,
        shipping_city TEXT NOT NULL,
        shipping_postcode TEXT NOT NULL,
        is_priority INTEGER NOT NULL DEFAULT 0,
        sla_deadline TEXT NOT NULL,
        status TEXT NOT NULL, -- PENDING_LABEL, READY_TO_PICK, PICKING, PACKING, STAGED, DISPATCHED, EXCEPTION
        courier_id TEXT,
        shipping_cost REAL DEFAULT 0,
        tracking_number TEXT,
        staging_bay TEXT,
        assigned_picker TEXT,
        assigned_packer TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        dispatched_at TEXT,
        FOREIGN KEY (courier_id) REFERENCES couriers(id)
    )
    """)

    # Order Items table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT NOT NULL,
        sku TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        picked_quantity INTEGER NOT NULL DEFAULT 0,
        is_verified INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (sku) REFERENCES products(sku)
    )
    """)

    # Stock Transfers between Secondary and Main Warehouse
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_transfers (
        id TEXT PRIMARY KEY,
        sku TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        status TEXT NOT NULL, -- REQUESTED, IN_TRANSIT, RECEIVED, CANCELLED
        requested_by TEXT NOT NULL,
        requested_at TEXT NOT NULL,
        received_at TEXT,
        notes TEXT,
        FOREIGN KEY (sku) REFERENCES products(sku)
    )
    """)

    # Exceptions & Issues table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exceptions (
        id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        sku TEXT,
        issue_type TEXT NOT NULL, -- MISSING_STOCK, DAMAGED_ITEM, WRONG_VARIANT, ADDRESS_ERROR, OTHER
        description TEXT NOT NULL,
        reported_by TEXT NOT NULL,
        status TEXT NOT NULL, -- OPEN, IN_PROGRESS, RESOLVED
        reported_at TEXT NOT NULL,
        resolved_at TEXT,
        resolution_notes TEXT,
        FOREIGN KEY (order_id) REFERENCES orders(id)
    )
    """)

    # Audit / Activity logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT,
        action TEXT NOT NULL,
        user_name TEXT NOT NULL,
        details TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

def log_activity(order_id, action, user_name, details):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO activity_logs (order_id, action, user_name, details, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (order_id, action, user_name, details, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()
