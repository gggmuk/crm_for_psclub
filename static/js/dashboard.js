/* ==========================================
   CyberLounge Dashboard — Production JS
   ========================================== */

// State
let currentTab = 'operational';
let clientsData = [];
let filteredClients = [];
let clientsPage = 0;
const CLIENTS_PER_PAGE = 20;
let bookingsCache = [];
let recentSessionsCache = [];
let charts = {};

// ============ UTILITIES ============
function getCookie(name) {
    let v = null;
    if (document.cookie) {
        document.cookie.split(';').forEach(c => {
            c = c.trim();
            if (c.startsWith(name + '=')) v = decodeURIComponent(c.substring(name.length + 1));
        });
    }
    return v;
}

function showToast(msg, type = 'success') {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = `toast ${type}`;
    t.classList.remove('hidden');
    setTimeout(() => t.classList.add('hidden'), 3000);
}

function formatDateTime(s) {
    if (!s) return '—';
    const d = new Date(s);
    return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function formatMoney(n) { return Math.round(n || 0).toLocaleString('ru-RU'); }

function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }

// ============ TAB SWITCHING ============
const tabTitles = { operational: 'Операции', analytics: 'Аналитика', clients: 'Клиенты', bookings: 'Бронирования', management: 'Управление', scanner: 'QR Сканер' };

function switchTab(tab) {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(`tab-${tab}`).classList.add('active');
    ['operational', 'analytics', 'clients', 'bookings', 'management', 'scanner'].forEach(t => {
        const el = document.getElementById(`view-${t}`);
        if (el) el.classList.add('hidden');
    });
    document.getElementById(`view-${tab}`).classList.remove('hidden');
    document.getElementById('page-title').textContent = tabTitles[tab];
    currentTab = tab;
    document.getElementById('sidebar').classList.remove('open');

    if (tab === 'operational') { fetchPlaces(); fetchTariffs(); fetchQuickStats(); }
    else if (tab === 'analytics') loadAnalytics();
    else if (tab === 'clients') loadClients();
    else if (tab === 'bookings') { loadBookingStats(); loadAllBookings(); }
    else if (tab === 'management') loadManagement();
    else if (tab === 'scanner') resetScanner();
}

// ============ QUICK STATS ============
async function fetchQuickStats() {
    try {
        const res = await fetch('/api/manager_stats/');
        const d = await res.json();
        document.getElementById('qs-active').textContent = d.active_sessions || 0;
        document.getElementById('qs-completed').textContent = d.completed_sessions || 0;
        document.getElementById('qs-revenue').textContent = formatMoney(d.total_revenue_day) + ' сом';
        document.getElementById('qs-occupancy').textContent = (d.occupancy_rate_current || 0) + '%';
    } catch (e) { console.error('Quick stats error:', e); }
}

// ============ PLACES ============
async function fetchPlaces() {
    try {
        const res = await fetch('/api/place_status/');
        const places = await res.json();
        const grid = document.getElementById('places-grid');
        grid.innerHTML = '';

        places.forEach(p => {
            const isFree = p.status === 'free';
            const isMaint = p.status === 'maintenance';
            const typeClass = (p.place_type || 'Basic').toLowerCase();

            let timeHTML = '';
            if (!isFree && p.active_session) {
                if (p.active_session.scheduled_end_time) {
                    const end = new Date(p.active_session.scheduled_end_time);
                    const diff = Math.ceil((end - new Date()) / 60000);
                    if (diff > 0) {
                        const h = Math.floor(diff / 60), m = diff % 60;
                        timeHTML = `<div class="time-remaining">⏳ ${h > 0 ? h + 'ч ' : ''}${m}мин</div>`;
                    } else {
                        timeHTML = '<div class="time-remaining time-expired">⏰ Время вышло!</div>';
                    }
                } else {
                    const s = new Date(p.active_session.start_time);
                    timeHTML = `<div class="place-meta">🕐 с ${s.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}</div>`;
                }
            }

            const tariffHTML = p.tariff_info
                ? `<div class="place-meta">💰 ${p.tariff_info.name} — ${p.tariff_info.hourly_rate} сом/ч</div>`
                : '<div class="place-meta">Нет тарифа</div>';

            const actionsHTML = isFree
                ? `<div class="place-actions"><button class="btn-start" onclick="openStartModal(${p.id})">✨ Начать</button></div>`
                : isMaint ? '' : `<div class="place-actions">
                    <button class="btn-prolong" onclick="openProlongModal(${p.active_session?.id})">⏱️ Продлить</button>
                    <button class="btn-stop" onclick="stopSession(${p.active_session?.id})">⏹ Стоп</button>
                  </div>`;

            const card = document.createElement('div');
            card.className = `place-card glass-card ${p.status}`;
            card.innerHTML = `
                <div class="place-name">${p.name}</div>
                <span class="place-type-badge ${typeClass}">${p.place_type || 'Basic'}</span>
                <div class="place-status-row"><span class="status-dot ${p.status}"></span><span class="place-status-text">${isFree ? 'Свободно' : isMaint ? 'Обслуживание' : 'Занято'}</span></div>
                ${!isFree && p.client_name ? `<div class="place-meta">👤 ${p.client_name}</div>` : ''}
                ${tariffHTML}${timeHTML}${actionsHTML}
            `;
            grid.appendChild(card);
        });
    } catch (e) { console.error('Places error:', e); }
}

async function fetchTariffs() {
    try {
        const res = await fetch('/api/tariffs/');
        const tariffs = await res.json();
        const c = document.getElementById('tariffs-list');
        c.innerHTML = tariffs.length === 0 ? '<div class="place-meta" style="text-align:center;padding:12px">Нет тарифов</div>' : '';
        tariffs.forEach(t => {
            c.innerHTML += `<div class="tariff-item"><div class="tariff-item-name">${t.name}</div><div class="tariff-item-price">${t.hourly_rate} сом/ч</div>${t.description ? `<div class="tariff-item-desc">${t.description}</div>` : ''}</div>`;
        });
    } catch (e) { console.error('Tariffs error:', e); }
}

// ============ SESSION CONTROL ============
async function openStartModal(placeId) {
    document.getElementById('placeId').value = placeId;
    document.getElementById('startModal').classList.remove('hidden');
    document.getElementById('isGuest').checked = false;
    toggleGuestMode();
    document.getElementById('telegramId').value = '';
    document.getElementById('clientName').value = '';
    document.getElementById('duration').value = '0';
    document.querySelectorAll('#startModal .dur-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('#startModal .dur-btn').classList.add('active');
    try {
        const res = await fetch('/api/promotions/');
        const promos = await res.json();
        const sel = document.getElementById('promotion');
        sel.innerHTML = '<option value="">Без акции</option>';
        promos.forEach(p => { if (p.is_active) sel.innerHTML += `<option value="${p.id}">${p.name} (-${p.discount_percentage}%)</option>`; });
    } catch (e) { console.error(e); }
}

function toggleGuestMode() {
    const g = document.getElementById('isGuest').checked;
    document.getElementById('telegramField').style.display = g ? 'none' : 'block';
    document.getElementById('nameLabel').innerHTML = g ? 'Имя гостя <small style="color:#ef4444">*</small>' : 'Имя клиента <small>(для новых)</small>';
}

function selectDuration(m, btn) {
    document.getElementById('duration').value = m;
    document.querySelectorAll('#startModal .dur-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
}

async function submitStart() {
    const placeId = document.getElementById('placeId').value;
    const isGuest = document.getElementById('isGuest').checked;
    const telegramId = document.getElementById('telegramId').value;
    const clientName = document.getElementById('clientName').value.trim();
    const duration = document.getElementById('duration').value;
    const promotionId = document.getElementById('promotion').value;

    if (!isGuest && !telegramId) { showToast('Введите Telegram ID', 'error'); return; }
    if (isGuest && !clientName) { showToast('Введите имя гостя', 'error'); return; }

    try {
        const payload = { place_id: placeId, is_guest: isGuest, duration: duration > 0 ? duration : null, promotion_id: promotionId || null };
        if (isGuest) payload.guest_name = clientName;
        else { payload.telegram_id = telegramId; if (clientName) payload.client_name = clientName; }

        const res = await fetch('/api/start_session/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify(payload)
        });
        if (res.ok) { closeModal('startModal'); fetchPlaces(); fetchQuickStats(); showToast('✅ Сессия начата!'); }
        else { const err = await res.json(); showToast('❌ ' + (err.error || 'Ошибка'), 'error'); }
    } catch (e) { showToast('❌ Ошибка соединения', 'error'); }
}

function openProlongModal(sid) {
    if (!sid) return;
    document.getElementById('prolongSessionId').value = sid;
    document.getElementById('prolongModal').classList.remove('hidden');
    document.querySelectorAll('#prolongModal .dur-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('#prolongModal .dur-btn')[1].classList.add('active');
}

function setProlongTime(m) {
    document.getElementById('prolongMinutes').value = m;
    document.querySelectorAll('#prolongModal .dur-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
}

async function submitProlong() {
    const sid = document.getElementById('prolongSessionId').value;
    const mins = document.getElementById('prolongMinutes').value;
    try {
        const res = await fetch('/api/prolong_session/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ session_id: sid, minutes_to_add: mins })
        });
        if (res.ok) { closeModal('prolongModal'); fetchPlaces(); showToast('✅ Сессия продлена!'); }
        else showToast('❌ Ошибка', 'error');
    } catch (e) { showToast('❌ Ошибка', 'error'); }
}

async function stopSession(sid) {
    if (!confirm('Завершить сессию?')) return;
    try {
        const res = await fetch(`/api/stop_session/${sid}/`, { method: 'POST', headers: { 'X-CSRFToken': getCookie('csrftoken') } });
        if (res.ok) { fetchPlaces(); fetchQuickStats(); showToast('✅ Сессия завершена!'); }
        else showToast('❌ Ошибка', 'error');
    } catch (e) { showToast('❌ Ошибка', 'error'); }
}

function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

// ============ ANALYTICS ============
async function loadAnalytics() {
    try {
        const [statsRes, revRes, occRes, clientsRes, sessRes] = await Promise.all([
            fetch('/api/manager_stats/'), fetch('/api/analytics/revenue/'),
            fetch('/api/analytics/occupancy/'), fetch('/api/analytics/clients/'),
            fetch('/api/analytics/sessions/')
        ]);
        const stats = await statsRes.json();
        const rev = await revRes.json();
        const occ = await occRes.json();
        const cl = await clientsRes.json();
        const sess = await sessRes.json();

        document.getElementById('kpi-revenue').textContent = formatMoney(stats.total_revenue_day) + ' сом';
        document.getElementById('kpi-occupancy').textContent = (stats.occupancy_rate_current || 0) + '%';
        document.getElementById('kpi-avg-check').textContent = formatMoney(stats.avg_session_cost) + ' сом';
        document.getElementById('kpi-top-place').textContent = stats.top_performing_place_name || 'N/A';

        renderChart('revenueChart', 'line', {
            labels: rev.daily.map(d => d.day_label),
            datasets: [{ label: 'Выручка', data: rev.daily.map(d => d.revenue), borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)', borderWidth: 2.5, fill: true, tension: 0.4, pointRadius: 2, pointHoverRadius: 5 }]
        });
        renderChart('occupancyChart', 'bar', {
            labels: occ.hourly_heatmap.map(h => h.label),
            datasets: [{ label: 'Загрузка %', data: occ.hourly_heatmap.map(h => h.avg_occupancy), backgroundColor: occ.hourly_heatmap.map(h => h.avg_occupancy > 60 ? 'rgba(239,68,68,0.6)' : h.avg_occupancy > 30 ? 'rgba(245,158,11,0.6)' : 'rgba(16,185,129,0.6)'), borderRadius: 4 }]
        });
        if (rev.by_place_type.length > 0) {
            renderChart('typeRevenueChart', 'doughnut', {
                labels: rev.by_place_type.map(t => t.place_type),
                datasets: [{ data: rev.by_place_type.map(t => t.total_revenue), backgroundColor: ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981'], borderWidth: 0 }]
            }, { cutout: '65%' });
        }
        renderChart('durationChart', 'bar', {
            labels: sess.duration_distribution.map(d => d.label),
            datasets: [{ label: 'Сессий', data: sess.duration_distribution.map(d => d.count), backgroundColor: 'rgba(139,92,246,0.6)', borderRadius: 4 }]
        });
        if (cl.rank_distribution.length > 0) {
            renderChart('rankChart', 'pie', {
                labels: cl.rank_distribution.map(r => r.rank),
                datasets: [{ data: cl.rank_distribution.map(r => r.count), backgroundColor: ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#ef4444'], borderWidth: 0 }]
            });
        }
        document.getElementById('summary-stats').innerHTML = `
            <div class="summary-item"><div class="summary-item-val" style="color:#3b82f6">${formatMoney(rev.all_time.total_revenue)} сом</div><div class="summary-item-label">Всего выручка</div></div>
            <div class="summary-item"><div class="summary-item-val" style="color:#8b5cf6">${rev.all_time.total_sessions}</div><div class="summary-item-label">Всего сессий</div></div>
            <div class="summary-item"><div class="summary-item-val" style="color:#10b981">${cl.total_clients}</div><div class="summary-item-label">Клиентов</div></div>
            <div class="summary-item"><div class="summary-item-val" style="color:#f59e0b">${Math.round(sess.avg_duration_minutes)}м</div><div class="summary-item-label">Ср. длительность</div></div>
            <div class="summary-item"><div class="summary-item-val" style="color:#ec4899">${sess.guest_sessions}</div><div class="summary-item-label">Гостевых сессий</div></div>
            <div class="summary-item"><div class="summary-item-val" style="color:#60a5fa">${Math.round(cl.avg_bonus_points)}</div><div class="summary-item-label">Ср. бонусы</div></div>
        `;

        const tbody = document.getElementById('recent-sessions-body');
        tbody.innerHTML = '';
        recentSessionsCache = sess.recent_sessions || [];
        sess.recent_sessions.forEach(s => {
            tbody.innerHTML += `<tr>
                <td>${s.id}</td><td>${s.place_name}</td><td>${s.client_name}</td>
                <td>${formatDateTime(s.start_time)}</td><td>${formatDateTime(s.end_time)}</td>
                <td><strong>${formatMoney(s.cost)} сом</strong></td>
                <td><span class="badge badge-green">Завершена</span></td>
            </tr>`;
        });
    } catch (e) { console.error('Analytics error:', e); }
}

function renderChart(id, type, data, extraOpts = {}) {
    if (charts[id]) charts[id].destroy();
    const ctx = document.getElementById(id)?.getContext('2d');
    if (!ctx) return;
    const isDoughnutOrPie = type === 'doughnut' || type === 'pie';
    charts[id] = new Chart(ctx, {
        type, data,
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: isDoughnutOrPie, position: 'bottom', labels: { color: '#94a3b8', font: { size: 11 }, padding: 16 } } },
            scales: isDoughnutOrPie ? {} : {
                y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#64748b', font: { size: 11 } } },
                x: { grid: { display: false }, ticks: { color: '#64748b', font: { size: 10 }, maxRotation: 45 } }
            },
            ...extraOpts
        }
    });
}

// ============ CLIENTS ============
async function loadClients() {
    try {
        const res = await fetch('/api/clients/?limit=500');
        clientsData = await res.json();
        filteredClients = clientsData;
        clientsPage = 0;
        renderClientsPage();
    } catch (e) { console.error(e); }
}

function renderClientsPage() {
    const total = Math.max(Math.ceil(filteredClients.length / CLIENTS_PER_PAGE), 1);
    if (clientsPage >= total) clientsPage = total - 1;
    const slice = filteredClients.slice(clientsPage * CLIENTS_PER_PAGE, (clientsPage + 1) * CLIENTS_PER_PAGE);
    renderClients(slice);
    const info = document.getElementById('clients-page-info');
    if (info) info.textContent = `Стр. ${clientsPage + 1} из ${total} • всего ${filteredClients.length}`;
}

function clientsPrevPage() { if (clientsPage > 0) { clientsPage--; renderClientsPage(); } }
function clientsNextPage() {
    if ((clientsPage + 1) * CLIENTS_PER_PAGE < filteredClients.length) { clientsPage++; renderClientsPage(); }
}

function renderClients(clients) {
    const tbody = document.getElementById('clients-table-body');
    tbody.innerHTML = '';
    clients.forEach(c => {
        const rankColor = c.rank === 'Новичок' ? 'badge-blue' : c.rank === 'Постоянный' ? 'badge-green' : 'badge-purple';
        tbody.innerHTML += `<tr>
            <td>${c.id}</td><td>${c.telegram_id}</td><td><strong>${c.name}</strong></td>
            <td><span class="badge ${rankColor}">${c.rank}</span></td>
            <td style="color:#a78bfa;font-weight:700">${c.bonus_points}</td>
            <td>${c.total_hours_played}ч</td>
            <td>${c.referrals_count || 0}</td>
            <td><button class="btn-confirm-booking" onclick="adjustBonus(${c.telegram_id},100)">+100</button><button class="btn-cancel-booking" onclick="adjustBonus(${c.telegram_id},-100)">−100</button></td>
        </tr>`;
    });
}

async function adjustBonus(telegramId, delta) {
    if (!confirm(`${delta > 0 ? 'Начислить' : 'Списать'} ${Math.abs(delta)} бонусов?`)) return;
    try {
        const res = await fetch(`/api/clients/${telegramId}/bonus/`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ delta })
        });
        if (res.ok) { showToast('✅ Бонусы обновлены!'); loadClients(); }
        else if (res.status === 403) showToast('❌ Только для администратора', 'error');
        else showToast('❌ Ошибка', 'error');
    } catch (e) { showToast('❌ Ошибка', 'error'); }
}

function downloadCSV(filename, rows) {
    const csv = rows.map(r => r.map(v => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob(["\ufeff" + csv], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
}

function exportClientsCSV() {
    downloadCSV('clients.csv', [['id', 'telegram_id', 'name', 'rank', 'bonus', 'hours', 'referrals'],
        ...filteredClients.map(c => [c.id, c.telegram_id, c.name, c.rank, c.bonus_points, c.total_hours_played, c.referrals_count || 0])]);
    showToast('✅ CSV выгружен!');
}

function exportBookingsCSV() {
    downloadCSV('bookings.csv', [['id', 'client', 'place', 'start', 'end', 'status'],
        ...bookingsCache.map(b => [b.id, b.client_name, b.place_name, b.start_time, b.end_time, b.status])]);
    showToast('✅ CSV выгружен!');
}

function exportSessionsCSV() {
    downloadCSV('sessions.csv', [['id', 'place', 'client', 'start', 'end', 'cost'],
        ...recentSessionsCache.map(s => [s.id, s.place_name, s.client_name, s.start_time, s.end_time, s.cost])]);
    showToast('✅ CSV выгружен!');
}

document.getElementById('client-search').addEventListener('input', e => {
    const q = e.target.value.toLowerCase();
    filteredClients = clientsData.filter(c => c.name.toLowerCase().includes(q) || String(c.telegram_id).includes(q));
    clientsPage = 0;
    renderClientsPage();
});

// ============ BOOKINGS ============
async function loadBookingStats() {
    try {
        const res = await fetch('/api/analytics/bookings/');
        const d = await res.json();
        document.getElementById('bookings-stats').innerHTML = `
            <div class="glass-card stat-mini"><div class="stat-mini-icon bg-blue">📅</div><div><div class="stat-mini-val">${d.total_bookings}</div><div class="stat-mini-label">Всего броней</div></div></div>
            <div class="glass-card stat-mini"><div class="stat-mini-icon bg-amber">⏳</div><div><div class="stat-mini-val">${d.status_breakdown.pending}</div><div class="stat-mini-label">Ожидающие</div></div></div>
            <div class="glass-card stat-mini"><div class="stat-mini-icon bg-green">✅</div><div><div class="stat-mini-val">${d.status_breakdown.confirmed}</div><div class="stat-mini-label">Подтвержденные</div></div></div>
            <div class="glass-card stat-mini"><div class="stat-mini-icon bg-purple">📊</div><div><div class="stat-mini-val">${d.status_breakdown.completed}</div><div class="stat-mini-label">Завершенные</div></div></div>
        `;
    } catch (e) { console.error(e); }
}

async function loadAllBookings() {
    try {
        const filter = document.getElementById('booking-filter').value;
        const url = filter ? `/api/all_bookings/?status=${filter}` : '/api/all_bookings/';
        const res = await fetch(url);
        const bookings = await res.json();
        bookingsCache = bookings;
        const tbody = document.getElementById('bookings-table-body');
        tbody.innerHTML = '';
        const statusMap = { pending: ['Ожидает', 'badge-amber'], confirmed: ['Подтверждено', 'badge-green'], canceled: ['Отменено', 'badge-red'], completed: ['Завершено', 'badge-gray'] };
        bookings.forEach(b => {
            const [text, cls] = statusMap[b.status] || ['—', 'badge-gray'];
            let actions = '';
            if (b.status === 'pending') actions = `<button class="btn-confirm-booking" onclick="confirmBooking(${b.id})">✓</button><button class="btn-cancel-booking" onclick="cancelBooking(${b.id})">✕</button>`;
            else if (b.status === 'confirmed') actions = `<button class="btn-cancel-booking" onclick="cancelBooking(${b.id})">Отменить</button>`;
            tbody.innerHTML += `<tr><td>${b.id}</td><td>${b.client_name}</td><td>${b.place_name}</td><td>${formatDateTime(b.start_time)}</td><td>${formatDateTime(b.end_time)}</td><td><span class="badge ${cls}">${text}</span></td><td>${actions}</td></tr>`;
        });
    } catch (e) { console.error(e); }
}

async function confirmBooking(id) {
    try {
        await fetch(`/api/confirm_booking/${id}/`, { method: 'POST', headers: { 'X-CSRFToken': getCookie('csrftoken') } });
        showToast('✅ Бронь подтверждена!');
        loadAllBookings(); loadBookingStats();
    } catch (e) { showToast('❌ Ошибка', 'error'); }
}

async function cancelBooking(id) {
    if (!confirm('Отменить бронь?')) return;
    try {
        await fetch(`/api/cancel_booking/${id}/`, { method: 'PATCH', headers: { 'X-CSRFToken': getCookie('csrftoken') } });
        showToast('✅ Бронь отменена!');
        loadAllBookings(); loadBookingStats();
    } catch (e) { showToast('❌ Ошибка', 'error'); }
}

// ============ MANAGEMENT ============
async function loadManagement() {
    try {
        const [tRes, pRes] = await Promise.all([fetch('/api/tariffs/'), fetch('/api/promotions/')]);
        renderTariffsMgmt(await tRes.json());
        renderPromosMgmt(await pRes.json());
    } catch (e) { console.error(e); }
}

function renderTariffsMgmt(tariffs) {
    const c = document.getElementById('manage-tariffs-list');
    c.innerHTML = '';
    tariffs.forEach(t => {
        c.innerHTML += `<div class="mgmt-item"><div class="mgmt-item-info"><h5>${t.name}</h5><div class="price">${t.hourly_rate} сом/ч</div>${t.description ? `<div class="desc">${t.description}</div>` : ''}</div><div class="mgmt-actions"><button class="btn-edit" onclick='openTariffModal(${JSON.stringify(t)})'>✏️</button><button class="btn-delete" onclick="deleteTariff(${t.id})">🗑</button></div></div>`;
    });
}

function renderPromosMgmt(promos) {
    const c = document.getElementById('manage-promotions-list');
    c.innerHTML = '';
    promos.forEach(p => {
        const badge = p.is_active ? '<span class="badge badge-green">Активна</span>' : '<span class="badge badge-gray">Неактивна</span>';
        c.innerHTML += `<div class="mgmt-item"><div class="mgmt-item-info"><h5>${p.name}</h5><div class="price" style="color:#a78bfa">-${p.discount_percentage}%</div>${p.description ? `<div class="desc">${p.description}</div>` : ''}<div style="margin-top:6px">${badge}</div></div><div class="mgmt-actions"><button class="btn-edit" onclick='openPromotionModal(${JSON.stringify(p)})'>✏️</button><button class="btn-delete" onclick="deletePromotion(${p.id})">🗑</button></div></div>`;
    });
}

function openTariffModal(t = null) {
    document.getElementById('tariffModal').classList.remove('hidden');
    if (t) {
        document.getElementById('tariffModalTitle').textContent = 'Редактировать тариф';
        document.getElementById('tariffId').value = t.id;
        document.getElementById('tariffName').value = t.name;
        document.getElementById('tariffRate').value = t.hourly_rate;
        document.getElementById('tariffDesc').value = t.description || '';
        document.getElementById('tariffActive').checked = t.is_active;
    } else {
        document.getElementById('tariffModalTitle').textContent = 'Добавить тариф';
        document.getElementById('tariffId').value = '';
        document.getElementById('tariffName').value = '';
        document.getElementById('tariffRate').value = '';
        document.getElementById('tariffDesc').value = '';
        document.getElementById('tariffActive').checked = true;
    }
}

async function submitTariff() {
    const id = document.getElementById('tariffId').value;
    const data = { name: document.getElementById('tariffName').value, hourly_rate: document.getElementById('tariffRate').value, description: document.getElementById('tariffDesc').value, is_active: document.getElementById('tariffActive').checked };
    const url = id ? `/api/tariffs/${id}/` : '/api/tariffs/manage/';
    try {
        const res = await fetch(url, { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') }, body: JSON.stringify(data) });
        if (res.ok) { closeModal('tariffModal'); loadManagement(); if (currentTab === 'operational') fetchTariffs(); showToast('✅ Тариф сохранен!'); }
        else showToast('❌ Ошибка', 'error');
    } catch (e) { showToast('❌ Ошибка', 'error'); }
}

async function deleteTariff(id) {
    if (!confirm('Удалить тариф?')) return;
    try {
        await fetch(`/api/tariffs/${id}/`, { method: 'DELETE', headers: { 'X-CSRFToken': getCookie('csrftoken') } });
        loadManagement(); showToast('✅ Тариф удален!');
    } catch (e) { showToast('❌ Ошибка', 'error'); }
}

function openPromotionModal(p = null) {
    document.getElementById('promotionModal').classList.remove('hidden');
    if (p) {
        document.getElementById('promotionModalTitle').textContent = 'Редактировать акцию';
        document.getElementById('promotionId').value = p.id;
        document.getElementById('promotionName').value = p.name;
        document.getElementById('promotionDiscount').value = p.discount_percentage;
        document.getElementById('promotionDesc').value = p.description || '';
        document.getElementById('promotionActive').checked = p.is_active;
    } else {
        document.getElementById('promotionModalTitle').textContent = 'Добавить акцию';
        document.getElementById('promotionId').value = '';
        document.getElementById('promotionName').value = '';
        document.getElementById('promotionDiscount').value = '';
        document.getElementById('promotionDesc').value = '';
        document.getElementById('promotionActive').checked = true;
    }
}

async function submitPromotion() {
    const id = document.getElementById('promotionId').value;
    const data = { name: document.getElementById('promotionName').value, discount_percentage: document.getElementById('promotionDiscount').value, description: document.getElementById('promotionDesc').value, is_active: document.getElementById('promotionActive').checked };
    const url = id ? `/api/promotions/${id}/` : '/api/promotions/';
    try {
        const res = await fetch(url, { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') }, body: JSON.stringify(data) });
        if (res.ok) { closeModal('promotionModal'); loadManagement(); showToast('✅ Акция сохранена!'); }
        else { const err = await res.json(); showToast('❌ Ошибка: ' + JSON.stringify(err), 'error'); }
    } catch (e) { showToast('❌ Ошибка', 'error'); }
}

async function deletePromotion(id) {
    if (!confirm('Удалить акцию?')) return;
    try {
        await fetch(`/api/promotions/${id}/`, { method: 'DELETE', headers: { 'X-CSRFToken': getCookie('csrftoken') } });
        loadManagement(); showToast('✅ Акция удалена!');
    } catch (e) { showToast('❌ Ошибка', 'error'); }
}

// ============ CLOCK ============
function updateClock() {
    const now = new Date();
    document.getElementById('clock').textContent = now.toLocaleTimeString('ru-RU');
    document.getElementById('clock-date').textContent = now.toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric', month: 'long' });
}

// ============ QR SCANNER ============
let html5QrCode = null;
let scannedClientData = null;
let scannerBusy = false;

function startQRScanner() {
    scannerBusy = false;
    const config = { fps: 10, qrbox: { width: 250, height: 250 } };
    html5QrCode = new Html5Qrcode('qr-reader');
    html5QrCode.start(
        { facingMode: 'environment' },
        config,
        onQRCodeScanned,
        () => {}
    ).then(() => {
        document.getElementById('btn-start-scan').style.display = 'none';
        document.getElementById('btn-stop-scan').style.display = 'block';
    }).catch(err => {
        console.error('Camera error:', err);
        showToast('❌ Не удалось открыть камеру', 'error');
    });
}

function stopQRScanner() {
    if (html5QrCode) {
        try {
            html5QrCode.stop().then(() => {
                try { html5QrCode.clear(); } catch(e) {}
                document.getElementById('btn-start-scan').style.display = 'block';
                document.getElementById('btn-stop-scan').style.display = 'none';
            }).catch(() => {});
        } catch(e) {}
    }
}

async function onQRCodeScanned(decodedText) {
    if (scannerBusy) return; // Блокируем повторные вызовы
    scannerBusy = true;
    stopQRScanner();
    try {
        const data = JSON.parse(decodedText);
        if (data.type === 'cyberlounge_client' && data.telegram_id) {
            await lookupClient(data.telegram_id);
        } else {
            showToast('❌ Неизвестный QR-код', 'error');
            scannerBusy = false;
        }
    } catch (e) {
        const numId = parseInt(decodedText);
        if (numId) await lookupClient(numId);
        else { showToast('❌ QR-код не от CyberLounge', 'error'); scannerBusy = false; }
    }
}

async function lookupClient(telegramId) {
    try {
        const res = await fetch(`/api/client_info/${telegramId}/`);
        if (!res.ok) {
            showToast('❌ Клиент не найден в базе', 'error');
            return;
        }
        const client = await res.json();
        scannedClientData = { ...client, telegram_id: telegramId };

        document.getElementById('sc-name').textContent = client.name;
        document.getElementById('sc-rank').textContent = client.rank;
        document.getElementById('sc-bonus').textContent = client.bonus_points;
        document.getElementById('sc-hours').textContent = client.total_hours_played + 'ч';

        await loadScannerPlaces();

        document.getElementById('scan-step-1').style.display = 'none';
        document.getElementById('scan-step-2').style.display = 'block';

        showToast('✅ Клиент: ' + client.name + ' | ' + client.rank);
    } catch (e) {
        console.error('Lookup error:', e);
        showToast('❌ Ошибка соединения с сервером', 'error');
    }
}

async function loadScannerPlaces() {
    try {
        const res = await fetch('/api/place_status/');
        const places = await res.json();
        const free = places.filter(p => p.status === 'free');
        const grid = document.getElementById('scanner-places-grid');

        if (free.length === 0) {
            grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text-muted);padding:24px;">😔 Нет свободных комнат</div>';
            return;
        }

        grid.innerHTML = '';
        free.forEach(p => {
            const typeIcon = p.place_type === 'VIP' ? '👑' : p.place_type === 'Bootcamp' ? '🎮' : '🎮';
            const price = p.tariff_info ? p.tariff_info.hourly_rate + ' сом/ч' : '';
            const card = document.createElement('div');
            card.className = 'scanner-place-btn';
            card.setAttribute('data-place-id', p.id);
            card.innerHTML = `
                <div style="font-size:28px;margin-bottom:6px;">${typeIcon}</div>
                <div style="font-weight:700;font-size:15px;">${p.name}</div>
                <div style="font-size:11px;color:var(--text-dim);margin-top:2px;">${p.place_type || 'Standard'}</div>
                <div style="font-size:13px;color:#818cf8;font-weight:700;margin-top:6px;">${price}</div>
            `;
            card.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                selectScanPlace(p.id, this);
            });
            grid.appendChild(card);
        });
    } catch (e) { console.error('Scanner places error:', e); }
}

function selectScanPlace(placeId, el) {
    document.querySelectorAll('.scanner-place-btn').forEach(b => b.classList.remove('selected'));
    el.classList.add('selected');
    document.getElementById('scanner-place-id').value = placeId;
}

function selectScanDuration(minutes, btn) {
    document.getElementById('scanner-duration').value = minutes;
    btn.closest('.duration-grid').querySelectorAll('.dur-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
}

function lookupManualId() {
    const id = document.getElementById('manual-telegram-id').value;
    if (!id) { showToast('Введите Telegram ID', 'error'); return; }
    lookupClient(parseInt(id));
}

function resetScanner() {
    scannedClientData = null;
    scannerBusy = false;
    const step1 = document.getElementById('scan-step-1');
    const step2 = document.getElementById('scan-step-2');
    if (step1) step1.style.display = 'block';
    if (step2) step2.style.display = 'none';
    const placeId = document.getElementById('scanner-place-id');
    if (placeId) placeId.value = '';
    const dur = document.getElementById('scanner-duration');
    if (dur) dur.value = '0';
    const manualId = document.getElementById('manual-telegram-id');
    if (manualId) manualId.value = '';
}

async function submitScanSession() {
    if (!scannedClientData) { showToast('Сначала отсканируйте клиента', 'error'); return; }

    const placeId = document.getElementById('scanner-place-id').value;
    if (!placeId) { showToast('⚠️ Выберите место!', 'error'); return; }

    const duration = document.getElementById('scanner-duration').value;

    try {
        const payload = {
            place_id: placeId,
            is_guest: false,
            telegram_id: scannedClientData.telegram_id,
            client_name: scannedClientData.name,
            duration: duration > 0 ? duration : null
        };

        const res = await fetch('/api/start_session/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            showToast('🎮 Сессия для ' + scannedClientData.name + ' начата!');
            resetScanner();
            fetchPlaces();
            fetchQuickStats();
        } else {
            const err = await res.json();
            showToast('❌ ' + (err.error || 'Ошибка'), 'error');
        }
    } catch (e) {
        showToast('❌ Ошибка соединения', 'error');
    }
}

// ============ INIT ============
document.addEventListener('DOMContentLoaded', () => {
    fetchPlaces();
    fetchTariffs();
    fetchQuickStats();
    updateClock();
    setInterval(updateClock, 1000);
    setInterval(() => { if (currentTab === 'operational') { fetchPlaces(); fetchQuickStats(); } }, 30000);
});
