document.addEventListener("DOMContentLoaded", () => {
    const hamburgerBtn = document.getElementById('hamburgerBtn');
    if (hamburgerBtn) {
        const sidebar = document.querySelector('.sidebar');
        
        if (localStorage.getItem('sidebarCollapsed') === 'true') {
            sidebar.classList.add('collapsed');
        }

        hamburgerBtn.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
        });
    }

    const tabs = document.querySelectorAll('.nav-item');
    const panes = document.querySelectorAll('.tab-pane');
    
    // Tab switching
    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            const target = tab.getAttribute('data-tab');
            
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            panes.forEach(pane => {
                pane.classList.remove('active');
                if(pane.id === target) {
                    pane.classList.add('active');
                    window.location.hash = '#' + target;
                    if(target === 'history') loadHistory();
                }
            });
        });
    });

    // Hash Load handling
    const initialHash = window.location.hash.substring(1);
    if(initialHash) {
        document.querySelector(`.nav-item[data-tab="${initialHash}"]`)?.click();
    }

    window.currentDateFormat = 'US';
    window.currentTimeZone = 'UTC';
    
    let currentConfig = { accounts: [], global: {} };

    // Populate Timezone select
    const tzSelect = document.getElementById('timezone');
    if (tzSelect && Intl.supportedValuesOf) {
        tzSelect.innerHTML = '';
        Intl.supportedValuesOf('timeZone').forEach(tz => {
            const option = document.createElement('option');
            option.value = tz;
            option.textContent = tz.replace(/_/g, ' ');
            tzSelect.appendChild(option);
        });
        tzSelect.value = 'UTC';
    } else if (tzSelect) {
        tzSelect.innerHTML = '<option value="UTC">UTC</option>';
    }

    const autoDetectTzBtn = document.getElementById('autoDetectTzBtn');
    if (autoDetectTzBtn) {
        autoDetectTzBtn.addEventListener('click', () => {
            try {
                const userTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
                if (userTz) {
                    if (!tzSelect.querySelector(`option[value="${userTz}"]`)) {
                        const option = document.createElement('option');
                        option.value = userTz;
                        option.textContent = userTz.replace(/_/g, ' ');
                        tzSelect.appendChild(option);
                    }
                    tzSelect.value = userTz;
                }
            } catch (e) {
                console.error('Time zone detection failed', e);
            }
        });
    }

    function renderAccounts() {
        const accountsList = document.getElementById('accountsList');
        if (!accountsList) return;
        accountsList.innerHTML = '';
        currentConfig.accounts.forEach(acc => {
            const card = document.createElement('div');
            card.className = 'account-card';
            card.id = `acc-card-${acc.id}`;
            card.innerHTML = `
                <div class="account-header">
                    <div class="account-title">${acc.name}</div>
                    <div class="account-points" id="acc-pts-${acc.id}">0 P</div>
                </div>
                <div class="account-status">
                    <div class="status-dot offline" id="acc-dot-${acc.id}"></div>
                    <span id="acc-status-${acc.id}">Offline</span>
                </div>
                <div class="account-actions">
                    <button class="btn primary" id="acc-start-${acc.id}" style="flex: 1; padding: 0.5rem;">Start</button>
                    <button class="btn danger" id="acc-stop-${acc.id}" style="flex: 1; display: none; padding: 0.5rem;">Stop</button>
                    <button class="btn" id="acc-edit-${acc.id}" style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; padding: 0.5rem;">Edit</button>
                    <button class="btn" id="acc-del-${acc.id}" style="background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); color: #ef4444; padding: 0.5rem; flex: 0 0 40px;" title="Delete">✕</button>
                </div>
            `;
            accountsList.appendChild(card);

            document.getElementById(`acc-start-${acc.id}`).addEventListener('click', () => {
                fetch('/api/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ account_id: acc.id }) })
                    .then(r => r.json()).then(res => { if (res.status !== 'success') alert(res.message); checkStatus(); });
            });
            document.getElementById(`acc-stop-${acc.id}`).addEventListener('click', () => {
                fetch('/api/stop', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ account_id: acc.id }) })
                    .then(r => r.json()).then(res => { if (res.status !== 'success') alert(res.message); checkStatus(); });
            });
            document.getElementById(`acc-edit-${acc.id}`).addEventListener('click', () => openModal(acc));
            document.getElementById(`acc-del-${acc.id}`).addEventListener('click', () => {
                if (confirm(`Are you sure you want to delete ${acc.name}?`)) {
                    currentConfig.accounts = currentConfig.accounts.filter(a => a.id !== acc.id);
                    saveCurrentConfig();
                }
            });
        });
        checkStatus();
    }

    function openModal(acc = null) {
        document.getElementById('accountModal').classList.remove('hidden');
        document.getElementById('accountForm').reset();
        if (acc) {
            document.getElementById('modalTitle').textContent = 'Edit Account';
            document.getElementById('account_id').value = acc.id;
            document.getElementById('account_name').value = acc.name;
            document.getElementById('cookie').value = acc.cookie;
            document.getElementById('gift_type').value = acc.gift_type || 'All';
            document.getElementById('min_points').value = acc.min_points || 10;
            document.getElementById('sleep_low_points').value = acc.sleep_low_points || 900;
            document.getElementById('sleep_list_ended').value = acc.sleep_list_ended || 120;
            document.getElementById('pinned').checked = acc.pinned || false;
            document.getElementById('safety_check').checked = acc.safety_check !== undefined ? acc.safety_check : true;
        } else {
            document.getElementById('modalTitle').textContent = 'Add Account';
            document.getElementById('account_id').value = '';
            document.getElementById('safety_check').checked = true;
        }
    }

    const accountModal = document.getElementById('accountModal');
    if(accountModal) {
        document.getElementById('closeModalBtn').addEventListener('click', () => accountModal.classList.add('hidden'));
        document.getElementById('addAccountBtn').addEventListener('click', () => openModal(null));
        
        document.getElementById('accountForm').addEventListener('submit', (e) => {
            e.preventDefault();
            const id = document.getElementById('account_id').value || Date.now().toString();
            const accData = {
                id: id,
                name: document.getElementById('account_name').value,
                cookie: document.getElementById('cookie').value,
                gift_type: document.getElementById('gift_type').value,
                min_points: parseInt(document.getElementById('min_points').value) || 10,
                sleep_low_points: parseInt(document.getElementById('sleep_low_points').value) || 900,
                sleep_list_ended: parseInt(document.getElementById('sleep_list_ended').value) || 120,
                pinned: document.getElementById('pinned').checked,
                safety_check: document.getElementById('safety_check').checked
            };
            
            const existingIdx = currentConfig.accounts.findIndex(a => a.id === id);
            if (existingIdx >= 0) {
                currentConfig.accounts[existingIdx] = accData;
            } else {
                currentConfig.accounts.push(accData);
            }
            saveCurrentConfig();
            accountModal.classList.add('hidden');
        });
    }

    function loadConfig() {
        fetch('/api/config')
            .then(r => r.json())
            .then(data => {
                currentConfig = data;
                if (!currentConfig.global) currentConfig.global = {};
                if (!currentConfig.accounts) currentConfig.accounts = [];
                
                const g = currentConfig.global;
                if(g.date_format) {
                    const df = document.getElementById('date_format');
                    if(df) df.value = g.date_format;
                    window.currentDateFormat = g.date_format;
                }
                if(g.timezone) {
                    if (tzSelect && !tzSelect.querySelector(`option[value="${g.timezone}"]`)) {
                        const option = document.createElement('option');
                        option.value = g.timezone;
                        option.textContent = g.timezone.replace(/_/g, ' ');
                        tzSelect.appendChild(option);
                    }
                    if (tzSelect) tzSelect.value = g.timezone;
                    window.currentTimeZone = g.timezone;
                }
                if(g.discord_webhook) { const e = document.getElementById('discord_webhook'); if(e) e.value = g.discord_webhook; }
                if(g.telegram_token) { const e = document.getElementById('telegram_token'); if(e) e.value = g.telegram_token; }
                if(g.telegram_chat_id) { const e = document.getElementById('telegram_chat_id'); if(e) e.value = g.telegram_chat_id; }
                if(g.n8n_webhook) { const e = document.getElementById('n8n_webhook'); if(e) e.value = g.n8n_webhook; }
                if(g.auto_start !== undefined) { const e = document.getElementById('auto_start'); if(e) e.checked = g.auto_start; }

                renderAccounts();
            });
    }
    
    loadConfig();

    function saveCurrentConfig(msgElement = null) {
        fetch('/api/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(currentConfig)
        }).then(() => {
            if(msgElement) {
                msgElement.classList.remove('hidden');
                setTimeout(() => msgElement.classList.add('hidden'), 3000);
            }
            renderAccounts();
        });
    }

    const globalConfigForm = document.getElementById('globalConfigForm');
    const notifyConfigForm = document.getElementById('notifyConfigForm');

    function updateGlobalConfigFromUI() {
        currentConfig.global = {
            ...currentConfig.global,
            date_format: document.getElementById('date_format') ? document.getElementById('date_format').value : 'US',
            timezone: document.getElementById('timezone') ? document.getElementById('timezone').value : 'UTC',
            auto_start: document.getElementById('auto_start') ? document.getElementById('auto_start').checked : false,
            discord_webhook: document.getElementById('discord_webhook') ? document.getElementById('discord_webhook').value : '',
            telegram_token: document.getElementById('telegram_token') ? document.getElementById('telegram_token').value : '',
            telegram_chat_id: document.getElementById('telegram_chat_id') ? document.getElementById('telegram_chat_id').value : '',
            n8n_webhook: document.getElementById('n8n_webhook') ? document.getElementById('n8n_webhook').value : ''
        };
        window.currentDateFormat = currentConfig.global.date_format;
        window.currentTimeZone = currentConfig.global.timezone;
    }

    if (globalConfigForm) {
        globalConfigForm.addEventListener('submit', (e) => {
            e.preventDefault();
            updateGlobalConfigFromUI();
            saveCurrentConfig(document.getElementById('globalSaveMsg'));
        });
    }

    if (notifyConfigForm) {
        notifyConfigForm.addEventListener('submit', (e) => {
            e.preventDefault();
            updateGlobalConfigFromUI();
            saveCurrentConfig(document.getElementById('notifySaveMsg'));
        });
    }

    const testNotifyBtn = document.getElementById('testNotifyBtn');
    if (testNotifyBtn) {
        testNotifyBtn.addEventListener('click', () => {
            const config = {
                discord_webhook: document.getElementById('discord_webhook').value,
                telegram_token: document.getElementById('telegram_token').value,
                telegram_chat_id: document.getElementById('telegram_chat_id').value,
                n8n_webhook: document.getElementById('n8n_webhook').value
            };
            
            const originalText = testNotifyBtn.textContent;
            testNotifyBtn.textContent = 'Testing...';
            testNotifyBtn.disabled = true;
            
            fetch('/api/test_notification', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            })
            .then(res => res.json())
            .then(data => {
                testNotifyBtn.textContent = originalText;
                testNotifyBtn.disabled = false;
                alert(data.message);
            })
            .catch(err => {
                testNotifyBtn.textContent = originalText;
                testNotifyBtn.disabled = false;
                alert('Error dispatching test notification.');
            });
        });
    }

    function checkStatus() {
        fetch('/api/status')
            .then(r => r.json())
            .then(data => {
                let activeCount = 0;
                currentConfig.accounts.forEach(acc => {
                    const status = data[acc.id] || { running: false, points: 0 };
                    const dot = document.getElementById(`acc-dot-${acc.id}`);
                    const statusText = document.getElementById(`acc-status-${acc.id}`);
                    const pts = document.getElementById(`acc-pts-${acc.id}`);
                    const startBtn = document.getElementById(`acc-start-${acc.id}`);
                    const stopBtn = document.getElementById(`acc-stop-${acc.id}`);

                    if(dot && statusText && pts && startBtn && stopBtn) {
                        pts.textContent = `${status.points} P`;
                        if (status.running) {
                            activeCount++;
                            dot.className = 'status-dot online';
                            statusText.textContent = 'Running';
                            startBtn.style.display = 'none';
                            stopBtn.style.display = 'block';
                        } else {
                            dot.className = 'status-dot offline';
                            statusText.textContent = 'Offline';
                            startBtn.style.display = 'block';
                            stopBtn.style.display = 'none';
                        }
                    }
                });

                const globalDot = document.getElementById('globalStatusDot');
                const globalStatus = document.getElementById('globalStatus');
                if (globalDot && globalStatus) {
                    globalStatus.textContent = `Active Bots: ${activeCount}`;
                    if (activeCount > 0) {
                        globalDot.className = 'status-dot online';
                    } else {
                        globalDot.className = 'status-dot offline';
                    }
                }
            });
    }

    setInterval(checkStatus, 3000);

    // Logging SSE
    const logContainer = document.getElementById('logContainer');
    const evtSource = new EventSource('/api/logs');
    
    const colorMap = {
        'white': '#f8fafc',
        'red': '#ef4444',
        'yellow': '#f59e0b',
        'green': '#10b981',
        'blue': '#3b82f6',
        'magenta': '#d946ef'
    };

    evtSource.onmessage = function(event) {
        const logData = JSON.parse(event.data);
        const div = document.createElement('div');
        div.className = 'log-entry';
        
        const time = document.createElement('span');
        time.className = 'log-time';
        time.textContent = `[${logData.timestamp}]`;
        
        const msg = document.createElement('span');
        msg.style.color = colorMap[logData.color.toLowerCase()] || colorMap['white'];
        msg.textContent = logData.message;
        
        div.appendChild(time);
        div.appendChild(msg);
        logContainer.appendChild(div);
        
        logContainer.scrollTop = logContainer.scrollHeight;
    };

    function formatDateString(dateStr) {
        if(!dateStr) return '';
        try {
            const d = new Date(dateStr);
            if(isNaN(d)) return dateStr;
            const fmt = window.currentDateFormat;
            const tzOptions = window.currentTimeZone ? { timeZone: window.currentTimeZone } : {};

            if(fmt === 'US') {
                return d.toLocaleString('en-US', { ...tzOptions, month: '2-digit', day: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true});
            } else if(fmt === 'EU') {
                return d.toLocaleString('en-GB', { ...tzOptions, day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false});
            } else {
                return d.toLocaleString('sv-SE', { ...tzOptions, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }).replace('T', ' ');
            }
        } catch(e) {
            return dateStr;
        }
    }

    function loadHistory() {
        fetch('/api/history')
            .then(r => r.json())
            .then(data => {
                const tbody = document.getElementById('historyBody');
                tbody.innerHTML = '';
                data.slice().reverse().forEach(entry => {
                    const tr = document.createElement('tr');
                    const linkMarkup = entry.link ? `<a href="${entry.link}" target="_blank" style="color: #60a5fa; text-decoration: none;">${entry.name}</a>` : entry.name;
                    const imageMarkup = entry.image ? `<img src="${entry.image}" style="width: 120px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-right: 15px; float: left;">` : '';
                    tr.innerHTML = `
                        <td>${formatDateString(entry.date)}</td>
                        <td>${entry.account_name || 'Main'}</td>
                        <td style="font-weight: 600; vertical-align: middle;">${imageMarkup} <div style="display:flex; flex-direction:column; justify-content:center; min-height: 45px;">${linkMarkup}</div></td>
                        <td style="vertical-align: middle;"><span class="cost-badge">${entry.cost} P</span></td>
                    `;
                    tbody.appendChild(tr);
                });
            });
    }

    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    if (clearHistoryBtn) {
        let clearTimer = null;
        let countdown = 3;
        clearHistoryBtn.addEventListener('click', () => {
            if (countdown > 0) {
                if (clearTimer) return;
                clearHistoryBtn.textContent = `Confirm Purge (${countdown})`;
                clearTimer = setInterval(() => {
                    countdown--;
                    if (countdown > 0) {
                        clearHistoryBtn.textContent = `Confirm Purge (${countdown})`;
                    } else {
                        clearInterval(clearTimer);
                        clearHistoryBtn.textContent = `Delete Now`;
                        clearHistoryBtn.style.background = '#b91c1c';
                    }
                }, 1000);
            } else {
                clearHistoryBtn.disabled = true;
                clearHistoryBtn.textContent = `Clearing...`;
                fetch('/api/history', { method: 'DELETE' })
                    .then(r => r.json())
                    .then(r => {
                        loadHistory();
                        clearHistoryBtn.disabled = false;
                        clearHistoryBtn.textContent = `Clear History`;
                        clearHistoryBtn.style.background = '#ef4444';
                        countdown = 3;
                        clearTimer = null;
                    })
                    .catch(e => {
                        clearHistoryBtn.disabled = false;
                        clearHistoryBtn.textContent = `Clear History`;
                        clearHistoryBtn.style.background = '#ef4444';
                        countdown = 3;
                        clearTimer = null;
                    });
            }
        });
    }
});
