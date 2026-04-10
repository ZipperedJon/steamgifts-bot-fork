document.addEventListener("DOMContentLoaded", () => {
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
                    if(target === 'history') loadHistory();
                }
            });
        });
    });

    // Form Handling
    const configForm = document.getElementById('configForm');
    const saveMsg = document.getElementById('saveMsg');
    
    // Load config
    fetch('/api/config')
        .then(r => r.json())
        .then(data => {
            if(data.cookie) document.getElementById('cookie').value = data.cookie;
            if(data.gift_type) document.getElementById('gift_type').value = data.gift_type;
            if(data.min_points) document.getElementById('min_points').value = data.min_points;
            if(data.sleep_low_points) document.getElementById('sleep_low_points').value = data.sleep_low_points;
            if(data.sleep_list_ended) document.getElementById('sleep_list_ended').value = data.sleep_list_ended;
            if(data.pinned) document.getElementById('pinned').checked = data.pinned;
        });

    configForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const config = {
            cookie: document.getElementById('cookie').value,
            gift_type: document.getElementById('gift_type').value,
            min_points: parseInt(document.getElementById('min_points').value) || 10,
            sleep_low_points: parseInt(document.getElementById('sleep_low_points').value) || 900,
            sleep_list_ended: parseInt(document.getElementById('sleep_list_ended').value) || 120,
            pinned: document.getElementById('pinned').checked
        };
        fetch('/api/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(config)
        }).then(() => {
            saveMsg.classList.remove('hidden');
            setTimeout(() => saveMsg.classList.add('hidden'), 3000);
        });
    });

    // Bot Control
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const botStatus = document.getElementById('botStatus');

    function updateStatus(isRunning) {
        if(isRunning) {
            botStatus.textContent = 'Running';
            botStatus.className = 'status-badge online';
            startBtn.style.display = 'none';
            stopBtn.style.display = 'block';
        } else {
            botStatus.textContent = 'Stopped';
            botStatus.className = 'status-badge offline';
            startBtn.style.display = 'block';
            stopBtn.style.display = 'none';
        }
    }

    function checkStatus() {
        fetch('/api/status')
            .then(r => r.json())
            .then(data => updateStatus(data.running));
    }

    setInterval(checkStatus, 3000);
    checkStatus();

    startBtn.addEventListener('click', () => {
        fetch('/api/start', {method:'POST'}).then(r => r.json()).then(data => {
            if(data.status === 'success') {
                updateStatus(true);
                document.querySelector('[data-tab="logs"]').click();
            } else {
                alert(data.message);
            }
        });
    });

    stopBtn.addEventListener('click', () => {
        fetch('/api/stop', {method:'POST'}).then(() => {
            updateStatus(false);
        });
    });

    // Logging SSE
    const logContainer = document.getElementById('logContainer');
    const evtSource = new EventSource('/api/logs');
    
    const colorMap = {
        'white': '#f8fafc', // var(--text-color)
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
        
        // Auto scroll setup
        logContainer.scrollTop = logContainer.scrollHeight;
    };

    // History lazy load
    function loadHistory() {
        fetch('/api/history')
            .then(r => r.json())
            .then(data => {
                const tbody = document.getElementById('historyBody');
                tbody.innerHTML = '';
                // Reverse to show newest first
                data.slice().reverse().forEach(entry => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${entry.date}</td>
                        <td style="font-weight: 600">${entry.name}</td>
                        <td><span class="cost-badge">${entry.cost} P</span></td>
                    `;
                    tbody.appendChild(tr);
                });
            });
    }
});
