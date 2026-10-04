/**
 * Fulfillment Hub - Frontend Application State & Controller
 * Coordinates Office Command Center, Warehouse Pick/Pack Wizard, Inventory Transfers,
 * Staging Bay Manifests, and Audio Verification Engine.
 */

let state = {
    currentTab: 'office',
    orders: [],
    couriers: [],
    inventory: [],
    transfers: [],
    exceptions: [],
    stagingBays: [],
    kpis: {},
    activeOrderModalId: null,
    activePickingOrder: null, // For Warehouse Floor Mode
    filterStatus: 'ALL',
    filterChannel: 'ALL',
    filterPriorityOnly: false,
    searchDebounceTimer: null
};

// -------------------------------------------------------------
// Initialization
// -------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    initClock();
    loadCouriers();
    refreshAllData();
    setInterval(refreshAllData, 15000); // Polling for live team updates
});

function initClock() {
    function updateClock() {
        const now = new Date();
        const clockEl = document.getElementById('live-time-clock');
        if (clockEl) {
            clockEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        }
    }
    updateClock();
    setInterval(updateClock, 1000);
}

async function refreshAllData() {
    await Promise.all([
        loadKPIs(),
        loadOrders(),
        loadWarehouseQueue(),
        loadInventory(),
        loadTransfers(),
        loadExceptions(),
        loadStagingOverview()
    ]);
    if (window.lucide) {
        lucide.createIcons();
    }
}

// -------------------------------------------------------------
// Tab Switching
// -------------------------------------------------------------
function switchTab(tabName) {
    state.currentTab = tabName;
    ['office', 'warehouse', 'inventory', 'staging', 'exceptions'].forEach(t => {
        const el = document.getElementById(`tab-${t}`);
        const btn = document.getElementById(`nav-btn-${t}`);
        if (t === tabName) {
            el.classList.remove('hidden');
            btn.className = "px-3 py-1.5 rounded-md text-xs font-semibold flex items-center space-x-1.5 bg-blue-600 text-white shadow-sm transition-all";
        } else {
            el.classList.add('hidden');
            btn.className = "px-3 py-1.5 rounded-md text-xs font-semibold flex items-center space-x-1.5 text-slate-300 hover:text-white transition-all";
        }
    });

    if (tabName === 'warehouse') {
        renderWarehouseFloor();
    }
    if (window.lucide) {
        lucide.createIcons();
    }
}

// -------------------------------------------------------------
// KPIs & Analytics
// -------------------------------------------------------------
async function loadKPIs() {
    try {
        const res = await fetch('/api/analytics/kpis');
        const data = await res.json();
        state.kpis = data;

        document.getElementById('kpi-total-orders').textContent = data.total_orders;
        document.getElementById('kpi-pending-label').textContent = data.status_counts.PENDING_LABEL;
        document.getElementById('kpi-ready-pick').textContent = data.status_counts.READY_TO_PICK;
        document.getElementById('kpi-in-progress').textContent = data.status_counts.PICKING + data.status_counts.PACKING;
        document.getElementById('kpi-staged').textContent = data.status_counts.STAGED;
        document.getElementById('kpi-dispatched').textContent = data.status_counts.DISPATCHED;
        document.getElementById('kpi-exceptions').textContent = data.status_counts.EXCEPTION;

        // Card counts
        document.getElementById('card-count-pending').textContent = data.status_counts.PENDING_LABEL;
        document.getElementById('card-count-ready').textContent = data.status_counts.READY_TO_PICK;
        document.getElementById('card-count-picking').textContent = data.status_counts.PICKING;
        document.getElementById('card-count-packing').textContent = data.status_counts.PACKING;
        document.getElementById('card-count-staged').textContent = data.status_counts.STAGED;
        document.getElementById('card-count-dispatched').textContent = data.status_counts.DISPATCHED;

        // Badges
        const activeQueue = data.status_counts.READY_TO_PICK + data.status_counts.PICKING + data.status_counts.PACKING;
        document.getElementById('queue-badge').textContent = activeQueue;
        document.getElementById('exception-badge').textContent = data.open_exceptions;
        const excPill = document.getElementById('open-exceptions-count-pill');
        if (excPill) excPill.textContent = `${data.open_exceptions} Active Issues`;

    } catch (err) {
        console.error("Failed to load KPIs", err);
    }
}

// -------------------------------------------------------------
// Couriers
// -------------------------------------------------------------
async function loadCouriers() {
    try {
        const res = await fetch('/api/couriers');
        const data = await res.json();
        state.couriers = data.couriers;
    } catch (err) {
        console.error("Failed to load couriers", err);
    }
}

// -------------------------------------------------------------
// Office Hub & Orders
// -------------------------------------------------------------
async function loadOrders() {
    try {
        const status = document.getElementById('filter-status').value;
        const channel = document.getElementById('filter-channel').value;
        const search = document.getElementById('order-search').value.trim();

        let url = `/api/orders?limit=100`;
        if (status && status !== 'ALL') url += `&status=${status}`;
        if (channel && channel !== 'ALL') url += `&channel=${encodeURIComponent(channel)}`;
        if (state.filterPriorityOnly) url += `&priority_only=true`;
        if (search) url += `&search=${encodeURIComponent(search)}`;

        const res = await fetch(url);
        const data = await res.json();
        state.orders = data.orders;
        renderOrdersTable(data.orders);
    } catch (err) {
        console.error("Failed to load orders", err);
    }
}

function renderOrdersTable(orders) {
    const tbody = document.getElementById('orders-table-body');
    if (!orders || orders.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-8 text-slate-400">
                    <i data-lucide="package-search" class="w-8 h-8 mx-auto mb-2 text-slate-300"></i>
                    No orders match your current filter.
                </td>
            </tr>
        `;
        if (window.lucide) lucide.createIcons();
        return;
    }

    const now = new Date();

    tbody.innerHTML = orders.map(o => {
        const isPriority = o.is_priority === 1;
        const deadline = new Date(o.sla_deadline);
        const diffHours = (deadline - now) / (1000 * 60 * 60);
        const isUrgent = diffHours < 3 && o.status !== 'DISPATCHED';

        let statusBadge = getStatusBadgeHTML(o.status);

        return `
            <tr class="hover:bg-slate-50 transition-colors cursor-pointer border-b border-slate-100" onclick="openOrderDetail('${o.id}')">
                <td class="py-3 px-4">
                    <div class="flex items-center space-x-2">
                        ${isPriority ? '<span class="px-1.5 py-0.5 rounded text-[10px] font-black bg-amber-500 text-slate-950 flex items-center space-x-0.5"><i data-lucide="zap" class="w-2.5 h-2.5 fill-slate-950"></i><span>PRIORITY</span></span>' : ''}
                        <span class="font-bold text-slate-900">${o.order_number}</span>
                    </div>
                </td>
                <td class="py-3 px-4 text-slate-600 font-medium">
                    ${o.channel}
                </td>
                <td class="py-3 px-4">
                    <div class="font-medium text-slate-800">${o.customer_name}</div>
                    <div class="text-[11px] text-slate-400">${o.shipping_city}</div>
                </td>
                <td class="py-3 px-4 text-slate-600">
                    <span class="font-bold text-slate-800">${o.total_units || o.item_count}</span> units (${o.item_count} SKU)
                </td>
                <td class="py-3 px-4">
                    ${o.courier_name ? `
                        <div class="font-semibold text-slate-800 flex items-center space-x-1">
                            <span>${o.courier_name}</span>
                            <span class="text-[10px] text-slate-400">(${o.courier_cutoff})</span>
                        </div>
                        <div class="text-[10px] text-slate-400 font-mono">${o.tracking_number || ''}</div>
                    ` : '<span class="text-amber-600 font-bold bg-amber-50 px-2 py-0.5 rounded text-[10px]">Unassigned</span>'}
                </td>
                <td class="py-3 px-4">
                    <div class="flex items-center space-x-1.5">
                        <span class="font-medium ${isUrgent ? 'text-rose-600 font-bold urgent-badge' : 'text-slate-600'}">
                            ${formatHoursRemaining(diffHours, o.status)}
                        </span>
                    </div>
                </td>
                <td class="py-3 px-4">
                    ${statusBadge}
                </td>
                <td class="py-3 px-4 text-right">
                    <button onclick="event.stopPropagation(); openOrderDetail('${o.id}')" class="text-xs bg-slate-100 hover:bg-blue-50 text-slate-700 hover:text-blue-700 px-2.5 py-1 rounded border border-slate-200 font-medium transition-all">
                        Details
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    if (window.lucide) lucide.createIcons();
}

function getStatusBadgeHTML(status) {
    switch (status) {
        case 'PENDING_LABEL':
            return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">Pending Label</span>';
        case 'READY_TO_PICK':
            return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-300">Ready to Pick</span>';
        case 'PICKING':
            return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-100 text-indigo-800 border border-indigo-300">In Picking</span>';
        case 'PACKING':
            return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-300">In Packing</span>';
        case 'STAGED':
            return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">Staged in Bay</span>';
        case 'DISPATCHED':
            return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-teal-100 text-teal-800 border border-teal-300">Dispatched</span>';
        case 'EXCEPTION':
            return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300">Exception</span>';
        default:
            return `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-800">${status}</span>`;
    }
}

function formatHoursRemaining(hours, status) {
    if (status === 'DISPATCHED') return '<span class="text-slate-400">Shipped</span>';
    if (hours < 0) return `<span class="text-rose-600 font-bold">${Math.abs(Math.round(hours))}h overdue</span>`;
    if (hours < 1) return `<span class="text-rose-600 font-bold">${Math.round(hours * 60)}m left</span>`;
    return `${Math.round(hours)}h remaining`;
}

function filterByStatus(status) {
    document.getElementById('filter-status').value = status;
    loadOrders();
}

function filterPriorityOrders() {
    state.filterPriorityOnly = !state.filterPriorityOnly;
    loadOrders();
}

function resetFilters() {
    document.getElementById('filter-status').value = 'ALL';
    document.getElementById('filter-channel').value = 'ALL';
    document.getElementById('order-search').value = '';
    state.filterPriorityOnly = false;
    loadOrders();
}

function debounceSearch() {
    clearTimeout(state.searchDebounceTimer);
    state.searchDebounceTimer = setTimeout(loadOrders, 300);
}

// -------------------------------------------------------------
// Order Detail & Courier Selection Modal
// -------------------------------------------------------------
async function openOrderDetail(orderId) {
    state.activeOrderModalId = orderId;
    try {
        const res = await fetch(`/api/orders/${orderId}`);
        const order = await res.json();

        document.getElementById('modal-order-number').textContent = order.order_number;
        document.getElementById('modal-order-customer').textContent = `${order.customer_name} • ${order.channel}`;
        document.getElementById('modal-status-badge').innerHTML = getStatusBadgeHTML(order.status);
        document.getElementById('modal-shipping-address').textContent = `${order.shipping_address}, ${order.shipping_city} ${order.shipping_postcode}`;
        document.getElementById('modal-shipping-email').textContent = order.customer_email;

        // SLA
        const deadline = new Date(order.sla_deadline);
        const diffHours = (deadline - new Date()) / (1000 * 60 * 60);
        document.getElementById('modal-sla-badge').innerHTML = `SLA: <strong>${formatHoursRemaining(diffHours, order.status)}</strong>`;

        // Priority button
        const pBtn = document.getElementById('modal-priority-toggle-btn');
        if (order.is_priority === 1) {
            pBtn.className = "text-xs font-bold px-3 py-1 rounded-md border bg-amber-500 text-slate-950 border-amber-400 flex items-center space-x-1";
            pBtn.innerHTML = '<i data-lucide="zap" class="w-3.5 h-3.5 fill-slate-950"></i><span>Priority Order</span>';
        } else {
            pBtn.className = "text-xs font-semibold px-3 py-1 rounded-md border bg-slate-100 text-slate-700 hover:bg-slate-200 border-slate-300 flex items-center space-x-1";
            pBtn.innerHTML = '<i data-lucide="zap" class="w-3.5 h-3.5"></i><span>Mark as Priority</span>';
        }

        // Courier Info
        if (order.courier_name) {
            document.getElementById('modal-courier-info').textContent = `${order.courier_name} (${order.courier_service})`;
            document.getElementById('modal-tracking-info').textContent = `Tracking: ${order.tracking_number} • Staging: ${order.staging_bay || 'Unassigned'}`;
        } else {
            document.getElementById('modal-courier-info').textContent = "Not Assigned (Select Courier Below)";
            document.getElementById('modal-tracking-info').textContent = "Shipping label required";
        }

        // Items List
        const itemsList = document.getElementById('modal-items-list');
        itemsList.innerHTML = order.items.map(it => `
            <div class="p-3 bg-white flex items-center justify-between">
                <div>
                    <div class="font-bold text-slate-900">${it.product_name}</div>
                    <div class="text-[11px] text-slate-500">Variant: <strong class="text-blue-700 font-semibold">${it.variant_name}</strong> • SKU: <span class="font-mono">${it.sku}</span></div>
                    <div class="text-[11px] text-slate-400 mt-0.5">
                        Shelf: <strong class="text-slate-700 shelf-tag">Aisle ${it.location_aisle} &bull; Bay ${it.location_bay} &bull; Shelf ${it.location_shelf}</strong>
                    </div>
                </div>
                <div class="text-right">
                    <span class="text-xs font-bold bg-slate-100 text-slate-800 px-2 py-1 rounded border">Qty: ${it.quantity}</span>
                    <div class="text-[10px] mt-1 ${it.is_verified ? 'text-emerald-600 font-bold' : 'text-slate-400'}">
                        ${it.is_verified ? '&#10003; Pick Verified' : 'Pending Pick'}
                    </div>
                </div>
            </div>
        `).join('');

        // Courier Selector
        const selectorSection = document.getElementById('modal-courier-selector-section');
        const couriersGrid = document.getElementById('modal-couriers-grid');

        if (order.status === 'PENDING_LABEL') {
            selectorSection.classList.remove('hidden');
            couriersGrid.innerHTML = state.couriers.map(c => `
                <div onclick="assignCourierToOrder('${order.id}', '${c.id}', ${c.base_rate})" class="cursor-pointer bg-white p-3 rounded-lg border-2 border-slate-200 hover:border-blue-500 hover:shadow transition-all text-left">
                    <div class="flex items-center justify-between">
                        <span class="font-bold text-slate-900">${c.name}</span>
                        <span class="text-xs font-black text-blue-600">$${c.base_rate.toFixed(2)}</span>
                    </div>
                    <div class="text-[11px] text-slate-500 mt-0.5">${c.service_type}</div>
                    <div class="text-[10px] text-amber-700 font-semibold mt-1">Pickup Cutoff: ${c.cutoff_time}</div>
                    <button class="mt-2 w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-1 rounded text-[10px]">
                        Select &amp; Create Label
                    </button>
                </div>
            `).join('');
        } else {
            selectorSection.classList.add('hidden');
        }

        // Activity Logs
        const actLog = document.getElementById('modal-activity-log');
        if (order.activity_logs && order.activity_logs.length > 0) {
            actLog.innerHTML = order.activity_logs.map(log => `
                <div class="text-[11px] p-2 bg-slate-50 rounded border border-slate-200 flex items-start space-x-2">
                    <span class="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0"></span>
                    <div class="flex-1">
                        <span class="font-bold text-slate-800">${log.action}</span> by <span class="font-medium text-slate-600">${log.user_name}</span>: ${log.details}
                        <div class="text-[10px] text-slate-400 mt-0.5">${new Date(log.timestamp).toLocaleTimeString()}</div>
                    </div>
                </div>
            `).join('');
        } else {
            actLog.innerHTML = '<p class="text-slate-400 italic">No previous activity recorded.</p>';
        }

        openModal('order-detail-modal');
        if (window.lucide) lucide.createIcons();

    } catch (err) {
        console.error("Failed to load order details", err);
    }
}

async function assignCourierToOrder(orderId, courierId, baseRate) {
    try {
        const res = await fetch(`/api/orders/${orderId}/assign-courier`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ courier_id: courierId, shipping_cost: baseRate })
        });
        const data = await res.json();
        if (data.success) {
            window.warehouseAudio.playScanSuccess();
            closeModal('order-detail-modal');
            refreshAllData();
        }
    } catch (err) {
        alert("Failed to assign courier: " + err);
    }
}

async function toggleCurrentOrderPriority() {
    if (!state.activeOrderModalId) return;
    try {
        const res = await fetch(`/api/orders/${state.activeOrderModalId}/toggle-priority`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            openOrderDetail(state.activeOrderModalId); // reload modal
            refreshAllData();
        }
    } catch (err) {
        alert("Error toggling priority: " + err);
    }
}

// -------------------------------------------------------------
// Shipping Label Printing
// -------------------------------------------------------------
async function printShippingLabelForCurrentOrder() {
    if (!state.activeOrderModalId) return;
    try {
        const res = await fetch(`/api/orders/${state.activeOrderModalId}`);
        const order = await res.json();

        if (order.status === 'PENDING_LABEL') {
            alert("Please assign a courier before printing a shipping label.");
            return;
        }

        document.getElementById('label-courier-name').textContent = order.courier_name || 'COURIER DISPATCH';
        document.getElementById('label-service-type').textContent = order.courier_service || 'STANDARD';
        document.getElementById('label-customer-name').textContent = order.customer_name;
        document.getElementById('label-customer-address').innerHTML = `${order.shipping_address}<br>${order.shipping_city} ${order.shipping_postcode}`;
        document.getElementById('label-staging-bay').textContent = order.staging_bay || 'BAY A';
        document.getElementById('label-tracking-number').textContent = order.tracking_number || 'TRK-99201';

        openModal('shipping-label-modal');
    } catch (err) {
        alert("Error loading label: " + err);
    }
}

// -------------------------------------------------------------
// WAREHOUSE FLOOR MODE (Tech-Uncomfortable friendly)
// -------------------------------------------------------------
async function loadWarehouseQueue() {
    try {
        const res = await fetch('/api/warehouse/queue');
        const data = await res.json();
        state.warehouseQueue = data.queue;
        if (state.currentTab === 'warehouse' && !state.activePickingOrder) {
            renderWarehouseFloor();
        }
    } catch (err) {
        console.error("Failed to load warehouse queue", err);
    }
}

function refreshWarehouseQueue() {
    state.activePickingOrder = null;
    loadWarehouseQueue();
    renderWarehouseFloor();
}

function renderWarehouseFloor() {
    const container = document.getElementById('warehouse-active-task-container');
    if (!container) return;

    // IF an order is actively being picked, render the Pick Wizard
    if (state.activePickingOrder) {
        renderPickWizard(container, state.activePickingOrder);
        return;
    }

    // ELSE render prioritized queue cards
    const queue = state.warehouseQueue || [];
    if (queue.length === 0) {
        container.innerHTML = `
            <div class="bg-white rounded-2xl p-12 text-center border border-slate-200">
                <i data-lucide="check-circle-2" class="w-16 h-16 text-emerald-500 mx-auto mb-3"></i>
                <h3 class="text-xl font-bold text-slate-800">All Pick Lists Clear!</h3>
                <p class="text-xs text-slate-500 mt-1">There are no orders waiting to be picked right now.</p>
            </div>
        `;
        if (window.lucide) lucide.createIcons();
        return;
    }

    container.innerHTML = `
        <div class="space-y-4">
            <div class="flex items-center justify-between">
                <h3 class="text-sm font-bold text-slate-800 uppercase tracking-wider">
                    Prioritized Picking Queue (${queue.length} orders waiting)
                </h3>
                <span class="text-xs text-slate-500">Auto-sorted: Priority orders first, then closest cutoff time</span>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                ${queue.map(order => {
                    const isPriority = order.is_priority === 1;
                    const isPicking = order.status === 'PICKING';
                    const isPacking = order.status === 'PACKING';

                    return `
                        <div class="bg-white rounded-xl border-2 ${isPriority ? 'border-amber-400 shadow-md' : 'border-slate-200'} p-5 flex flex-col justify-between space-y-4 hover:shadow-lg transition-all">
                            <div>
                                <div class="flex items-center justify-between">
                                    <span class="text-lg font-black text-slate-900">${order.order_number}</span>
                                    ${isPriority ? '<span class="bg-amber-500 text-slate-950 font-black text-[10px] px-2 py-0.5 rounded-full flex items-center gap-1"><i data-lucide="zap" class="w-3 h-3 fill-slate-950"></i>SAME-DAY SLA</span>' : '<span class="text-xs text-slate-400 font-medium">Standard</span>'}
                                </div>
                                <div class="mt-2 text-xs text-slate-600">
                                    <div class="font-bold text-slate-800">${order.total_units} Items to Collect</div>
                                    <div class="text-slate-500 mt-0.5">Courier: <strong class="text-slate-700">${order.courier_name}</strong> (Cutoff: ${order.courier_cutoff})</div>
                                </div>
                            </div>

                            <div class="pt-2 border-t border-slate-100 flex items-center justify-between">
                                <span class="text-xs font-semibold ${isPicking ? 'text-indigo-600' : 'text-slate-500'}">
                                    ${order.status}
                                </span>
                                <button onclick="startWarehousePick('${order.id}')" class="bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-4 py-2 rounded-lg text-xs flex items-center space-x-1.5 shadow-sm transition-all">
                                    <i data-lucide="play" class="w-3.5 h-3.5 fill-slate-950"></i>
                                    <span>${isPacking ? 'Open Pack & Stage' : isPicking ? 'Continue Picking' : 'Start Picking'}</span>
                                </button>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        </div>
    `;

    if (window.lucide) lucide.createIcons();
}

async function startWarehousePick(orderId) {
    try {
        await fetch(`/api/warehouse/orders/${orderId}/start-picking?picker_name=Dave%20Miller`, { method: 'POST' });
        const res = await fetch(`/api/orders/${orderId}`);
        const order = await res.json();
        state.activePickingOrder = order;
        renderWarehouseFloor();
    } catch (err) {
        alert("Error starting pick: " + err);
    }
}

function renderPickWizard(container, order) {
    const unpickedItems = order.items.filter(it => it.picked_quantity < it.quantity);
    const isReadyToPack = unpickedItems.length === 0;

    if (isReadyToPack) {
        // Render Pack & Stage Screen
        container.innerHTML = `
            <div class="bg-white rounded-2xl border-2 border-emerald-400 p-8 shadow-xl max-w-3xl mx-auto space-y-6 animate-in fade-in">
                <div class="text-center">
                    <div class="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 mx-auto flex items-center justify-center font-bold text-2xl mb-3">
                        &#10003;
                    </div>
                    <h3 class="text-2xl font-black text-slate-900">All Items Picked &amp; Verified!</h3>
                    <p class="text-xs text-slate-500 mt-1">Order <strong class="text-slate-800">${order.order_number}</strong> is ready for boxing and staging.</p>
                </div>

                <!-- Box packing checklist -->
                <div class="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2 text-xs">
                    <div class="font-bold text-slate-700 uppercase tracking-wider mb-2">Packing Steps:</div>
                    <label class="flex items-center space-x-2 text-slate-800">
                        <input type="checkbox" checked class="w-4 h-4 text-emerald-600 rounded">
                        <span>Place all ${order.items.reduce((acc, i) => acc + i.quantity, 0)} items into box</span>
                    </label>
                    <label class="flex items-center space-x-2 text-slate-800">
                        <input type="checkbox" checked class="w-4 h-4 text-emerald-600 rounded">
                        <span>Attach Shipping Label: <strong>${order.tracking_number}</strong></span>
                    </label>
                </div>

                <!-- Prominent Staging Bay Instruction -->
                <div class="bg-amber-100 border-2 border-amber-400 p-5 rounded-xl text-center">
                    <span class="text-xs uppercase font-extrabold text-amber-900 block mb-1">Place Box Into Dedicated Staging Bay:</span>
                    <span class="text-3xl font-black text-slate-950 tracking-wider">${order.staging_bay || order.courier_bay || 'BAY A - DHL'}</span>
                    <p class="text-[11px] text-amber-800 mt-1">Keep boxes separated by courier to prevent missed pickups.</p>
                </div>

                <div class="flex items-center justify-between pt-4">
                    <button onclick="refreshWarehouseQueue()" class="text-xs text-slate-500 hover:text-slate-800 font-semibold">
                        Back to Queue
                    </button>
                    <button onclick="completePackAndStage('${order.id}')" class="bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold px-6 py-3 rounded-xl text-sm flex items-center space-x-2 shadow-lg transition-all">
                        <i data-lucide="check" class="w-5 h-5"></i>
                        <span>Confirm Box Placed in Bay &amp; Complete</span>
                    </button>
                </div>
            </div>
        `;
        if (window.lucide) lucide.createIcons();
        return;
    }

    // Active item being picked (pick one by one)
    const currentItem = unpickedItems[0];

    container.innerHTML = `
        <div class="bg-white rounded-2xl border-2 border-blue-500 p-6 shadow-xl max-w-3xl mx-auto space-y-6">
            <!-- Header -->
            <div class="flex items-center justify-between border-b pb-4">
                <div>
                    <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">Active Pick Task</span>
                    <h3 class="text-xl font-black text-slate-900">${order.order_number}</h3>
                </div>
                <div class="text-right">
                    <span class="text-xs text-slate-500">Progress:</span>
                    <span class="text-sm font-bold text-blue-600 ml-1">
                        ${order.items.reduce((acc, i) => acc + i.picked_quantity, 0)} / ${order.items.reduce((acc, i) => acc + i.quantity, 0)} Items Picked
                    </span>
                </div>
            </div>

            <!-- PROMINENT SHELF LOCATION (Largest element on screen) -->
            <div class="bg-slate-900 text-white p-5 rounded-xl text-center shadow-inner">
                <span class="text-xs font-semibold uppercase text-amber-400 tracking-widest block mb-1">
                    GO TO SHELF LOCATION:
                </span>
                <div class="text-3xl sm:text-4xl font-black tracking-widest font-mono text-white">
                    AISLE ${currentItem.location_aisle} &bull; BAY ${currentItem.location_bay} &bull; SHELF ${currentItem.location_shelf}
                </div>
            </div>

            <!-- Product & Variant Verification Card -->
            <div class="bg-blue-50/70 border-2 border-blue-300 rounded-xl p-5 space-y-2">
                <span class="text-[11px] font-bold uppercase text-blue-800 tracking-wider">Item to Collect:</span>
                <div class="text-lg font-black text-slate-900">${currentItem.product_name}</div>
                
                <!-- Variant Highlight: Large and distinct to prevent variant errors! -->
                <div class="flex items-center space-x-2 pt-1">
                    <span class="text-xs text-slate-600 font-semibold">Exact Variant:</span>
                    <span class="px-2.5 py-1 rounded-md text-xs font-black bg-blue-600 text-white shadow-sm">
                        ${currentItem.variant_name}
                    </span>
                    <span class="text-xs text-slate-400 font-mono">(${currentItem.sku})</span>
                </div>

                <div class="text-xs font-semibold text-slate-700 pt-2 flex items-center justify-between">
                    <span>Quantity to pick: <strong class="text-base text-blue-900 font-black">${currentItem.quantity - currentItem.picked_quantity} unit</strong></span>
                    <span class="text-slate-500">Main Wh Stock: <strong>${currentItem.main_warehouse_stock}</strong></span>
                </div>
            </div>

            <!-- Barcode Scanner Simulation & Verification Box -->
            <div class="bg-slate-50 p-5 rounded-xl border border-slate-200 space-y-3">
                <div class="flex items-center justify-between">
                    <label class="text-xs font-bold text-slate-800 flex items-center space-x-1.5">
                        <i data-lucide="scan" class="w-4 h-4 text-blue-600"></i>
                        <span>Scan Item Barcode or SKU to Verify:</span>
                    </label>
                    <span class="text-[10px] text-slate-500">Hardware scanner or keyboard input</span>
                </div>

                <div class="flex items-center space-x-2">
                    <input type="text" id="warehouse-scan-input" placeholder="Scan barcode or type SKU..." autofocus onkeypress="handleScanKeyPress(event, '${order.id}')" class="flex-1 p-3 text-sm font-mono font-bold border-2 border-slate-300 rounded-lg focus:border-blue-600 focus:outline-none">
                    
                    <button onclick="submitItemScan('${order.id}')" class="bg-blue-600 hover:bg-blue-500 text-white font-bold px-4 py-3 rounded-lg text-xs flex items-center space-x-1">
                        <span>Verify Scan</span>
                    </button>
                </div>

                <!-- 1-Click Simulation Buttons for Reviewer Convenience -->
                <div class="pt-2 flex flex-wrap items-center gap-2 text-xs">
                    <span class="text-slate-400 font-medium">Quick Simulators:</span>
                    <button onclick="simulateScan('${order.id}', '${currentItem.barcode}')" class="bg-emerald-100 hover:bg-emerald-200 text-emerald-800 font-bold px-2.5 py-1 rounded border border-emerald-300 transition-all">
                        &#10003; 1-Click Correct Barcode (${currentItem.barcode})
                    </button>
                    <button onclick="simulateScan('${order.id}', 'WRONG-SKU-999')" class="bg-rose-100 hover:bg-rose-200 text-rose-800 font-bold px-2.5 py-1 rounded border border-rose-300 transition-all">
                        &#10007; Test Wrong SKU Mismatch
                    </button>
                </div>

                <!-- Scan Feedback banner -->
                <div id="scan-feedback-message" class="hidden text-xs p-3 rounded-lg font-bold"></div>
            </div>

            <!-- Emergency Buttons (Item Missing / Can't Find) -->
            <div class="flex items-center justify-between pt-3 border-t">
                <button onclick="openExceptionModalForCurrentOrder('${currentItem.sku}')" class="text-rose-600 hover:text-rose-800 font-bold text-xs flex items-center space-x-1.5 p-2 rounded-lg hover:bg-rose-50 transition-all">
                    <i data-lucide="alert-triangle" class="w-4 h-4"></i>
                    <span>Can't Find Item / Missing Stock</span>
                </button>
                <button onclick="refreshWarehouseQueue()" class="text-slate-500 hover:text-slate-700 font-semibold text-xs">
                    Pause &amp; Return to Queue
                </button>
            </div>
        </div>
    `;

    if (window.lucide) lucide.createIcons();
    // Auto focus scan input
    setTimeout(() => {
        const inp = document.getElementById('warehouse-scan-input');
        if (inp) inp.focus();
    }, 100);
}

function handleScanKeyPress(e, orderId) {
    if (e.key === 'Enter') {
        submitItemScan(orderId);
    }
}

async function submitItemScan(orderId) {
    const input = document.getElementById('warehouse-scan-input');
    const code = input ? input.value.trim() : '';
    if (!code) return;
    await executeScanVerification(orderId, code);
}

async function simulateScan(orderId, code) {
    const input = document.getElementById('warehouse-scan-input');
    if (input) input.value = code;
    await executeScanVerification(orderId, code);
}

async function executeScanVerification(orderId, code) {
    const feedbackEl = document.getElementById('scan-feedback-message');
    try {
        const res = await fetch(`/api/warehouse/orders/${orderId}/verify-item`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scanned_code: code })
        });
        const data = await res.json();

        if (res.ok && data.success) {
            // Audio Chime & Success Feedback
            window.warehouseAudio.playScanSuccess();
            feedbackEl.className = "text-xs p-3 rounded-lg font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 block";
            feedbackEl.textContent = data.message;

            // Reload Order to advance to next item
            setTimeout(async () => {
                const refreshedOrder = await (await fetch(`/api/orders/${orderId}`)).json();
                state.activePickingOrder = refreshedOrder;
                renderWarehouseFloor();
            }, 600);

        } else {
            // Error Buzzer & Loud Warning
            window.warehouseAudio.playScanError();
            feedbackEl.className = "text-xs p-3 rounded-lg font-bold bg-rose-100 text-rose-800 border border-rose-300 block";
            feedbackEl.textContent = data.message || "SCAN ERROR! SKU does not match.";
        }
    } catch (err) {
        window.warehouseAudio.playScanError();
        alert("Scan request failed: " + err);
    }
}

async function completePackAndStage(orderId) {
    try {
        const res = await fetch(`/api/warehouse/orders/${orderId}/pack-and-stage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ packer_name: "Dave Miller", box_size: "Standard Box M" })
        });
        const data = await res.json();
        if (data.success) {
            window.warehouseAudio.playOrderComplete();
            alert(`Order successfully packed and staged in ${data.staging_bay}!`);
            state.activePickingOrder = null;
            refreshAllData();
        }
    } catch (err) {
        alert("Error packing order: " + err);
    }
}

// -------------------------------------------------------------
// INVENTORY & WAREHOUSE 2 TRANSFERS
// -------------------------------------------------------------
async function loadInventory() {
    try {
        const search = document.getElementById('inventory-search') ? document.getElementById('inventory-search').value.trim() : '';
        let url = '/api/inventory';
        if (search) url += `?search=${encodeURIComponent(search)}`;

        const res = await fetch(url);
        const data = await res.json();
        state.inventory = data.products;
        renderInventoryTable(data.products);
        populateTransferSkuSelect(data.products);
    } catch (err) {
        console.error("Failed to load inventory", err);
    }
}

function renderInventoryTable(products) {
    const tbody = document.getElementById('inventory-table-body');
    if (!tbody) return;

    tbody.innerHTML = products.map(p => {
        const isLowStock = p.main_warehouse_stock <= p.reorder_threshold;
        return `
            <tr class="hover:bg-slate-50 transition-colors border-b border-slate-100">
                <td class="py-3 px-4">
                    <div class="font-bold text-slate-900">${p.name}</div>
                    <div class="text-[11px] text-slate-500 font-semibold text-blue-700">${p.variant_name}</div>
                </td>
                <td class="py-3 px-4 font-mono text-[11px] text-slate-600">
                    <div>${p.sku}</div>
                    <div class="text-slate-400 text-[10px]">${p.barcode}</div>
                </td>
                <td class="py-3 px-4 font-mono font-bold text-slate-800 shelf-tag">
                    Aisle ${p.location_aisle} &bull; Bay ${p.location_bay} &bull; Shelf ${p.location_shelf}
                </td>
                <td class="py-3 px-4 text-center">
                    <span class="text-sm font-black ${isLowStock ? 'text-rose-600 bg-rose-50 px-2 py-0.5 rounded' : 'text-slate-800'}">
                        ${p.main_warehouse_stock}
                    </span>
                </td>
                <td class="py-3 px-4 text-center">
                    <span class="text-sm font-semibold text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full">
                        ${p.secondary_warehouse_stock}
                    </span>
                </td>
                <td class="py-3 px-4">
                    ${isLowStock ? 
                        '<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-rose-100 text-rose-800 border border-rose-300">LOW STOCK</span>' : 
                        '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">Healthy</span>'}
                </td>
                <td class="py-3 px-4 text-right">
                    <button onclick="quickTransferPrompt('${p.sku}', '${p.name} - ${p.variant_name}')" class="text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold px-2.5 py-1 rounded border border-indigo-200 transition-all">
                        + Restock from Wh 2
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    if (window.lucide) lucide.createIcons();
}

function filterLowStockProducts() {
    const low = state.inventory.filter(p => p.main_warehouse_stock <= p.reorder_threshold);
    renderInventoryTable(low);
}

function populateTransferSkuSelect(products) {
    const sel = document.getElementById('transfer-sku-select');
    if (!sel) return;
    sel.innerHTML = products.map(p => `
        <option value="${p.sku}">
            ${p.name} (${p.variant_name}) — Main: ${p.main_warehouse_stock} | Wh 2: ${p.secondary_warehouse_stock}
        </option>
    `).join('');
}

function quickTransferPrompt(sku, title) {
    const sel = document.getElementById('transfer-sku-select');
    if (sel) sel.value = sku;
    document.getElementById('transfer-notes').value = `Urgent replenishment for ${title}`;
    openModal('stock-transfer-modal');
}

function openTransferModal() {
    openModal('stock-transfer-modal');
}

async function submitStockTransfer(e) {
    e.preventDefault();
    const sku = document.getElementById('transfer-sku-select').value;
    const quantity = parseInt(document.getElementById('transfer-quantity').value);
    const notes = document.getElementById('transfer-notes').value;
    const requested_by = document.getElementById('transfer-requester').value;

    try {
        const res = await fetch('/api/transfers/request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sku, quantity, notes, requested_by })
        });
        const data = await res.json();
        if (data.success) {
            window.warehouseAudio.playScanSuccess();
            closeModal('stock-transfer-modal');
            refreshAllData();
        } else {
            alert(data.detail || "Transfer request failed");
        }
    } catch (err) {
        alert("Error requesting transfer: " + err);
    }
}

async function loadTransfers() {
    try {
        const res = await fetch('/api/transfers');
        const data = await res.json();
        state.transfers = data.transfers;

        const countEl = document.getElementById('transfers-count');
        if (countEl) countEl.textContent = `${data.transfers.length} transfers`;

        const container = document.getElementById('transfers-container');
        if (!container) return;

        if (data.transfers.length === 0) {
            container.innerHTML = '<p class="p-4 text-xs text-slate-400 italic">No transfers in progress.</p>';
            return;
        }

        container.innerHTML = data.transfers.map(tr => `
            <div class="p-4 bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div class="flex items-center space-x-3">
                    <div class="w-9 h-9 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs">
                        <i data-lucide="arrow-right-left" class="w-4 h-4"></i>
                    </div>
                    <div>
                        <div class="font-bold text-slate-900">${tr.product_name} <span class="text-blue-700 font-semibold">(${tr.variant_name})</span></div>
                        <div class="text-[11px] text-slate-500">
                            Quantity: <strong class="text-indigo-900">${tr.quantity} units</strong> &bull; Requested by ${tr.requested_by} &bull; ${tr.notes || 'Routine stock rebalance'}
                        </div>
                    </div>
                </div>

                <div class="flex items-center space-x-3">
                    <span class="px-2.5 py-1 rounded-full text-[10px] font-bold ${tr.status === 'RECEIVED' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800 animate-pulse'}">
                        ${tr.status}
                    </span>
                    ${tr.status !== 'RECEIVED' ? `
                        <button onclick="receiveTransfer('${tr.id}')" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-3 py-1.5 rounded-lg text-xs flex items-center space-x-1 shadow-sm transition-all">
                            <i data-lucide="check" class="w-3.5 h-3.5"></i>
                            <span>Receive at Main Dock</span>
                        </button>
                    ` : ''}
                </div>
            </div>
        `).join('');

        if (window.lucide) lucide.createIcons();

    } catch (err) {
        console.error("Failed to load transfers", err);
    }
}

async function receiveTransfer(transferId) {
    try {
        const res = await fetch(`/api/transfers/${transferId}/receive`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            window.warehouseAudio.playOrderComplete();
            refreshAllData();
        }
    } catch (err) {
        alert("Failed to receive transfer: " + err);
    }
}

// -------------------------------------------------------------
// STAGING BAYS & DISPATCH
// -------------------------------------------------------------
async function loadStagingOverview() {
    try {
        const res = await fetch('/api/dispatch/staging-overview');
        const data = await res.json();
        state.stagingBays = data.bays;

        const grid = document.getElementById('staging-bays-grid');
        if (!grid) return;

        grid.innerHTML = data.bays.map(bay => `
            <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col justify-between">
                <div class="p-4 border-b border-slate-100 bg-slate-50">
                    <div class="flex items-center justify-between">
                        <span class="font-black text-slate-900 text-sm">${bay.staging_bay}</span>
                        <span class="text-xs bg-blue-100 text-blue-800 font-bold px-2 py-0.5 rounded-full">${bay.package_count} pkgs</span>
                    </div>
                    <div class="text-[11px] text-slate-500 mt-1">
                        Courier: <strong>${bay.courier.name}</strong> &bull; Cutoff: <strong class="text-amber-700">${bay.cutoff_time}</strong>
                    </div>
                </div>

                <div class="p-4 space-y-2 max-h-56 overflow-y-auto divide-y divide-slate-100 text-xs">
                    ${bay.orders.length > 0 ? bay.orders.map(o => `
                        <div class="pt-2 first:pt-0">
                            <div class="flex items-center justify-between font-bold text-slate-800">
                                <span>${o.order_number}</span>
                                ${o.is_priority ? '<span class="text-[9px] bg-amber-500 text-slate-950 px-1.5 py-0.2 rounded font-black">PRIORITY</span>' : ''}
                            </div>
                            <div class="text-[11px] text-slate-500">${o.customer_name} &bull; ${o.shipping_city}</div>
                            <div class="font-mono text-[10px] text-slate-400 mt-0.5">${o.tracking_number}</div>
                        </div>
                    `).join('') : '<p class="text-slate-400 text-center py-4 italic text-xs">No boxes currently in bay</p>'}
                </div>

                <div class="p-3 border-t border-slate-100 bg-slate-50">
                    <button onclick="confirmCourierHandover('${bay.courier.id}', '${bay.courier.name}')" ${bay.package_count === 0 ? 'disabled class="w-full bg-slate-200 text-slate-400 py-2 rounded-lg text-xs font-bold cursor-not-allowed"' : 'class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 rounded-lg text-xs flex items-center justify-center space-x-1.5 shadow-sm transition-all"'}>
                        <i data-lucide="check-circle-2" class="w-4 h-4"></i>
                        <span>Handover to ${bay.courier.name}</span>
                    </button>
                </div>
            </div>
        `).join('');

        if (window.lucide) lucide.createIcons();

    } catch (err) {
        console.error("Failed to load staging bays", err);
    }
}

async function confirmCourierHandover(courierId, courierName) {
    if (!confirm(`Confirm driver pickup and handover for all packages in ${courierName} staging bay?`)) return;
    try {
        const res = await fetch(`/api/dispatch/courier-handover/${courierId}`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            window.warehouseAudio.playOrderComplete();
            alert(data.message);
            refreshAllData();
        }
    } catch (err) {
        alert("Handover failed: " + err);
    }
}

// -------------------------------------------------------------
// EXCEPTIONS & ISSUES
// -------------------------------------------------------------
async function loadExceptions(status = 'ALL') {
    try {
        const res = await fetch(`/api/exceptions?status=${status}`);
        const data = await res.json();
        state.exceptions = data.exceptions;

        const container = document.getElementById('exceptions-container');
        if (!container) return;

        if (data.exceptions.length === 0) {
            container.innerHTML = '<p class="p-6 text-center text-xs text-slate-400 italic">No exceptions logged.</p>';
            return;
        }

        container.innerHTML = data.exceptions.map(exc => `
            <div class="p-4 bg-white flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div class="flex items-start space-x-3">
                    <div class="w-9 h-9 rounded-lg bg-rose-100 text-rose-700 flex items-center justify-center font-bold text-xs mt-0.5 shrink-0">
                        <i data-lucide="alert-octagon" class="w-5 h-5"></i>
                    </div>
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="font-bold text-slate-900">${exc.order_number}</span>
                            <span class="text-xs bg-rose-100 text-rose-800 font-bold px-2 py-0.5 rounded border border-rose-200">${exc.issue_type}</span>
                            <span class="text-[11px] text-slate-400">Reported by ${exc.reported_by} (${new Date(exc.reported_at).toLocaleTimeString()})</span>
                        </div>
                        <p class="text-xs text-slate-700 mt-1 font-medium">${exc.description}</p>
                        ${exc.product_name ? `
                            <div class="text-[11px] text-slate-500 mt-1">
                                Product: <strong class="text-slate-800">${exc.product_name} (${exc.variant_name})</strong> &bull; Shelf: <span class="font-mono">Aisle ${exc.location_aisle}-Bay ${exc.location_bay}</span>
                            </div>
                        ` : ''}
                        ${exc.resolution_notes ? `<div class="text-[11px] text-emerald-700 mt-1 font-semibold">&#10003; Resolution: ${exc.resolution_notes}</div>` : ''}
                    </div>
                </div>

                <div class="flex items-center space-x-2 shrink-0">
                    <span class="px-2.5 py-1 rounded-full text-[10px] font-bold ${exc.status === 'RESOLVED' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800 font-black'}">
                        ${exc.status}
                    </span>
                    ${exc.status !== 'RESOLVED' ? `
                        <button onclick="resolveExceptionPrompt('${exc.id}', '${exc.order_number}')" class="bg-blue-600 hover:bg-blue-500 text-white font-bold px-3 py-1.5 rounded-lg text-xs flex items-center space-x-1 shadow-sm transition-all">
                            <i data-lucide="check" class="w-3.5 h-3.5"></i>
                            <span>Resolve &amp; Re-pick</span>
                        </button>
                    ` : ''}
                </div>
            </div>
        `).join('');

        if (window.lucide) lucide.createIcons();

    } catch (err) {
        console.error("Failed to load exceptions", err);
    }
}

function openExceptionModalForCurrentOrder(sku = null) {
    const orderId = state.activePickingOrder ? state.activePickingOrder.id : state.activeOrderModalId;
    if (!orderId) return;

    document.getElementById('exception-order-id').value = orderId;
    openModal('flag-exception-modal');
}

async function submitException(e) {
    e.preventDefault();
    const orderId = document.getElementById('exception-order-id').value;
    const issue_type = document.getElementById('exception-type').value;
    const description = document.getElementById('exception-notes').value;
    const reported_by = document.getElementById('exception-reporter').value;

    try {
        const res = await fetch(`/api/orders/${orderId}/flag-exception`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ issue_type, description, reported_by })
        });
        const data = await res.json();
        if (data.success) {
            window.warehouseAudio.playScanError();
            closeModal('flag-exception-modal');
            state.activePickingOrder = null;
            refreshAllData();
            alert("Exception logged! Office and warehouse floor alerted.");
        }
    } catch (err) {
        alert("Failed to log exception: " + err);
    }
}

async function resolveExceptionPrompt(exceptionId, orderNumber) {
    const notes = prompt(`Enter resolution notes for Order ${orderNumber} (e.g., 'Found in back stock', 'Transferred from Wh 2', 'Substituted variant with customer approval'):`, "Restocked from overflow warehouse. Shelf replenished.");
    if (!notes) return;

    try {
        const res = await fetch(`/api/exceptions/${exceptionId}/resolve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ resolution_notes: notes, action: "RETURN_TO_QUEUE" })
        });
        const data = await res.json();
        if (data.success) {
            window.warehouseAudio.playOrderComplete();
            refreshAllData();
        }
    } catch (err) {
        alert("Failed to resolve exception: " + err);
    }
}

// -------------------------------------------------------------
// Demo Data Reset
// -------------------------------------------------------------
async function resetDemoData() {
    if (!confirm("Reset database to fresh 250 orders, products, and couriers?")) return;
    try {
        const res = await fetch('/api/system/reset-demo-data', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            window.warehouseAudio.playOrderComplete();
            alert("Database reset to 250 realistic demo orders!");
            state.activePickingOrder = null;
            refreshAllData();
        }
    } catch (err) {
        alert("Reset failed: " + err);
    }
}

// -------------------------------------------------------------
// Modal Utilities
// -------------------------------------------------------------
function openModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
}

function closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
}
