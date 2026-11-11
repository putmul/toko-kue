(function () {
    'use strict';

    const root = document.querySelector('[data-mis-dashboard]');
    if (!root) return;

    const startInput = root.querySelector('[data-mis-start-date]');
    const endInput = root.querySelector('[data-mis-end-date]');
    const applyButton = root.querySelector('[data-mis-apply]');
    const errorBox = root.querySelector('[data-mis-error]');
    const refreshState = root.querySelector('[data-mis-refresh-state]');
    const numberFormat = new Intl.NumberFormat('id-ID');
    const currencyFormat = new Intl.NumberFormat('id-ID', {
        style: 'currency', currency: 'IDR', maximumFractionDigits: 0
    });

    function dateString(date) {
        return date.toISOString().slice(0, 10);
    }

    function setDefaultPeriod() {
        const end = new Date();
        const start = new Date(end);
        start.setDate(start.getDate() - 29);
        startInput.value = dateString(start);
        endInput.value = dateString(end);
    }

    function showError(message) {
        errorBox.textContent = message;
        errorBox.hidden = false;
    }

    function clearError() {
        errorBox.textContent = '';
        errorBox.hidden = true;
    }

    function setText(selector, value) {
        const element = root.querySelector(selector);
        if (element) element.textContent = value;
    }

    function formatDate(value) {
        const parts = String(value).split('-');
        if (parts.length !== 3) return value;
        return `${parts[2]}/${parts[1]}`;
    }

    function escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"']/g, character => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
        }[character]));
    }

    function iconMarkup(name, extraClass) {
        return `<svg class="ui-icon ${extraClass || ''}" aria-hidden="true" focusable="false"><use href="#icon-${name}"></use></svg>`;
    }

    function renderKpi(kpi) {
        setText('[data-kpi="total_pendapatan"]', currencyFormat.format(kpi.total_pendapatan || 0));
        setText('[data-kpi="transaksi_berhasil"]', numberFormat.format(kpi.transaksi_berhasil || 0));
        setText('[data-kpi="rata_rata_transaksi"]', currencyFormat.format(kpi.rata_rata_transaksi || 0));
        setText('[data-kpi="alert_terbuka"]', numberFormat.format(kpi.alert_terbuka || 0));
        setText('[data-kpi-subtitle="total_transaksi"]', `${numberFormat.format(kpi.total_transaksi || 0)} total transaksi`);
        setText('[data-kpi-alert-caption]', `${numberFormat.format(kpi.request_menunggu || 0)} request stok menunggu`);
    }

    function renderSalesChart(rows) {
        const container = root.querySelector('[data-chart-sales]');
        if (!rows.length || rows.every(row => !row.pendapatan && !row.transaksi_berhasil)) {
            container.innerHTML = '<div class="mis-empty-chart">Belum ada data penjualan pada periode ini.</div>';
            return;
        }

        const width = 760;
        const height = 280;
        const padding = { top: 20, right: 20, bottom: 45, left: 62 };
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;
        const maxValue = Math.max(...rows.map(row => Number(row.pendapatan) || 0), 1);
        const points = rows.map((row, index) => {
            const x = padding.left + (rows.length === 1 ? chartWidth / 2 : (index / (rows.length - 1)) * chartWidth);
            const y = padding.top + chartHeight - ((Number(row.pendapatan) || 0) / maxValue) * chartHeight;
            return { x, y, row };
        });
        const path = points.map((point, index) => `${index ? 'L' : 'M'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(' ');
        const area = `${path} L ${points[points.length - 1].x.toFixed(2)} ${padding.top + chartHeight} L ${points[0].x.toFixed(2)} ${padding.top + chartHeight} Z`;
        const grid = [0, 1, 2, 3, 4].map(index => {
            const y = padding.top + (index / 4) * chartHeight;
            const value = maxValue - (index / 4) * maxValue;
            return `<line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" class="mis-grid-line" />
                <text x="${padding.left - 10}" y="${y + 4}" text-anchor="end" class="mis-axis-label">${currencyFormat.format(value).replace(',00', '')}</text>`;
        }).join('');
        const labels = points.map((point, index) => {
            if (rows.length > 12 && index % Math.ceil(rows.length / 6) !== 0 && index !== rows.length - 1) return '';
            return `<text x="${point.x}" y="${height - 15}" text-anchor="middle" class="mis-axis-label">${formatDate(point.row.tanggal)}</text>`;
        }).join('');
        const dots = points.map(point => `<circle cx="${point.x}" cy="${point.y}" r="4" class="mis-chart-dot"><title>${point.row.tanggal}: ${currencyFormat.format(point.row.pendapatan || 0)}</title></circle>`).join('');

        container.innerHTML = `<svg class="mis-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Grafik tren penjualan">
            ${grid}
            <path d="${area}" class="mis-area-path"></path>
            <path d="${path}" class="mis-line-path"></path>
            ${dots}
            ${labels}
        </svg>
        <div class="mis-chart-legend"><span class="mis-legend-dot"></span>Pendapatan berhasil</div>`;
    }

    function renderProducts(products) {
        const container = root.querySelector('[data-chart-products]');
        if (!products.length) {
            container.innerHTML = '<div class="mis-empty-chart">Belum ada produk terjual.</div>';
            return;
        }
        const max = Math.max(...products.map(product => Number(product.jumlah_terjual) || 0), 1);
        container.innerHTML = products.map(product => {
            const percentage = Math.max(5, ((Number(product.jumlah_terjual) || 0) / max) * 100);
            return `<div class="mis-bar-row">
                <div class="mis-bar-label"><span>${escapeHtml(product.nama)}</span><strong>${numberFormat.format(product.jumlah_terjual)} unit</strong></div>
                <div class="mis-bar-track"><span style="width: ${percentage}%"></span></div>
                <small>${currencyFormat.format(product.pendapatan || 0)}</small>
            </div>`;
        }).join('');
    }

    function renderBranches(branches) {
        const container = root.querySelector('[data-chart-branches]');
        // Dashboard manajer tidak menampilkan perbandingan cabang.
        if (!container) return;
        if (!branches.length) {
            container.innerHTML = '<div class="mis-empty-chart">Belum ada data cabang.</div>';
            return;
        }
        const max = Math.max(...branches.map(branch => Number(branch.pendapatan) || 0), 1);
        container.innerHTML = branches.map(branch => {
            const percentage = Math.max(3, ((Number(branch.pendapatan) || 0) / max) * 100);
            return `<div class="mis-branch-row">
                <div class="mis-branch-label"><span>${escapeHtml(branch.cabang)}</span><strong>${currencyFormat.format(branch.pendapatan || 0)}</strong></div>
                <div class="mis-branch-track"><span style="width: ${percentage}%"></span></div>
                <small>${numberFormat.format(branch.transaksi_berhasil || 0)} transaksi berhasil</small>
            </div>`;
        }).join('');
    }

    function renderStock(stock) {
        const summary = stock.summary || {};
        ['normal', 'menipis', 'habis'].forEach(status => {
            setText(`[data-stock-count="${status}"]`, numberFormat.format(summary[status] || 0));
        });
        const list = root.querySelector('[data-stock-list]');
        const attention = (stock.items || []).filter(item => item.status_stok !== 'normal').slice(0, 6);
        if (!attention.length) {
            list.innerHTML = '<div class="mis-inline-empty">Semua stok berada di atas batas minimum.</div>';
            return;
        }
        list.innerHTML = attention.map(item => `<div class="mis-stock-row">
            <div><strong>${escapeHtml(item.produk)}</strong><small>${escapeHtml(item.cabang)}</small></div>
            <span class="mis-status-badge ${item.status_stok === 'habis' ? 'habis' : 'menipis'}">${item.stok_cabang} / min ${item.stok_minimum}</span>
        </div>`).join('');
    }

    function renderAlerts(alerts) {
        const list = root.querySelector('[data-alert-list]');
        if (!alerts.length) {
            list.innerHTML = '<div class="mis-inline-empty">Tidak ada alert terbuka.</div>';
            return;
        }
        list.innerHTML = alerts.map(alert => `<div class="mis-alert-row ${alert.tingkat}">
            <div class="mis-alert-mark">${iconMarkup('alert')}</div>
            <div class="mis-alert-copy"><strong>${escapeHtml(alert.judul)}</strong><p>${escapeHtml(alert.pesan)}</p><small>${escapeHtml(alert.cabang || 'Semua cabang')}</small></div>
            <button type="button" class="mis-alert-handle" data-alert-id="${alert.id}">Tangani</button>
        </div>`).join('');
        list.querySelectorAll('[data-alert-id]').forEach(button => {
            button.addEventListener('click', () => handleAlert(button.dataset.alertId));
        });
    }

    async function handleAlert(alertId) {
        const button = root.querySelector(`[data-alert-id="${alertId}"]`);
        if (button) { button.disabled = true; button.textContent = '...'; }
        try {
            const response = await fetch(`/api/mis/alerts/${alertId}/tangani`, { method: 'POST', credentials: 'same-origin' });
            if (!response.ok) throw new Error('Alert gagal diperbarui.');
            await loadDashboard();
        } catch (error) {
            showError(error.message);
            if (button) { button.disabled = false; button.textContent = 'Tangani'; }
        }
    }

    async function loadDashboard() {
        clearError();
        applyButton.disabled = true;
        refreshState.textContent = 'Memuat data...';
        const params = new URLSearchParams({ start_date: startInput.value, end_date: endInput.value });
        try {
            const response = await fetch(`/api/mis/dashboard?${params.toString()}`, { credentials: 'same-origin' });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || 'Dashboard gagal dimuat.');
            renderKpi(payload.kpi);
            renderSalesChart(payload.sales_trend || []);
            renderProducts(payload.top_products || []);
            renderBranches(payload.branch_comparison || []);
            renderStock(payload.stock || {});
            renderAlerts(payload.alerts || []);
            refreshState.textContent = payload.meta && payload.meta.last_refresh ? `Diperbarui ${payload.meta.last_refresh}` : 'Data terbaru';
        } catch (error) {
            showError(error.message);
            refreshState.textContent = 'Gagal memuat data';
        } finally {
            applyButton.disabled = false;
        }
    }

    setDefaultPeriod();
    applyButton.addEventListener('click', loadDashboard);
    loadDashboard();
})();
