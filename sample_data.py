"""
Sample data generator for Fulfillment Hub (XYZ E-Commerce).
Generates 250 realistic daily orders, products with variants, locations, couriers, staging bays,
warehouse stock distributions, and exception cases to mirror real warehouse operations.
"""

import random
from datetime import datetime, timedelta, timezone
from database import get_db, init_db

COURIERS = [
    {
        "id": "courier_dhl",
        "name": "DHL Express",
        "service_type": "Next-Day Air (Priority)",
        "base_rate": 14.50,
        "cutoff_time": "14:00",
        "staging_bay": "Bay A - DHL",
        "color_badge": "bg-amber-100 text-amber-800 border-amber-300"
    },
    {
        "id": "courier_fedex",
        "name": "FedEx Ground",
        "service_type": "2-Day Expedited",
        "base_rate": 11.20,
        "cutoff_time": "15:30",
        "staging_bay": "Bay B - FedEx",
        "color_badge": "bg-purple-100 text-purple-800 border-purple-300"
    },
    {
        "id": "courier_ups",
        "name": "UPS Standard",
        "service_type": "Standard Ground (3-5 Days)",
        "base_rate": 7.80,
        "cutoff_time": "17:00",
        "staging_bay": "Bay C - UPS",
        "color_badge": "bg-amber-900/10 text-amber-900 border-amber-800/30"
    },
    {
        "id": "courier_speedy",
        "name": "SpeedyShip Local",
        "service_type": "Same-Day Metro Dispatch",
        "base_rate": 16.00,
        "cutoff_time": "13:00",
        "staging_bay": "Bay D - SpeedyShip",
        "color_badge": "bg-emerald-100 text-emerald-800 border-emerald-300"
    }
]

PRODUCTS = [
    # Electronics / Tech
    {
        "sku": "TECH-NC-BLK",
        "barcode": "890123456701",
        "name": "AcousticPro ANC Headphones",
        "variant_name": "Midnight Black",
        "category": "Electronics",
        "unit_price": 129.99,
        "weight_kg": 0.45,
        "main_warehouse_stock": 28,
        "secondary_warehouse_stock": 65,
        "location_aisle": "A", "location_bay": "01", "location_shelf": "02",
        "reorder_threshold": 15
    },
    {
        "sku": "TECH-NC-SLV",
        "barcode": "890123456702",
        "name": "AcousticPro ANC Headphones",
        "variant_name": "Platinum Silver",
        "category": "Electronics",
        "unit_price": 129.99,
        "weight_kg": 0.45,
        "main_warehouse_stock": 4, # Low stock in main!
        "secondary_warehouse_stock": 50,
        "location_aisle": "A", "location_bay": "01", "location_shelf": "03",
        "reorder_threshold": 10
    },
    {
        "sku": "TECH-KB-RED",
        "barcode": "890123456703",
        "name": "Apex Mech Keyboard",
        "variant_name": "Linear Red Switches / RGB",
        "category": "Electronics",
        "unit_price": 89.50,
        "weight_kg": 0.85,
        "main_warehouse_stock": 19,
        "secondary_warehouse_stock": 40,
        "location_aisle": "A", "location_bay": "03", "location_shelf": "01",
        "reorder_threshold": 8
    },
    {
        "sku": "TECH-KB-BRN",
        "barcode": "890123456704",
        "name": "Apex Mech Keyboard",
        "variant_name": "Tactile Brown Switches / Stealth",
        "category": "Electronics",
        "unit_price": 89.50,
        "weight_kg": 0.85,
        "main_warehouse_stock": 2, # Critical low stock in main
        "secondary_warehouse_stock": 35,
        "location_aisle": "A", "location_bay": "03", "location_shelf": "02",
        "reorder_threshold": 8
    },
    {
        "sku": "TECH-MOU-WL",
        "barcode": "890123456705",
        "name": "GlideMaster Wireless Mouse",
        "variant_name": "Matte Charcoal",
        "category": "Electronics",
        "unit_price": 45.00,
        "weight_kg": 0.18,
        "main_warehouse_stock": 52,
        "secondary_warehouse_stock": 120,
        "location_aisle": "A", "location_bay": "04", "location_shelf": "01",
        "reorder_threshold": 20
    },
    # Apparel
    {
        "sku": "APP-HOOD-BLK-M",
        "barcode": "890123456706",
        "name": "EcoHeavy Fleece Hoodie",
        "variant_name": "Black / Medium",
        "category": "Apparel",
        "unit_price": 54.00,
        "weight_kg": 0.60,
        "main_warehouse_stock": 34,
        "secondary_warehouse_stock": 80,
        "location_aisle": "B", "location_bay": "02", "location_shelf": "01",
        "reorder_threshold": 12
    },
    {
        "sku": "APP-HOOD-BLK-L",
        "barcode": "890123456707",
        "name": "EcoHeavy Fleece Hoodie",
        "variant_name": "Black / Large",
        "category": "Apparel",
        "unit_price": 54.00,
        "weight_kg": 0.65,
        "main_warehouse_stock": 26,
        "secondary_warehouse_stock": 70,
        "location_aisle": "B", "location_bay": "02", "location_shelf": "02",
        "reorder_threshold": 12
    },
    {
        "sku": "APP-HOOD-SAGE-M",
        "barcode": "890123456708",
        "name": "EcoHeavy Fleece Hoodie",
        "variant_name": "Sage Green / Medium",
        "category": "Apparel",
        "unit_price": 54.00,
        "weight_kg": 0.60,
        "main_warehouse_stock": 12,
        "secondary_warehouse_stock": 45,
        "location_aisle": "B", "location_bay": "02", "location_shelf": "03",
        "reorder_threshold": 10
    },
    {
        "sku": "APP-TEE-WHT-L",
        "barcode": "890123456709",
        "name": "Supima Classic Crewneck Tee",
        "variant_name": "Optic White / Large",
        "category": "Apparel",
        "unit_price": 28.00,
        "weight_kg": 0.22,
        "main_warehouse_stock": 45,
        "secondary_warehouse_stock": 150,
        "location_aisle": "B", "location_bay": "04", "location_shelf": "02",
        "reorder_threshold": 25
    },
    # Home & Lifestyle
    {
        "sku": "HOME-MUG-CER-BLU",
        "barcode": "890123456710",
        "name": "Artisan Ceramic Mug",
        "variant_name": "Cobalt Blue Glaze (350ml)",
        "category": "Home Goods",
        "unit_price": 22.00,
        "weight_kg": 0.40,
        "main_warehouse_stock": 18,
        "secondary_warehouse_stock": 60,
        "location_aisle": "C", "location_bay": "01", "location_shelf": "01",
        "reorder_threshold": 10
    },
    {
        "sku": "HOME-BTL-THRM-BLK",
        "barcode": "890123456711",
        "name": "HydroShield Insulated Bottle",
        "variant_name": "Onyx Black (750ml)",
        "category": "Home Goods",
        "unit_price": 32.50,
        "weight_kg": 0.50,
        "main_warehouse_stock": 31,
        "secondary_warehouse_stock": 90,
        "location_aisle": "C", "location_bay": "02", "location_shelf": "02",
        "reorder_threshold": 15
    },
    {
        "sku": "BAG-COMMUTE-OLV",
        "barcode": "890123456712",
        "name": "Everyday Urban Canvas Backpack",
        "variant_name": "Olive Green (22L)",
        "category": "Accessories",
        "unit_price": 75.00,
        "weight_kg": 0.70,
        "main_warehouse_stock": 15,
        "secondary_warehouse_stock": 45,
        "location_aisle": "C", "location_bay": "03", "location_shelf": "03",
        "reorder_threshold": 8
    },
    {
        "sku": "BAG-COMMUTE-NVY",
        "barcode": "890123456713",
        "name": "Everyday Urban Canvas Backpack",
        "variant_name": "Deep Navy (22L)",
        "category": "Accessories",
        "unit_price": 75.00,
        "weight_kg": 0.70,
        "main_warehouse_stock": 3, # Low stock in main
        "secondary_warehouse_stock": 30,
        "location_aisle": "C", "location_bay": "03", "location_shelf": "04",
        "reorder_threshold": 8
    },
    {
        "sku": "DESK-PAD-LTHR-BRN",
        "barcode": "890123456714",
        "name": "Top-Grain Leather Desk Mat",
        "variant_name": "Cognac Brown (80x40cm)",
        "category": "Accessories",
        "unit_price": 42.00,
        "weight_kg": 0.55,
        "main_warehouse_stock": 22,
        "secondary_warehouse_stock": 55,
        "location_aisle": "C", "location_bay": "05", "location_shelf": "01",
        "reorder_threshold": 10
    }
]

FIRST_NAMES = ["Liam", "Olivia", "Noah", "Emma", "Oliver", "Charlotte", "Elijah", "Amelia", "James", "Sophia",
               "William", "Isabella", "Benjamin", "Mia", "Lucas", "Evelyn", "Henry", "Harper", "Alexander", "Camila"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
              "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
CITIES = [
    ("New York", "NY", "10001"), ("Los Angeles", "CA", "90001"), ("Chicago", "IL", "60601"),
    ("Houston", "TX", "77001"), ("Phoenix", "AZ", "85001"), ("Philadelphia", "PA", "19101"),
    ("Dallas", "TX", "75201"), ("Austin", "TX", "73301"), ("Seattle", "WA", "98101"),
    ("Boston", "MA", "02101"), ("Denver", "CO", "80201"), ("Atlanta", "GA", "30301")
]
STREETS = ["Maple Ave", "Oak Street", "Broadway", "Pine Lane", "Elm St", "Cedar Blvd", "Sunset Way", "Washington Rd"]
CHANNELS = ["Shopify Webstore", "Amazon Prime", "eBay Store", "Direct Corporate"]
PICKERS = ["Dave Miller", "Samira Khan", "Marcus Vance"]
PACKERS = ["Elena Rostova", "Carl Bradley"]

def seed_database():
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    # Clear existing data for clean idempotent seed
    cursor.execute("DELETE FROM exceptions")
    cursor.execute("DELETE FROM stock_transfers")
    cursor.execute("DELETE FROM order_items")
    cursor.execute("DELETE FROM orders")
    cursor.execute("DELETE FROM products")
    cursor.execute("DELETE FROM couriers")
    cursor.execute("DELETE FROM activity_logs")

    # Insert Couriers
    for c in COURIERS:
        cursor.execute("""
            INSERT INTO couriers (id, name, service_type, base_rate, cutoff_time, staging_bay, color_badge)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (c["id"], c["name"], c["service_type"], c["base_rate"], c["cutoff_time"], c["staging_bay"], c["color_badge"]))

    # Insert Products
    for p in PRODUCTS:
        cursor.execute("""
            INSERT INTO products (
                sku, barcode, name, variant_name, category, unit_price, weight_kg,
                main_warehouse_stock, secondary_warehouse_stock,
                location_aisle, location_bay, location_shelf, reorder_threshold
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["sku"], p["barcode"], p["name"], p["variant_name"], p["category"],
            p["unit_price"], p["weight_kg"], p["main_warehouse_stock"], p["secondary_warehouse_stock"],
            p["location_aisle"], p["location_bay"], p["location_shelf"], p["reorder_threshold"]
        ))

    # Generate 250 orders matching XYZ's daily volume
    # Distribution:
    # 40 PENDING_LABEL
    # 70 READY_TO_PICK
    # 35 PICKING
    # 35 PACKING
    # 40 STAGED
    # 25 DISPATCHED
    # 5 EXCEPTION
    # Total = 250

    status_quotas = [
        ("PENDING_LABEL", 40),
        ("READY_TO_PICK", 70),
        ("PICKING", 35),
        ("PACKING", 35),
        ("STAGED", 40),
        ("DISPATCHED", 25),
        ("EXCEPTION", 5)
    ]

    order_id_counter = 1000
    now = datetime.now(timezone.utc)
    random.seed(42) # Consistent realistic data

    for status, count in status_quotas:
        for _ in range(count):
            order_id_counter += 1
            order_num = f"XYZ-{order_id_counter}"
            order_id = f"ord_{order_id_counter}"
            channel = random.choice(CHANNELS)
            fname = random.choice(FIRST_NAMES)
            lname = random.choice(LAST_NAMES)
            customer_name = f"{fname} {lname}"
            customer_email = f"{fname.lower()}.{lname.lower()}@example.com"
            city_info = random.choice(CITIES)
            shipping_address = f"{random.randint(100, 999)} {random.choice(STREETS)}"
            shipping_city = f"{city_info[0]}, {city_info[1]}"
            shipping_postcode = city_info[2]

            # Priority calculation: approx 25% of orders are Priority (Same-Day)
            is_priority = 1 if (random.random() < 0.28 or channel == "Amazon Prime") else 0

            # SLA deadline:
            if is_priority:
                # Urgent: cutoff between 1 and 4 hours from now
                hours_offset = random.uniform(1.0, 4.0)
            else:
                # Regular: 12 to 28 hours from now
                hours_offset = random.uniform(12.0, 36.0)
            sla_deadline = (now + timedelta(hours=hours_offset)).isoformat()

            # Courier and label logic:
            courier = random.choice(COURIERS)
            courier_id = None
            shipping_cost = 0.0
            tracking_num = None
            staging_bay = None
            assigned_picker = None
            assigned_packer = None
            dispatched_at = None

            created_time = (now - timedelta(hours=random.uniform(1, 10))).isoformat()
            updated_time = created_time

            if status != "PENDING_LABEL":
                courier_id = courier["id"]
                shipping_cost = courier["base_rate"] + round(random.uniform(0.5, 3.0), 2)
                tracking_num = f"{courier['name'][:3].upper()}{random.randint(100000000, 999999999)}"

            if status in ["PICKING", "PACKING", "STAGED", "DISPATCHED"]:
                assigned_picker = random.choice(PICKERS)

            if status in ["PACKING", "STAGED", "DISPATCHED"]:
                assigned_packer = random.choice(PACKERS)

            if status in ["STAGED", "DISPATCHED"]:
                staging_bay = courier["staging_bay"]

            if status == "DISPATCHED":
                dispatched_at = (now - timedelta(minutes=random.randint(10, 180))).isoformat()

            cursor.execute("""
                INSERT INTO orders (
                    id, order_number, channel, customer_name, customer_email,
                    shipping_address, shipping_city, shipping_postcode,
                    is_priority, sla_deadline, status, courier_id, shipping_cost,
                    tracking_number, staging_bay, assigned_picker, assigned_packer,
                    created_at, updated_at, dispatched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id, order_num, channel, customer_name, customer_email,
                shipping_address, shipping_city, shipping_postcode,
                is_priority, sla_deadline, status, courier_id, shipping_cost,
                tracking_num, staging_bay, assigned_picker, assigned_packer,
                created_time, updated_time, dispatched_at
            ))

            # Assign 1 to 3 items per order
            num_items = random.choices([1, 2, 3], weights=[0.65, 0.25, 0.10])[0]
            selected_products = random.sample(PRODUCTS, num_items)

            for prod in selected_products:
                qty = 1 if random.random() < 0.85 else 2
                picked_qty = 0
                is_verified = 0

                if status in ["PACKING", "STAGED", "DISPATCHED"]:
                    picked_qty = qty
                    is_verified = 1
                elif status == "PICKING":
                    # Some items might be partially picked
                    picked_qty = qty if random.random() < 0.6 else 0
                    is_verified = 1 if picked_qty == qty else 0

                cursor.execute("""
                    INSERT INTO order_items (order_id, sku, quantity, picked_quantity, is_verified)
                    VALUES (?, ?, ?, ?, ?)
                """, (order_id, prod["sku"], qty, picked_qty, is_verified))

            # If status == EXCEPTION, create an explicit exception record
            if status == "EXCEPTION":
                issue_types = [
                    ("MISSING_STOCK", "Product not found at indicated shelf location A-03-02. Needs physical search or transfer from Secondary Warehouse."),
                    ("DAMAGED_ITEM", "Corner box dented/cracked during picking. Requires replacement before packing."),
                    ("WRONG_VARIANT", "Shelf bin contained Black/Medium instead of Black/Large. Restocking bin."),
                    ("ADDRESS_ERROR", "Apt / Suite number missing from customer delivery address.")
                ]
                issue_choice = random.choice(issue_types)
                exception_id = f"exc_{order_id_counter}"
                cursor.execute("""
                    INSERT INTO exceptions (id, order_id, sku, issue_type, description, reported_by, status, reported_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?)
                """, (
                    exception_id, order_id, selected_products[0]["sku"],
                    issue_choice[0], issue_choice[1],
                    random.choice(PICKERS), (now - timedelta(minutes=random.randint(15, 120))).isoformat()
                ))

    # Add realistic Stock Transfers
    sample_transfers = [
        ("tr_1", "TECH-NC-SLV", 30, "IN_TRANSIT", "Samira Khan", (now - timedelta(hours=2)).isoformat(), "Moving 30 units to Main Warehouse Shelf A-01-03 for weekend orders"),
        ("tr_2", "TECH-KB-BRN", 25, "REQUESTED", "Dave Miller", (now - timedelta(hours=1)).isoformat(), "Main warehouse stock at 2 units. Urgent restock requested"),
        ("tr_3", "BAG-COMMUTE-NVY", 20, "RECEIVED", "Marcus Vance", (now - timedelta(hours=5)).isoformat(), "Successfully received and placed in shelf C-03-04"),
    ]
    for tr in sample_transfers:
        cursor.execute("""
            INSERT INTO stock_transfers (id, sku, quantity, status, requested_by, requested_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, tr)

    conn.commit()
    conn.close()
    print("Database seeded successfully with 250 orders, couriers, and warehouse inventory.")

if __name__ == "__main__":
    seed_database()
