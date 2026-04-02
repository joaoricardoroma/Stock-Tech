/**
 * Wine Stock Dashboard — Interactive JavaScript
 * Handles: day-card clicks, table sorting/filtering, modals,
 * invoice clearing, KPI counter animations, stock filtering.
 */

// ===================================================================
// Weekly Data from server
// ===================================================================
const weeklyData = JSON.parse(
    document.getElementById('weeklyDataJSON').textContent
);

// ===================================================================
// Day Card Interactions
// ===================================================================
let selectedDayIndex = null;

function toggleDayDetail(card, index) {
    const panel = document.getElementById('dayDetailPanel');
    const allCards = document.querySelectorAll('.weekly-day-card');

    // Deselect if clicking same card
    if (selectedDayIndex === index) {
        panel.style.display = 'none';
        card.classList.remove('selected');
        selectedDayIndex = null;
        return;
    }

    // Remove previous selection
    allCards.forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    selectedDayIndex = index;

    const day = weeklyData[index];
    const titleEl = document.getElementById('dayDetailTitle');
    titleEl.textContent = `${day.day_name} — ${day.date_formatted}`;

    const bodyEl = document.getElementById('dayDetailBody');
    const details = day.wine_details;
    const keys = Object.keys(details);

    if (keys.length === 0) {
        bodyEl.innerHTML = '<div class="day-wine-item" style="justify-content:center; color: var(--text-muted);">No activity this day</div>';
    } else {
        bodyEl.innerHTML = keys.map(name => {
            const d = details[name];
            return `
                <div class="day-wine-item">
                    <span class="day-wine-name">${name}</span>
                    <div class="day-wine-stats">
                        ${d.sold > 0 ? `<span class="day-wine-sold">-${d.sold} sold</span>` : ''}
                        ${d.ordered > 0 ? `<span class="day-wine-ordered">+${d.ordered} ordered</span>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }

    panel.style.display = 'block';
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function closeDayDetail() {
    document.getElementById('dayDetailPanel').style.display = 'none';
    document.querySelectorAll('.weekly-day-card').forEach(c => c.classList.remove('selected'));
    selectedDayIndex = null;
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

    // Determine if numeric
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

    // Update sort icons
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

// Close on overlay click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.classList.remove('active');
            document.body.style.overflow = '';
        }
    });
});

// Close on Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.active').forEach(m => {
            m.classList.remove('active');
        });
        document.body.style.overflow = '';
    }
});

// ===================================================================
// API Calls
// ===================================================================

async function submitSale() {
    const wineId = document.getElementById('saleWineSelect').value;
    const quantity = parseInt(document.getElementById('saleQuantity').value);
    const date = document.getElementById('saleDate').value;

    try {
        const resp = await fetch('/api/wine/sale', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ wine_id: parseInt(wineId), quantity, date })
        });

        const data = await resp.json();
        if (data.success) {
            showToast(`Sale recorded! New stock: ${data.new_stock}`, 'success');
            closeModal('addSaleModal');
            setTimeout(() => location.reload(), 1200);
        } else {
            showToast(data.error || 'Failed to record sale', 'danger');
        }
    } catch (err) {
        showToast('Network error', 'danger');
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

async function clearInvoice(purchaseId, btn) {
    try {
        const resp = await fetch(`/api/wine/clear-invoice/${purchaseId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await resp.json();
        if (data.success) {
            btn.innerHTML = '<i class="fas fa-check-double"></i> Cleared';
            btn.classList.add('cleared');
            showToast(`Invoice cleared! Stock updated to ${data.new_stock}`, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showToast(data.error || 'Failed', 'danger');
        }
    } catch (err) {
        showToast('Network error', 'danger');
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
            // Ease out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = target * eased;

            if (isEuro) {
                el.textContent = `€${current.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
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
    const todayCard = document.querySelector('.weekly-day-card.today');
    if (todayCard) {
        const idx = parseInt(todayCard.dataset.dayIndex);
        if (weeklyData[idx] && Object.keys(weeklyData[idx].wine_details).length > 0) {
            // Small delay for animation
            setTimeout(() => toggleDayDetail(todayCard, idx), 600);
        }
    }
});
