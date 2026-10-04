# 5-Minute Video Walkthrough Script: XYZ Fulfillment Hub

> **Recording Time Target:** 4 minutes 45 seconds (Buffer under the 5-minute hard limit)  
> **Presenter:** Product Engineer / Fulfillment Architect  
> **Visuals:** Screen recording of `http://127.0.0.1:8000` with live clicking and sound on.

---

## Timed Walkthrough Structure

| Timestamp | Segment | Key Screen Focus |
|---|---|---|
| **0:00 – 1:00** | **1. How I Understood the Problem** | KPI Header Ribbon & Problem Context |
| **1:00 – 2:15** | **2. What We Built: Office Command Center** | Pipeline Kanban, Rate Shopping, 1-Click Thermal Label |
| **2:15 – 3:30** | **3. Warehouse Floor Mode (Audio & Scan Verification)** | Large Shelf Location, Barcode Scan Audio, Staging Bay |
| **3:30 – 4:15** | **4. Inventory Transfer & Courier Manifest Handover** | Wh 2 Transfer Hub & Staging Bay Handover |
| **4:15 – 4:55** | **5. Why We Made These Choices & Conclusion** | Human-centric UX, zero-friction Python stack |

---

## Complete Narration Script

### [0:00 – 1:00] Part 1: How I Understood the Problem
*(Start screen recording on the main dashboard showing the 250-order pipeline ribbon.)*

> **"Hello everyone! Today I’m walking you through Fulfillment Hub, built for XYZ E-Commerce.**
>
> When reviewing XYZ's scenario, I realized that XYZ isn't failing because they lack hard-working staff. They have an office team of 1 to 2 people and 2 to 3 warehouse workers who are experienced with physical products.
> 
> The real bottleneck is **spreadsheet blindness**:
> 1. In a spreadsheet, 250 orders look like 250 identical rows. You cannot tell what is waiting for a courier, what is missing stock, or which order has an urgent 2:00 PM cutoff.
> 2. Priority orders get buried in regular orders and miss same-day deadlines.
> 3. Warehouse workers are explicitly **not very comfortable with technology**. Handing them complicated software or tiny spreadsheets causes wrong variants and mispicks.
> 4. Stock in the secondary warehouse isn't replenished proactively.
> 5. And packed boxes get misplaced before courier pickup.
>
> Our goal was simple: **Design an intuitive, error-proof hub tailored to XYZ’s actual people and volume.** Let’s see it in action."

---

### [1:00 – 2:15] Part 2: What We Built – The Office Command Center
*(Click on 'Office Hub' tab. Click on a 'Pending Label' order to open the modal.)*

> **"First, the Office Command Center.**
> 
> Across the top, the office team sees a live pulse of the entire operation: 250 orders today, 40 needing labels, and live countdowns for courier pickup cutoffs.
> 
> Clicking on any pending order opens our **Courier Rate & SLA Engine**. Here, the office team doesn't have to guess courier rules. They see real-time options side-by-side: DHL Express, FedEx, UPS, or SpeedyShip, comparing shipping costs and cutoff deadlines.
> 
> With one click, they select DHL Express. The system instantly generates a tracking number, assigns **Staging Bay A**, transitions the order to `Ready to Pick`, and produces a standard **4x6 printable thermal shipping label** complete with scannable barcode and return dock details.
> 
> If a customer calls for same-day delivery, one click on 'Toggle Priority' floats that order to the top of the picking list with a high-visibility badge."

---

### [2:15 – 3:30] Part 3: Warehouse Floor Mode (Designed for the Floor Team)
*(Click on 'Warehouse Floor' tab. Click 'Start Picking' on order XYZ-1002. Demonstrate correct barcode scan and wrong SKU test.)*

> **"Now, let's step onto the warehouse floor. This is where the magic happens for workers who aren't tech-savvy.**
> 
> Notice how the interface transforms: high contrast, zero clutter, and extra-large touch targets.
> 
> The picking queue is **auto-sorted by SLA urgency**. Pickers don't search through lists; they just click the top card.
> 
> When picking begins:
> 1. The shelf location is displayed in giant font: **`AISLE B • BAY 02 • SHELF 01`**. Workers know immediately where to walk.
> 2. Next, look at the **Variant Card**: it clearly highlights *EcoHeavy Fleece Hoodie - Black / Medium*.
> 3. To prevent shipping the wrong variant—one of XYZ’s biggest pain points—we integrated an audible verification engine. 
> 
> Watch what happens if a picker accidentally scans the wrong variant: *(Click 'Test Wrong SKU Mismatch' -> Audio buzzer sounds)*. A loud warning buzzes and an alert explains the mistake.
> 
> Now watch when they scan the correct barcode: *(Click '1-Click Correct Barcode' -> Crisp scanner chime sounds)*. The item is verified, and stock is decremented from the shelf.
> 
> Once all items are verified, the worker arrives at the **Pack & Stage** screen. It explicitly instructs: **'Place box into Bay A - DHL'**. This ensures packed boxes are never misplaced."

---

### [3:30 – 4:15] Part 4: Multi-Warehouse Transfers & Staging Bay Handover
*(Click on 'Inventory & Wh 2' tab, then switch to 'Staging & Dispatch' tab.)*

> **"Next, we solved the two-warehouse inventory coordination problem.**
> 
> XYZ has a main warehouse and a secondary overflow warehouse. In the **Inventory Hub**, we track both side-by-side. 
> 
> If Main Warehouse stock is low, a worker or office operator clicks **'Request Transfer from Wh 2'**. When the runner delivers the stock to the dock, clicking **'Receive at Main Dock'** instantly replenishes shelf stock.
> 
> Finally, in **Staging & Dispatch**, packed boxes wait in designated bays: Bay A for DHL, Bay B for FedEx, Bay C for UPS. 
> 
> When the DHL driver arrives at 2:00 PM, the warehouse lead clicks **'Handover to DHL Express'**. All staged parcels are logged as `Dispatched` in one click with a complete audit timestamp."

---

### [4:15 – 4:55] Part 5: Why We Made These Specific Choices
*(Switch back to main overview)*

> **"Why did we make these choices?**
> 
> 1. **Human-Centric UX:** Instead of training workers to read complex software, we brought warehouse hardware ergonomics into the browser—large shelf tags, audio scanner feedback, and dedicated staging bays.
> 2. **Operational Decoupling:** Office handles couriers and customer communication; the warehouse floor only focuses on pick, verify, and drop.
> 3. **Pragmatic Tech Stack:** Built with pure Python, SQLite, and vanilla client-side Web Audio. It requires zero compilation, zero Node dependencies, and can run on a tablet, desktop, or mobile device with a single command.
> 
> Fulfillment Hub gives XYZ the efficiency of an enterprise warehouse management system, without the complexity or cost. Thank you!"

---

## Tips for Recording
1. **Screen Resolution:** 1920x1080 (1080p).
2. **Audio:** Make sure your speaker audio is shared so the scanner beeps and buzzers are heard during the video.
3. **Cursor:** Use a visible cursor highlighter or smooth mouse movements.
4. **Timing Check:** Keep each section within the timestamp bounds to comfortably land at ~4:45.
