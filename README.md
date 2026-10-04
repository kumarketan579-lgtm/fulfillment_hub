# XYZ Fulfillment Hub

> **A streamlined, human-centered fulfillment and warehouse dispatch system designed specifically for small e-commerce operations scaling from 200–300 orders/day.**

Built in **Python (FastAPI + SQLite)** with a lightweight, responsive interface powered by Tailwind CSS, Lucide icons, and the Web Audio API. Requires **no build tools, no Node.js/npm**, and runs locally with a single command.

---

## Quickstart (Run Locally in 5 Seconds)

### 1. Requirements
- Python 3.10+ (Standard Python environment)
- Dependencies: `fastapi`, `uvicorn`, `jinja2`, `requests`

```bash
pip install fastapi uvicorn jinja2 requests
```

### 2. Launch the Application
Navigate to the project folder and run:
```bash
python run.py
```
*This command automatically initializes the SQLite database, seeds 250 realistic demo orders matching XYZ's daily volume, starts the local server, and opens your browser at `http://127.0.0.1:8000`.*

### 3. Run the Automated Test Suite
```bash
python test_fulfillment_hub.py
```
*Runs all 9 end-to-end integration tests verifying order triage, barcode scanning, mismatch detection, multi-warehouse stock replenishment, and courier handover.*

---

## The Problem: How Spreadsheets Failed XYZ

XYZ is an e-commerce business shipping 200–300 orders daily. The office team (1–2 people) managed orders via spreadsheets and PDFs in shared folders, while the warehouse team (2–3 people) printed sheets and packed boxes. The warehouse workers are experienced with physical handling but **not comfortable with technology**.

As volume grew, spreadsheets introduced critical operational failures:
1. **Blindness to order status:** Nobody could tell at a glance where an order was in the pipeline.
2. **Missed courier cutoffs & lost priorities:** Urgent same-day orders were buried in the spreadsheet rows, missing courier pickup cutoffs.
3. **Inventory mismatch & secondary warehouse bottlenecks:** Spreadsheets showed phantom inventory, and stock trapped in the overflow warehouse wasn't transferred in time.
4. **Wrong variants shipped:** Pickers easily confused similar products (e.g. Black vs Platinum Silver headphones or Medium vs Large hoodies).
5. **Misplaced packages at staging:** Packed boxes were scattered on the warehouse floor, leading to missed courier handovers.
6. **Lost sticky notes:** Missing items and damaged goods were communicated verbally and forgotten.

---

## The Solution: Key Features

### 1. Office Command Center (Triage & Rate Shopping)
- **Visual Pipeline:** Live counters and Kanban stages: `Pending Label` &rarr; `Ready to Pick` &rarr; `In Picking` &rarr; `In Packing` &rarr; `Staged in Bay` &rarr; `Dispatched` &rarr; `Exception`.
- **Courier Rate & SLA Engine:** Compares couriers (DHL Express, FedEx Ground, UPS Standard, SpeedyShip Local) with live rates and pickup cutoff countdowns (e.g. DHL Express pickup in 1h 20m).
- **1-Click Thermal Shipping Label:** Generates standard 4" x 6" printable labels with scannable barcodes and assigned staging bays.
- **Search & Filter:** Instant search by customer name, order number, SKU, or delivery city.

### 2. Warehouse Floor Mode (Designed for Non-Tech-Savvy Workers)
- **High-Contrast, Touch-Friendly UI:** Extra-large fonts, high-contrast action buttons, zero nested menus, zero unnecessary text.
- **Auto-Prioritized Queue:** Same-day priority orders and nearing courier cutoffs automatically float to the top of the picker's screen.
- **Prominent Bin Locations:** Displays clear shelf navigation: `AISLE B • BAY 02 • SHELF 01`.
- **Variant Protection & Barcode Verification:**
  - Clear visual variant tags (e.g., *EcoHeavy Hoodie - Black / Medium*).
  - Workers verify by scanning the item barcode or typing the SKU (supports physical USB scanners or 1-click simulation buttons).
  - **Audio feedback engine:** Plays a crisp high chime on match, and a loud warning buzzer on variant mismatch, explaining the mistake before it reaches the box.
- **Direct Staging Assignment:** Once packed, workers are explicitly instructed which physical bay to drop the box into (e.g., *Place in BAY A - DHL*).

### 3. Two-Tier Inventory & Stock Transfer Hub
- **Main vs Secondary Overflow Tracking:** Clear separation between **Main Warehouse (WH-01)** (ships all orders) and **Secondary Overflow (WH-02)**.
- **Proactive Transfer Requests:** When Main Warehouse stock drops below threshold, 1-click dispatch initiates transfer from WH-02.
- **Dock Receiving:** Main warehouse team confirms receipt at the dock with 1 click, instantly updating live inventory.

### 4. Staging Bays & Courier Dispatch Manifests
- **Bay Segregation:** 4 physical staging zones:
  - `Bay A`: DHL Express
  - `Bay B`: FedEx Ground
  - `Bay C`: UPS Standard
  - `Bay D`: SpeedyShip Local
- **Courier Manifest Generator:** Displays all parcels waiting for each driver, total package count, tracking IDs, and destinations.
- **1-Click Driver Handover:** Confirms batch collection when the courier driver arrives, marking all parcels as `Dispatched` and logging the audit trail.

### 5. Exception Management Queue ("No Problem Forgotten")
- Direct **"Can't Find Item / Missing Stock"** button during picking.
- Categorized logs: Missing Stock, Wrong Variant in Bin, Damaged Product, Incomplete Address.
- Assigned resolution workflows: Restock from overflow warehouse, substitute with customer approval, or cancel.

---

## Project Structure

```
fulfillment_hub/
├── app.py                  # FastAPI REST API & routes
├── database.py             # SQLite schemas, connections & audit logging
├── sample_data.py          # 250-order realistic seed generator
├── run.py                  # Single-command launcher (server + browser launch)
├── test_fulfillment_hub.py # Automated test suite (9 integration tests)
├── static/
│   ├── css/
│   │   └── custom.css      # Warehouse high-contrast styles & print styles
│   └── js/
│       ├── audio.js        # Web Audio synthesizer for scanner beeps & buzzers
│       └── app.js          # Reactive frontend controller & wizard state
├── templates/
│   └── index.html          # Main responsive single-page application
├── README.md               # Setup guide & architectural documentation
├── WALKTHROUGH_SCRIPT.md   # 5-minute video walkthrough script
└── AI_USAGE_NOTE.md        # 1-page note on AI tools, disagreements & judgment
```

---

## Seed Data Summary
The app includes a built-in reset button to reload **250 realistic orders** representing a typical daily run:
- **40 Pending Label:** Waiting for office review and courier assignment.
- **70 Ready to Pick:** Prioritized for warehouse floor workers (urgent SLAs on top).
- **35 In Picking / 35 In Packing:** Active fulfillment progress.
- **40 Staged:** Placed across Bay A, B, C, and D waiting for courier trucks.
- **25 Dispatched:** Completed shipments with carrier tracking numbers.
- **5 Exceptions:** Real-world blockers (empty shelf bin, dented box, missing apartment #).
