/**
 * Wine Stock Dashboard — Interactive JavaScript
 * Handles: day-card clicks, comps section, table sorting/filtering, modals,
 * invoice clearing (with photo upload), PDF exports, KPI animations.
 */

// ===================================================================
// Weekly Data from server
// ===================================================================
const weeklyData = JSON.parse(
    document.getElementById('weeklyDataJSON').textContent
);
const weeklyCompsData = JSON.parse(
    document.getElementById('weeklyCompsDataJSON').textContent
);
const weekOffset = JSON.parse(document.getElementById('weekOffsetJSON').textContent);
const weekLabel  = JSON.parse(document.getElementById('weekLabelJSON').textContent);

// ===================================================================
// Day Card Interactions (Sales)
// ===================================================================
let selectedDayIndex = null;

function toggleDayDetail(card, index) {
    const panel = document.getElementById('dayDetailPanel');
    const allCards = document.querySelectorAll('.weekly-day-card:not(.comp-day-card)');

    if (selectedDayIndex === index) {
        panel.style.display = 'none';
        card.classList.remove('selected');
        selectedDayIndex = null;
        return;
    }

    allCards.forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    selectedDayIndex = index;

    const day = weeklyData[index];
    const titleEl = document.getElementById('dayDetailTitle');
    titleEl.textContent = `${day.day_name} — ${day.date_formatted}`;

    const bodyEl = document.getElementById('dayDetailBody');
    const details = day.wine_details;

    const entries = Object.entries(details).sort(([, a], [, b]) => {
        if (b.sold !== a.sold) return b.sold - a.sold;
        return b.ordered - a.ordered;
    });

    if (entries.length === 0) {
        bodyEl.innerHTML = '<div class="day-wine-item" style="justify-content:center; color: var(--text-muted);">No activity this day</div>';
    } else {
        bodyEl.innerHTML = entries.map(([name, d]) => {
            const glassBadge = d.glasses_sold > 0
                ? `<span class="sale-type-mini glass-mini"><i class="fas fa-wine-glass"></i>${d.glasses_sold}gl</span>` : '';
            const bottleBadge = d.bottles_sold > 0
                ? `<span class="sale-type-mini bottle-mini"><i class="fas fa-wine-bottle"></i>${d.bottles_sold}bt</span>` : '';
            return `
            <div class="day-wine-item">
                <span class="day-wine-name">${name}</span>
                <div class="day-wine-stats">
                    ${d.sold > 0 ? `<span class="day-wine-sold">-${d.sold} sold</span>` : ''}
                    ${glassBadge}${bottleBadge}
                    ${d.ordered > 0 ? `<span class="day-wine-ordered">+${d.ordered} ordered</span>` : ''}
                </div>
            </div>
        `}).join('');
    }

    panel.style.display = 'block';
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function closeDayDetail() {
    document.getElementById('dayDetailPanel').style.display = 'none';
    document.querySelectorAll('.weekly-day-card:not(.comp-day-card)').forEach(c => c.classList.remove('selected'));
    selectedDayIndex = null;
}

// ===================================================================
// Comps Section Toggle
// ===================================================================
let compsSectionVisible = false;

function toggleCompsSection() {
    const section = document.getElementById('sectionWeeklyComps');
    const icon = document.getElementById('compsToggleIcon');
    compsSectionVisible = !compsSectionVisible;

    if (compsSectionVisible) {
        section.style.display = 'block';
        // Force reflow so CSS transition triggers properly
        section.offsetHeight;
        section.classList.add('comps-visible');
        icon.style.transform = 'rotate(180deg)';
    } else {
        section.classList.remove('comps-visible');
        icon.style.transform = 'rotate(0deg)';
        closeCompDayDetail();
        // Wait for transition before hiding
        setTimeout(() => { section.style.display = 'none'; }, 280);
    }
}

// ===================================================================
// Comp Day Card Interactions
// ===================================================================
let selectedCompDayIndex = null;

function toggleCompDayDetail(card, index) {
    const panel = document.getElementById('compDayDetailPanel');
    const allCards = document.querySelectorAll('.comp-day-card');

    if (selectedCompDayIndex === index) {
        panel.style.display = 'none';
        card.classList.remove('selected');
        selectedCompDayIndex = null;
        return;
    }

    allCards.forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    selectedCompDayIndex = index;

    const day = weeklyCompsData[index];
    document.getElementById('compDayDetailTitle').textContent = `${day.day_name} — ${day.date_formatted} (Comps)`;

    const bodyEl = document.getElementById('compDayDetailBody');
    const details = day.comp_details;
    const entries = Object.entries(details).sort(([, a], [, b]) => b.total - a.total);

    if (entries.length === 0) {
        bodyEl.innerHTML = '<div class="day-wine-item" style="justify-content:center; color: var(--text-muted);">No comps this day</div>';
    } else {
        bodyEl.innerHTML = entries.map(([name, d]) => {
            const glassBadge = d.glasses > 0
                ? `<span class="sale-type-mini glass-mini"><i class="fas fa-wine-glass"></i>${d.glasses}gl</span>` : '';
            const bottleBadge = d.bottles > 0
                ? `<span class="sale-type-mini bottle-mini"><i class="fas fa-wine-bottle"></i>${d.bottles}bt</span>` : '';
            return `
            <div class="day-wine-item">
                <span class="day-wine-name">${name}</span>
                <div class="day-wine-stats">
                    <span class="day-wine-comp"><i class="fas fa-gift"></i> ${d.total} comp${d.total !== 1 ? 's' : ''}</span>
                    ${glassBadge}${bottleBadge}
                </div>
            </div>
        `}).join('');
    }

    panel.style.display = 'block';
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function closeCompDayDetail() {
    document.getElementById('compDayDetailPanel').style.display = 'none';
    document.querySelectorAll('.comp-day-card').forEach(c => c.classList.remove('selected'));
    selectedCompDayIndex = null;
}

// ===================================================================
// Table Sorting
// ===================================================================
let sortColumn = -1;
let sortAsc = true;

function sortTable(colIndex) {
    const table = document.getElementById('wineDataTable');
    const tbody = document.getElementById('wineTableBody');
    const rows = Array.from(tbody.querySelectorAll('tr'));

    if (sortColumn === colIndex) {
        sortAsc = !sortAsc;
    } else {
        sortColumn = colIndex;
        sortAsc = true;
    }

    const isNumeric = [1, 2, 3, 5, 6, 7, 8].includes(colIndex);

    rows.sort((a, b) => {
        let aVal = a.cells[colIndex].textContent.trim();
        let bVal = b.cells[colIndex].textContent.trim();

        if (isNumeric) {
            aVal = parseFloat(aVal.replace(/[€%,]/g, '')) || 0;
            bVal = parseFloat(bVal.replace(/[€%,]/g, '')) || 0;
        } else {
            aVal = aVal.toLowerCase();
            bVal = bVal.toLowerCase();
        }

        if (aVal < bVal) return sortAsc ? -1 : 1;
        if (aVal > bVal) return sortAsc ? 1 : -1;
        return 0;
    });

    rows.forEach(row => tbody.appendChild(row));

    table.querySelectorAll('th.sortable i').forEach(icon => {
        icon.className = 'fas fa-sort';
        icon.style.opacity = '0.4';
    });
    const activeIcon = table.querySelectorAll('th.sortable')[colIndex].querySelector('i');
    activeIcon.className = sortAsc ? 'fas fa-sort-up' : 'fas fa-sort-down';
    activeIcon.style.opacity = '1';
}

// ===================================================================
// Table Filtering
// ===================================================================
function filterWineTable(query) {
    const rows = document.querySelectorAll('#wineTableBody tr');
    const q = query.toLowerCase();

    rows.forEach(row => {
        const name = row.cells[0].textContent.toLowerCase();
        const supplier = row.cells[4].textContent.toLowerCase();
        const match = name.includes(q) || supplier.includes(q);
        row.classList.toggle('hidden-row', !match);
    });
}

// ===================================================================
// Visual Stock Filtering
// ===================================================================
function filterStockCards(query) {
    const cards = document.querySelectorAll('.stock-card');
    const q = query.toLowerCase();

    cards.forEach(card => {
        const name = card.dataset.wineName;
        card.classList.toggle('hidden', !name.includes(q));
    });
}

function filterByStatus(status, btn) {
    document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');

    const cards = document.querySelectorAll('.stock-card');
    cards.forEach(card => {
        if (status === 'all') {
            card.classList.remove('hidden');
        } else {
            const cardStatus = card.dataset.wineStatus;
            card.classList.toggle('hidden', cardStatus !== status);
        }
    });
}

// ===================================================================
// Modal Management
// ===================================================================
function openModal(id) {
    document.getElementById(id).classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
    document.body.style.overflow = '';
}

document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.classList.remove('active');
            document.body.style.overflow = '';
        }
    });
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.active').forEach(m => {
            m.classList.remove('active');
        });
        document.body.style.overflow = '';
    }
});

// ===================================================================
// Sale Type Toggle (Glass / Bottle)
// ===================================================================
let currentSaleType = 'bottle';

function setSaleType(type) {
    currentSaleType = type;
    document.getElementById('saleBtnBottle').classList.toggle('active', type === 'bottle');
    document.getElementById('saleBtnGlass').classList.toggle('active', type === 'glass');
    document.getElementById('saleQtyLabel').textContent =
        type === 'glass' ? 'Quantity (Glasses)' : 'Quantity (Bottles)';
    updateSaleStockInfo();
}

function updateSaleStockInfo() {
    const sel = document.getElementById('saleWineSelect');
    const opt = sel.options[sel.selectedIndex];
    const stock = opt ? opt.dataset.stock : null;
    const gpb = opt ? parseInt(opt.dataset.gpb) || 1 : 1;
    const hint = document.getElementById('saleStockHint');

    if (stock !== null) {
        const stockNum = parseFloat(stock) || 0;
        if (currentSaleType === 'glass') {
            const glassesAvailable = Math.round(stockNum * gpb * 100) / 100;
            hint.textContent = `Stock: ${stock} bottles = ${glassesAvailable} glasses available (${gpb} glasses/bottle)`;
        } else {
            hint.textContent = `Current stock: ${stock} bottles`;
        }
    }
}

// ===================================================================
// Comp Type Toggle (Glass / Bottle)
// ===================================================================
let currentCompType = 'glass';

function setCompType(type) {
    currentCompType = type;
    document.getElementById('compBtnGlass').classList.toggle('active', type === 'glass');
    document.getElementById('compBtnBottle').classList.toggle('active', type === 'bottle');
    document.getElementById('compQtyLabel').textContent =
        type === 'glass' ? 'Quantity (Glasses)' : 'Quantity (Bottles)';
}

// ===================================================================
// API Calls
// ===================================================================

async function submitSale() {
    const wineId = document.getElementById('saleWineSelect').value;
    const quantity = parseInt(document.getElementById('saleQuantity').value);
    const saleDate = document.getElementById('saleDate').value;

    try {
        const resp = await fetch('/api/wine/sale', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                wine_id: parseInt(wineId),
                quantity,
                date: saleDate,
                sale_type: currentSaleType
            })
        });

        const data = await resp.json();
        if (data.success) {
            const typeLabel = currentSaleType === 'glass' ? 'glass sale' : 'bottle sale';
            showToast(`${typeLabel.charAt(0).toUpperCase() + typeLabel.slice(1)} recorded! Stock: ${data.stock_display}`, 'success');
            closeModal('addSaleModal');
            setTimeout(() => location.reload(), 1200);
        } else {
            showToast(data.error || 'Failed to record sale', 'danger');
        }
    } catch (err) {
        showToast('Network error', 'danger');
    }
}

async function submitComp() {
    const wineId = document.getElementById('compWineSelect').value;
    const quantity = parseInt(document.getElementById('compQuantity').value);
    const compDate = document.getElementById('compDate').value;
    const btn = document.getElementById('submitCompBtn');

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Recording...';

    try {
        const resp = await fetch('/api/wine/comp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                wine_id: parseInt(wineId),
                quantity,
                sale_type: currentCompType,
                date: compDate
            })
        });

        const data = await resp.json();
        if (data.success) {
            const typeLabel = currentCompType === 'glass' ? 'glass' : 'bottle';
            showToast(`Comp recorded: ${quantity} ${typeLabel}(s). Stock: ${data.stock_display}`, 'success');
            closeModal('addCompModal');
            setTimeout(() => location.reload(), 1200);
        } else {
            showToast(data.error || 'Failed to record comp', 'danger');
        }
    } catch (err) {
        showToast('Network error', 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-gift"></i> Record Comp';
    }
}

async function submitPurchase() {
    const wineId = document.getElementById('purchaseWineSelect').value;
    const quantity = parseInt(document.getElementById('purchaseQuantity').value);
    const date = document.getElementById('purchaseDate').value;

    try {
        const resp = await fetch('/api/wine/purchase', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ wine_id: parseInt(wineId), quantity, date })
        });

        const data = await resp.json();
        if (data.success) {
            showToast('Purchase recorded! Invoice pending.', 'success');
            closeModal('addPurchaseModal');
            setTimeout(() => location.reload(), 1200);
        } else {
            showToast(data.error || 'Failed', 'danger');
        }
    } catch (err) {
        showToast('Network error', 'danger');
    }
}

async function submitNewWine() {
    const name = document.getElementById('newWineName').value.trim();
    if (!name) { showToast('Wine name is required', 'warning'); return; }

    const body = {
        name,
        supplier_id: document.getElementById('newWineSupplier').value || null,
        cost_price: document.getElementById('newWineCost').value,
        glasses_per_bottle: document.getElementById('newWineGlasses').value,
        target_margin_percent: document.getElementById('newWineMargin').value,
        minimum_stock_threshold: document.getElementById('newWineThreshold').value,
        current_stock_qty: document.getElementById('newWineStock').value,
    };

    try {
        const resp = await fetch('/api/wine', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        const data = await resp.json();
        if (data.success) {
            showToast(`${name} added successfully!`, 'success');
            closeModal('addWineModal');
            setTimeout(() => location.reload(), 1200);
        } else {
            showToast(data.error || 'Failed', 'danger');
        }
    } catch (err) {
        showToast('Network error', 'danger');
    }
}

async function submitNewSupplier() {
    const name = document.getElementById('newSupplierName').value.trim();
    if (!name) { showToast('Supplier name is required', 'warning'); return; }

    const body = {
        name,
        contact_email: document.getElementById('newSupplierEmail').value.trim(),
        contact_phone: document.getElementById('newSupplierPhone').value.trim(),
        contact_whatsapp: document.getElementById('newSupplierWhatsapp').value.trim(),
        order_method: document.getElementById('newSupplierMethod').value,
        delivery_cutoff_time: document.getElementById('newSupplierCutoff').value.trim(),
        typical_delivery_days: parseInt(document.getElementById('newSupplierDeliveryDays').value) || 1,
        minimum_order_note: document.getElementById('newSupplierMinOrder').value.trim(),
    };

    try {
        const resp = await fetch('/api/supplier', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        const data = await resp.json();
        if (data.success) {
            showToast(`${name} added successfully!`, 'success');
            closeModal('addSupplierModal');
            setTimeout(() => location.reload(), 1200);
        } else {
            showToast(data.error || 'Failed', 'danger');
        }
    } catch (err) {
        showToast('Network error', 'danger');
    }
}

async function editWine(wineId) {
    try {
        const resp = await fetch(`/api/wine/${wineId}`);
        const wine = await resp.json();

        document.getElementById('editWineId').value = wine.id;
        document.getElementById('editWineName').value = wine.name;
        document.getElementById('editWineSupplier').value = wine.supplier_id || '';
        document.getElementById('editWineCost').value = wine.cost_price;
        document.getElementById('editWineGlasses').value = wine.glasses_per_bottle;
        document.getElementById('editWineMargin').value = wine.target_margin_percent;
        document.getElementById('editWineThreshold').value = wine.minimum_stock_threshold;
        document.getElementById('editWineCurrentStock').value = wine.current_stock_qty;

        openModal('editWineModal');
    } catch (err) {
        showToast('Failed to load wine data', 'danger');
    }
}

async function submitEditWine() {
    const wineId = document.getElementById('editWineId').value;
    const body = {
        name: document.getElementById('editWineName').value,
        supplier_id: document.getElementById('editWineSupplier').value || null,
        cost_price: document.getElementById('editWineCost').value,
        glasses_per_bottle: document.getElementById('editWineGlasses').value,
        target_margin_percent: document.getElementById('editWineMargin').value,
        minimum_stock_threshold: document.getElementById('editWineThreshold').value,
        current_stock_qty: document.getElementById('editWineCurrentStock').value,
    };

    try {
        const resp = await fetch(`/api/wine/${wineId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        const data = await resp.json();
        if (data.success) {
            showToast('Wine updated!', 'success');
            closeModal('editWineModal');
            setTimeout(() => location.reload(), 1200);
        } else {
            showToast(data.error || 'Failed', 'danger');
        }
    } catch (err) {
        showToast('Network error', 'danger');
    }
}

// ===================================================================
// Invoice: open upload modal
// ===================================================================
function openClearInvoiceModal(purchaseId, wineName, qty) {
    document.getElementById('clearInvoicePurchaseId').value = purchaseId;
    document.getElementById('clearInvoiceDesc').textContent =
        `Upload the invoice photo for: ${wineName} (${qty} bottles)`;
    document.getElementById('invoicePreview').style.display = 'none';
    document.getElementById('uploadPlaceholder').style.display = 'flex';
    document.getElementById('invoiceImageInput').value = '';
    openModal('clearInvoiceModal');
}

function previewInvoiceImage(input) {
    const file = input.files[0];
    if (!file) return;

    const preview = document.getElementById('invoicePreview');
    const placeholder = document.getElementById('uploadPlaceholder');

    if (file.type === 'application/pdf') {
        placeholder.innerHTML = `
            <i class="fas fa-file-pdf" style="font-size:48px; color:var(--accent-red); margin-bottom:10px;"></i>
            <p style="font-weight:600;">${file.name}</p>
            <p style="font-size:12px; color:var(--text-muted);">PDF ready to upload</p>
        `;
        placeholder.style.display = 'flex';
        preview.style.display = 'none';
    } else {
        const reader = new FileReader();
        reader.onload = (e) => {
            preview.src = e.target.result;
            preview.style.display = 'block';
            placeholder.style.display = 'none';
        };
        reader.readAsDataURL(file);
    }
}

async function submitClearInvoice() {
    const purchaseId = document.getElementById('clearInvoicePurchaseId').value;
    const fileInput = document.getElementById('invoiceImageInput');
    const btn = document.getElementById('submitClearInvoiceBtn');

    if (!fileInput.files[0]) {
        showToast('Please take a photo or upload the invoice first.', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';

    const formData = new FormData();
    formData.append('invoice_image', fileInput.files[0]);

    try {
        const resp = await fetch(`/api/wine/clear-invoice/${purchaseId}`, {
            method: 'POST',
            body: formData
        });

        const data = await resp.json();
        if (data.success) {
            showToast(`Invoice cleared! Stock updated to ${data.stock_display}`, 'success');
            closeModal('clearInvoiceModal');
            setTimeout(() => location.reload(), 1200);
        } else {
            showToast(data.error || 'Failed to clear invoice', 'danger');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check"></i> Confirm & Add to Stock';
        }
    } catch (err) {
        showToast('Network error', 'danger');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-check"></i> Confirm & Add to Stock';
    }
}

// ===================================================================
// Invoice Gallery
// ===================================================================
async function openInvoiceGallery(wineId, wineName) {
    document.getElementById('galleryWineName').textContent = wineName;
    const grid = document.getElementById('invoiceGalleryGrid');
    grid.innerHTML = '<div style="text-align:center; padding: 32px; color: var(--text-muted);"><i class="fas fa-spinner fa-spin fa-2x"></i></div>';
    openModal('invoiceGalleryModal');

    try {
        const resp = await fetch(`/api/wine/${wineId}/invoices`);
        const data = await resp.json();
        const invoices = data.invoices;

        if (!invoices || invoices.length === 0) {
            grid.innerHTML = `
                <div style="text-align:center; padding:40px; color: var(--text-muted);">
                    <i class="fas fa-receipt" style="font-size:48px; margin-bottom:16px; opacity:0.3;"></i>
                    <p>No invoices with images yet.</p>
                    <p style="font-size:12px;">Clear a pending invoice with a photo to see it here.</p>
                </div>`;
            return;
        }

        grid.innerHTML = invoices.map(inv => {
            const isPdf = inv.image_url.endsWith('.pdf');
            const thumbnail = isPdf
                ? `<div class="invoice-thumb-placeholder"><i class="fas fa-file-pdf"></i></div>`
                : `<img src="${inv.image_url}" alt="Invoice" class="invoice-thumb-img" onclick="window.open('${inv.image_url}', '_blank')"/>`;

            const dateOrdered = new Date(inv.date_ordered).toLocaleDateString('en-GB', {day:'2-digit',month:'short',year:'numeric'});
            const dateCleared = inv.date_cleared ? new Date(inv.date_cleared).toLocaleDateString('en-GB', {day:'2-digit',month:'short',year:'numeric'}) : 'N/A';

            return `
                <div class="invoice-gallery-card">
                    <div class="invoice-thumb">${thumbnail}</div>
                    <div class="invoice-meta">
                        <div class="invoice-meta-row">
                            <i class="fas fa-calendar-alt"></i> Ordered: ${dateOrdered}
                        </div>
                        <div class="invoice-meta-row">
                            <i class="fas fa-check-circle" style="color:var(--accent-green);"></i> Cleared: ${dateCleared}
                        </div>
                        <div class="invoice-meta-row">
                            <i class="fas fa-wine-bottle"></i> ${inv.quantity_ordered} bottles
                        </div>
                    </div>
                    <a href="${inv.image_url}" download="${inv.image_original || 'invoice.jpg'}" class="btn-glass" style="width:100%;text-align:center;font-size:12px;padding:8px;">
                        <i class="fas fa-download"></i> Download
                    </a>
                </div>
            `;
        }).join('');
    } catch (err) {
        grid.innerHTML = `<div style="color:var(--accent-red); padding:24px;"><i class="fas fa-exclamation-circle"></i> Failed to load invoices.</div>`;
    }
}

// ===================================================================
// Weekly PDF Download
// ===================================================================
async function downloadWeeklyPDF() {
    const btn = document.getElementById('btnDownloadWeekPDF');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
    btn.disabled = true;

    try {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
        const pageW = doc.internal.pageSize.getWidth();

        // ---- Header ----
        doc.setFillColor(7, 7, 13);
        doc.rect(0, 0, pageW, 30, 'F');
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(20);
        doc.setTextColor(212, 164, 74);
        doc.text('StockTech', 14, 13);
        doc.setFontSize(11);
        doc.setTextColor(200, 200, 200);
        doc.text('Weekly Wine Sales Analysis', 14, 21);
        doc.setFontSize(10);
        doc.setTextColor(160, 160, 160);
        doc.text(weekLabel, pageW - 14, 14, { align: 'right' });
        doc.text(`Generated: ${new Date().toLocaleDateString('en-GB', {day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'})}`, pageW - 14, 21, { align: 'right' });

        // ---- Day cards section ----
        let y = 40;
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(13);
        doc.setTextColor(255, 255, 255);
        doc.text('Day-by-Day Breakdown', 14, y);
        y += 8;

        const cols = ['Day', 'Date', 'Sold', 'Ordered', 'Comps', 'Top Sold Wine'];
        const colW = [26, 26, 22, 28, 22, pageW - 14 - 14 - 124];
        let x = 14;
        doc.setFillColor(30, 30, 50);
        doc.rect(14, y, pageW - 28, 8, 'F');
        doc.setFontSize(9);
        doc.setTextColor(212, 164, 74);
        cols.forEach((col, i) => { doc.text(col, x + 2, y + 5.5); x += colW[i]; });
        y += 8;

        let totalSold = 0, totalOrdered = 0, totalComps = 0;
        weeklyData.forEach((day, idx) => {
            const compDay = weeklyCompsData[idx] || {};
            const isToday = day.date === new Date().toISOString().split('T')[0];
            doc.setFillColor(idx % 2 === 0 ? 20 : 28, idx % 2 === 0 ? 20 : 28, idx % 2 === 0 ? 35 : 45);
            if (isToday) doc.setFillColor(30, 45, 30);
            doc.rect(14, y, pageW - 28, 7, 'F');

            const topWine = Object.entries(day.wine_details || {})
                .filter(([, v]) => v.sold > 0)
                .sort(([, a], [, b]) => b.sold - a.sold)[0];
            const topWineName = topWine ? `${topWine[0]} (${topWine[1].sold})` : '—';

            doc.setFont('helvetica', isToday ? 'bold' : 'normal');
            doc.setFontSize(8.5);

            x = 14;
            const compTotal = compDay.total_comps || 0;
            const rowData = [day.day_name, day.date_formatted, String(day.total_sold), String(day.total_ordered), String(compTotal), topWineName];
            rowData.forEach((val, i) => {
                if (i === 2) doc.setTextColor(46, 204, 113);
                else if (i === 3) doc.setTextColor(231, 76, 60);
                else if (i === 4) doc.setTextColor(160, 100, 220);
                else doc.setTextColor(isToday ? 150 : 200, isToday ? 220 : 200, isToday ? 150 : 200);
                doc.text(val, x + 2, y + 4.8);
                x += colW[i];
            });

            totalSold += day.total_sold;
            totalOrdered += day.total_ordered;
            totalComps += compTotal;
            y += 7;
        });

        // Totals row
        doc.setFillColor(212, 164, 74, 40);
        doc.rect(14, y, pageW - 28, 8, 'F');
        x = 14;
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(9);
        doc.setTextColor(212, 164, 74);
        doc.text('WEEK TOTAL', x + 2, y + 5.5); x += colW[0];
        doc.text('', x + 2, y + 5.5); x += colW[1];
        doc.setTextColor(46, 204, 113);
        doc.text(String(totalSold), x + 2, y + 5.5); x += colW[2];
        doc.setTextColor(231, 76, 60);
        doc.text(String(totalOrdered), x + 2, y + 5.5); x += colW[3];
        doc.setTextColor(160, 100, 220);
        doc.text(String(totalComps), x + 2, y + 5.5);
        y += 16;

        // ---- Wine detail breakdown ----
        const allWines = {};
        weeklyData.forEach(day => {
            Object.entries(day.wine_details || {}).forEach(([name, vals]) => {
                if (!allWines[name]) allWines[name] = { sold: 0, ordered: 0, glasses_sold: 0, bottles_sold: 0 };
                allWines[name].sold += vals.sold;
                allWines[name].ordered += vals.ordered;
                allWines[name].glasses_sold += (vals.glasses_sold || 0);
                allWines[name].bottles_sold += (vals.bottles_sold || 0);
            });
        });
        const wineList = Object.entries(allWines).sort(([,a],[,b]) => b.sold - a.sold).filter(([,v]) => v.sold > 0 || v.ordered > 0);

        if (wineList.length > 0) {
            if (y > 145) { doc.addPage(); y = 20; }
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(13);
            doc.setTextColor(255, 255, 255);
            doc.text('Wine Performance This Week', 14, y);
            y += 8;

            doc.setFillColor(30, 30, 50);
            doc.rect(14, y, 175, 8, 'F');
            doc.setFontSize(9);
            doc.setTextColor(212, 164, 74);
            doc.text('Wine Name', 16, y + 5.5);
            doc.text('Total Sold', 86, y + 5.5);
            doc.text('Glasses', 111, y + 5.5);
            doc.text('Bottles', 131, y + 5.5);
            doc.text('Ordered', 151, y + 5.5);
            y += 8;

            wineList.forEach(([name, vals], idx) => {
                if (y > 188) { doc.addPage(); y = 20; }
                doc.setFillColor(idx % 2 === 0 ? 20 : 28, idx % 2 === 0 ? 20 : 28, idx % 2 === 0 ? 35 : 45);
                doc.rect(14, y, 175, 7, 'F');
                doc.setFont('helvetica', 'normal');
                doc.setFontSize(8.5);
                doc.setTextColor(220, 220, 220);
                doc.text(name.length > 35 ? name.substring(0,33)+'...' : name, 16, y + 4.8);
                doc.setTextColor(46, 204, 113);
                doc.text(String(vals.sold), 86, y + 4.8);
                doc.setTextColor(150, 200, 255);
                doc.text(String(vals.glasses_sold), 111, y + 4.8);
                doc.text(String(vals.bottles_sold), 131, y + 4.8);
                doc.setTextColor(231, 76, 60);
                doc.text(String(vals.ordered), 151, y + 4.8);
                y += 7;
            });
        }

        // ---- Comps breakdown ----
        const allComps = {};
        weeklyCompsData.forEach(day => {
            Object.entries(day.comp_details || {}).forEach(([name, vals]) => {
                if (!allComps[name]) allComps[name] = { total: 0, glasses: 0, bottles: 0 };
                allComps[name].total += vals.total;
                allComps[name].glasses += (vals.glasses || 0);
                allComps[name].bottles += (vals.bottles || 0);
            });
        });
        const compList = Object.entries(allComps).sort(([,a],[,b]) => b.total - a.total).filter(([,v]) => v.total > 0);

        if (compList.length > 0) {
            if (y > 155) { doc.addPage(); y = 20; }
            y += 6;
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(13);
            doc.setTextColor(160, 100, 220);
            doc.text('Complimentary Drinks This Week', 14, y);
            y += 8;

            doc.setFillColor(40, 20, 60);
            doc.rect(14, y, 135, 8, 'F');
            doc.setFontSize(9);
            doc.setTextColor(180, 120, 255);
            doc.text('Wine Name', 16, y + 5.5);
            doc.text('Total Comps', 86, y + 5.5);
            doc.text('Glasses', 111, y + 5.5);
            doc.text('Bottles', 131, y + 5.5);
            y += 8;

            compList.forEach(([name, vals], idx) => {
                if (y > 188) { doc.addPage(); y = 20; }
                doc.setFillColor(idx % 2 === 0 ? 25 : 32, idx % 2 === 0 ? 15 : 20, idx % 2 === 0 ? 40 : 50);
                doc.rect(14, y, 135, 7, 'F');
                doc.setFont('helvetica', 'normal');
                doc.setFontSize(8.5);
                doc.setTextColor(220, 220, 220);
                doc.text(name.length > 35 ? name.substring(0,33)+'...' : name, 16, y + 4.8);
                doc.setTextColor(160, 100, 220);
                doc.text(String(vals.total), 86, y + 4.8);
                doc.setTextColor(180, 130, 240);
                doc.text(String(vals.glasses), 111, y + 4.8);
                doc.text(String(vals.bottles), 131, y + 4.8);
                y += 7;
            });
        }

        // Footer
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(8);
        doc.setTextColor(100, 100, 100);
        doc.text(`StockTech — ${weekLabel}`, 14, 198);
        doc.text('Confidential', pageW - 14, 198, { align: 'right' });

        const safeLabel = weekLabel.replace(/[^a-zA-Z0-9 \-]/g, '').replace(/\s+/g, '_');
        doc.save(`weekly_report_${safeLabel}.pdf`);
        showToast('Weekly PDF downloaded!', 'success');
    } catch (err) {
        console.error(err);
        showToast('Failed to generate PDF. Please try again.', 'danger');
    } finally {
        btn.innerHTML = '<i class="fas fa-file-pdf" style="color: var(--accent-red);"></i> Download PDF';
        btn.disabled = false;
    }
}

// ===================================================================
// Monthly PDF Download
// ===================================================================
async function downloadMonthlyPDF() {
    const btn = document.getElementById('btnDownloadMonthPDF');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
    btn.disabled = true;

    try {
        const resp = await fetch('/api/monthly-report-data');
        const data = await resp.json();

        const { jsPDF } = window.jspdf;
        const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
        const pageW = doc.internal.pageSize.getWidth();

        // ---- Cover page ----
        doc.setFillColor(7, 7, 13);
        doc.rect(0, 0, pageW, 210, 'F');
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(32);
        doc.setTextColor(212, 164, 74);
        doc.text('StockTech', pageW / 2, 70, { align: 'center' });
        doc.setFontSize(18);
        doc.setTextColor(255, 255, 255);
        doc.text('Monthly Wine Report', pageW / 2, 85, { align: 'center' });
        doc.setFontSize(14);
        doc.setTextColor(160, 160, 160);
        doc.text(data.month_label, pageW / 2, 98, { align: 'center' });
        doc.setFontSize(10);
        doc.setTextColor(120, 120, 120);
        doc.text(`Generated: ${data.generated_at}`, pageW / 2, 112, { align: 'center' });

        // KPI summary on cover
        const kpis = data.kpis;
        doc.setFontSize(12);
        const kpiData = [
            ['Total Units Sold', String(kpis.total_sold)],
            ['Total Bottles Ordered', String(kpis.total_ordered)],
            ['Total Comps Given', String(kpis.total_comps)],
            ['Estimated Revenue', `\u20ac${kpis.total_revenue.toLocaleString('en-IE', {minimumFractionDigits:2})}`],
        ];
        let kpiY = 130;
        kpiData.forEach(([label, val]) => {
            doc.setFont('helvetica', 'normal');
            doc.setTextColor(180, 180, 180);
            doc.text(label, pageW / 2 - 50, kpiY, { align: 'left' });
            doc.setFont('helvetica', 'bold');
            doc.setTextColor(212, 164, 74);
            doc.text(val, pageW / 2 + 50, kpiY, { align: 'right' });
            kpiY += 10;
        });

        // ---- Week pages ----
        data.weeks.forEach(week => {
            doc.addPage();
            let y = 14;

            doc.setFillColor(20, 20, 35);
            doc.rect(0, 0, pageW, 22, 'F');
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(14);
            doc.setTextColor(212, 164, 74);
            doc.text(`Week: ${week.label}`, 14, 14);
            doc.setFontSize(10);
            doc.setTextColor(160, 160, 160);
            doc.text(`Sold: ${week.total_sold} | Ordered: ${week.total_ordered} | Comps: ${week.total_comps}`, pageW - 14, 14, { align: 'right' });
            y = 30;

            const cols = ['Day', 'Date', 'Sold', 'Ordered', 'Comps', 'Top Wines'];
            const colW = [24, 24, 20, 26, 20, pageW - 28 - 14 - 94];
            doc.setFillColor(30, 30, 50);
            doc.rect(14, y, pageW - 28, 8, 'F');
            doc.setFontSize(9);
            doc.setTextColor(212, 164, 74);
            let x = 14;
            cols.forEach((col, i) => { doc.text(col, x + 2, y + 5.5); x += colW[i]; });
            y += 8;

            week.days.forEach((day, idx) => {
                doc.setFillColor(idx % 2 === 0 ? 20 : 28, idx % 2 === 0 ? 20 : 28, idx % 2 === 0 ? 35 : 45);
                doc.rect(14, y, pageW - 28, 7, 'F');
                const topEntries = Object.entries(day.wine_details || {})
                    .filter(([, v]) => v.sold > 0)
                    .sort(([, a], [, b]) => b.sold - a.sold)
                    .slice(0, 2)
                    .map(([n, v]) => `${n.substring(0, 12)} (${v.sold})`)
                    .join(', ');
                x = 14;
                const rowVals = [
                    day.day_name.substring(0,3),
                    day.date_formatted,
                    String(day.total_sold),
                    String(day.total_ordered),
                    String(day.total_comps || 0),
                    topEntries || '\u2014'
                ];
                rowVals.forEach((val, i) => {
                    doc.setFont('helvetica', 'normal');
                    doc.setFontSize(8.5);
                    if (i === 2) doc.setTextColor(46, 204, 113);
                    else if (i === 3) doc.setTextColor(231, 76, 60);
                    else if (i === 4) doc.setTextColor(160, 100, 220);
                    else doc.setTextColor(210, 210, 210);
                    doc.text(val, x + 2, y + 4.8);
                    x += colW[i];
                });
                y += 7;
            });

            // Week comps breakdown if any
            const weekCompDetails = {};
            week.days.forEach(day => {
                Object.entries(day.comp_details || {}).forEach(([name, vals]) => {
                    if (!weekCompDetails[name]) weekCompDetails[name] = { total: 0, glasses: 0, bottles: 0 };
                    weekCompDetails[name].total += vals.total;
                    weekCompDetails[name].glasses += (vals.glasses || 0);
                    weekCompDetails[name].bottles += (vals.bottles || 0);
                });
            });
            const weekCompList = Object.entries(weekCompDetails).filter(([,v]) => v.total > 0);

            if (weekCompList.length > 0 && y < 170) {
                y += 6;
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(10);
                doc.setTextColor(160, 100, 220);
                doc.text('Complimentary Drinks This Week:', 14, y);
                y += 6;
                weekCompList.forEach(([name, vals]) => {
                    if (y > 188) return;
                    doc.setFont('helvetica', 'normal');
                    doc.setFontSize(8.5);
                    doc.setTextColor(180, 130, 240);
                    const shortName = name.length > 30 ? name.substring(0,28)+'...' : name;
                    doc.text(`${shortName}: ${vals.total} total (${vals.glasses}gl + ${vals.bottles}bt)`, 18, y);
                    y += 6;
                });
            }
        });

        // ---- Wine summary page ----
        doc.addPage();
        let y = 14;
        doc.setFillColor(20, 20, 35);
        doc.rect(0, 0, pageW, 22, 'F');
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(14);
        doc.setTextColor(212, 164, 74);
        doc.text(`Wine Performance — ${data.month_label}`, 14, 14);
        y = 30;

        const wCols = ['Wine Name', 'Sold', 'Comps', 'Revenue \u20ac', 'Profit \u20ac', 'Stock'];
        const wColW = [82, 22, 22, 34, 34, 30];
        doc.setFillColor(30, 30, 50);
        doc.rect(14, y, pageW - 28, 8, 'F');
        doc.setFontSize(9);
        doc.setTextColor(212, 164, 74);
        let x = 14;
        wCols.forEach((col, i) => { doc.text(col, x + 2, y + 5.5); x += wColW[i]; });
        y += 8;

        data.wine_summary.forEach((wine, idx) => {
            if (y > 188) { doc.addPage(); y = 20; }
            doc.setFillColor(idx % 2 === 0 ? 20 : 28, idx % 2 === 0 ? 20 : 28, idx % 2 === 0 ? 35 : 45);
            doc.rect(14, y, pageW - 28, 7, 'F');
            x = 14;
            const wRow = [
                wine.name.length > 40 ? wine.name.substring(0,38)+'...' : wine.name,
                String(wine.sold),
                String(wine.comps || 0),
                wine.revenue.toFixed(2),
                wine.profit.toFixed(2),
                String(wine.current_stock)
            ];
            wRow.forEach((val, i) => {
                doc.setFont('helvetica', idx === 0 ? 'bold' : 'normal');
                doc.setFontSize(8.5);
                if (i === 1) doc.setTextColor(46, 204, 113);
                else if (i === 2) doc.setTextColor(160, 100, 220);
                else if (i === 3) doc.setTextColor(91, 141, 239);
                else if (i === 4) doc.setTextColor(idx === 0 ? 212 : 180, 164, idx === 0 ? 74 : 160);
                else doc.setTextColor(210, 210, 210);
                doc.text(val, x + 2, y + 4.8);
                x += wColW[i];
            });
            y += 7;
        });

        // Footer
        doc.setFontSize(8);
        doc.setTextColor(100, 100, 100);
        doc.text(`StockTech — ${data.month_label}`, 14, 198);
        doc.text('Confidential', pageW - 14, 198, { align: 'right' });

        doc.save(`monthly_report_${data.month_label.replace(' ', '_')}.pdf`);
        showToast('Monthly PDF downloaded!', 'success');
    } catch (err) {
        console.error(err);
        showToast('Failed to generate PDF.', 'danger');
    } finally {
        btn.innerHTML = '<i class="fas fa-file-pdf" style="color: var(--accent-red);"></i> Download Month PDF';
        btn.disabled = false;
    }
}

// ===================================================================
// KPI Counter Animation
// ===================================================================
function animateCounters() {
    document.querySelectorAll('.kpi-value[data-count]').forEach(el => {
        const target = parseFloat(el.dataset.count);
        const isEuro = target > 10;
        const duration = 1200;
        const start = performance.now();

        function update(now) {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = target * eased;

            if (isEuro) {
                el.textContent = `\u20ac${current.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
            } else {
                el.textContent = Math.round(current);
            }

            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }

        requestAnimationFrame(update);
    });
}

// ===================================================================
// Toast helper (referenced above, defined in base.html or here)
// ===================================================================
function showToast(message, type = 'success') {
    // Try base.html's showToast if available, otherwise create one
    const existing = document.getElementById('toastContainer');
    let container = existing;
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:10px;';
        document.body.appendChild(container);
    }

    const colors = { success: '#2ecc71', danger: '#e74c3c', warning: '#f39c12', info: '#3498db' };
    const toast = document.createElement('div');
    toast.style.cssText = `
        background: rgba(20,20,35,0.95);
        border-left: 4px solid ${colors[type] || colors.info};
        color: #e0e0e0;
        padding: 14px 20px;
        border-radius: 10px;
        font-size: 14px;
        font-weight: 500;
        max-width: 320px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        animation: fadeSlideIn 0.3s ease;
        backdrop-filter: blur(10px);
    `;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ===================================================================
// Init
// ===================================================================
document.addEventListener('DOMContentLoaded', () => {
    // Animate KPI counters when they come into view
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounters();
                observer.disconnect();
            }
        });
    }, { threshold: 0.2 });

    const kpiSection = document.getElementById('sectionKPIs');
    if (kpiSection) observer.observe(kpiSection);

    // Auto-expand today's day card if it has data
    const todayCard = document.querySelector('.weekly-day-card:not(.comp-day-card).today');
    if (todayCard) {
        const idx = parseInt(todayCard.dataset.dayIndex);
        if (weeklyData[idx] && Object.keys(weeklyData[idx].wine_details).length > 0) {
            setTimeout(() => toggleDayDetail(todayCard, idx), 600);
        }
    }

    // Initialize sale stock hint
    updateSaleStockInfo();

    // Add CSS for animations if not already present
    if (!document.getElementById('dynamicStyles')) {
        const style = document.createElement('style');
        style.id = 'dynamicStyles';
        style.textContent = `
            @keyframes fadeSlideIn {
                from { opacity: 0; transform: translateY(-8px); }
                to { opacity: 1; transform: translateY(0); }
            }
        `;
        document.head.appendChild(style);
    }
});
