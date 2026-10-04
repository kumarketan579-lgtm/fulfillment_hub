# AI Usage Note: Fulfillment Hub for XYZ E-Commerce

**Author:** Candidate / Software Engineer  
**Project:** Take-Home Project – Fulfillment Hub  
**Date:** October 2026  
**Format:** 1 Page Maximum  

---

### 1. AI Tools Used & How They Were Applied
During the design and implementation of Fulfillment Hub, I used **Advanced Agentic AI (Google DeepMind's coding agent)** in an interactive pair-programming capacity:
- **Architecture & Schema Brainstorming:** Used AI to explore relational schema structures for tracking multi-channel orders, multi-warehouse stock allocations, and courier cutoff schedules.
- **Realistic Dataset Generation:** Leveraged AI to generate a statistically representative daily volume dataset (250 orders) with authentic SKU taxonomies, realistic city/postcode distributions, and edge-case exceptions (damaged goods, variant mismatches).
- **Rapid Prototyping:** Used AI to scaffold boilerplate FastAPI route handlers and synthesize Web Audio API oscillator nodes for scanner sound effects without needing external `.mp3` assets.
- **Automated Test Scaffolding:** Used AI to construct end-to-end test scenarios across Starlette/Requests client interactions.

---

### 2. Disagreements with AI Suggestions & Key Engineering Decisions

While AI provided strong initial code templates, my domain judgment diverged from AI recommendations in two critical areas:

#### Disagreement 1: Rejecting a Complex Mobile Camera Scanner in Favor of Hardware/Simulation Ergonomics
- **The AI Suggestion:** The AI initially recommended embedding an in-browser HTML5 video camera barcode scanner library (`html5-qrcode` / `quagga.js`) so warehouse workers could use their personal smartphone cameras to scan boxes.
- **My Counter-Judgment & Decision:** I rejected this approach. In a real fulfillment center handling 200–300 parcels a day, camera-based smartphone scanning is deeply impractical: it drains battery, fails in varying warehouse lighting, is clumsy with gloved hands, and requires workers who are explicitly *"not comfortable with technology"* to fiddle with mobile browser camera permissions and focus squares.
- **The Solution Implemented:** I designed a dedicated **Warehouse Floor Mode** optimized for physical USB/Bluetooth handheld barcode scanners (which emit keyboard keystrokes ending in `Enter`), paired with a high-contrast UI and **instant one-click simulation buttons** for desktop evaluation. I also built a native Web Audio engine that gives unmistakable acoustic feedback (crisp high double-beep on match, low square-wave buzzer on mismatch). This minimizes screen interaction and aligns with real warehouse workflows.

#### Disagreement 2: Rejecting Single-Inventory Abstraction for Multi-Warehouse Decoupling
- **The AI Suggestion:** The AI proposed simplifying inventory into a single `available_stock` integer column on the product table, arguing that secondary warehouse stock could just be an internal attribute or dynamically merged into total inventory.
- **My Counter-Judgment & Decision:** I rejected this simplification because it ignores the fundamental operational constraint stated in XYZ's scenario: *orders can only ship from the Main Warehouse, and items must be physically moved before picking can occur.* Treating inventory as a single pooled pool would cause pickers to walk to empty shelves in the Main Warehouse for stock that actually sits in the overflow building down the street.
- **The Solution Implemented:** I enforced strict architectural separation between `main_warehouse_stock` and `secondary_warehouse_stock` and implemented a dedicated **Stock Transfer Request & Dock Receiving workflow**. When main stock falls below threshold, workers can trigger a transfer request, track transit, and receive goods at the dock before orders enter the pick queue.

#### Disagreement 3: Framework Selection (Decoupled Vanilla Frontend vs. Heavy SPA Frameworks)
- **The AI Suggestion:** The AI suggested setting up a Next.js / React frontend with npm dependencies, Tailwind build pipelines, and TypeScript configurations.
- **My Counter-Judgment & Decision:** For a take-home review, requiring reviewers to install `node`, `npm`, and troubleshoot node module version differences adds unnecessary friction. Instead, I chose a self-contained Python architecture (FastAPI + Starlette templates + CDN Tailwind & Lucide) with zero build steps. Any reviewer can clone the repo and run `python run.py`, having the entire application and database ready in 2 seconds.

---

### 3. Conclusion & Reflection
AI accelerated boilerplate generation, but **product judgment, operational empathy for non-technical warehouse workers, and architectural domain constraints** dictated the final system. Fulfillment Hub is not just a collection of code; it is a practical operational tool designed around human behavior on the warehouse floor.
