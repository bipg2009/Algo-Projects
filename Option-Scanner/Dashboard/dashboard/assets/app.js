document.addEventListener("DOMContentLoaded", () => {
    const wsStatusDot = document.getElementById("ws-status-dot");
    const wsStatusText = document.getElementById("ws-status-text");
    const lastUpdateTime = document.getElementById("last-update-time");
    
    const scannerState = document.getElementById("scanner-state");
    const marketTrend = document.getElementById("market-trend");
    const marketAtr = document.getElementById("market-atr");
    const muteTimer = document.getElementById("mute-timer");
    const tickerSpot = document.getElementById("ticker-spot");
    const tickerBody = document.getElementById("ticker-body");
    const activeTradesCount = document.getElementById("active-trades-count");
    
    const activeTradesBody = document.getElementById("active-trades-body");
    const signalList = document.getElementById("signal-list");
    const systemLogs = document.getElementById("system-logs");

    let ws;
    let reconnectInterval = 2000;
    let hostIdx = 0;
    const hostCandidates = Array.from(new Set([
        window.location.host,
        "127.0.0.1:5173",
        "localhost:5173",
    ].filter(Boolean)));

    function connect() {
        const proto = window.location.protocol === "https:" ? "wss" : "ws";
        const host = hostCandidates[hostIdx % hostCandidates.length];
        const wsUrl = `${proto}://${host}/ws`;
        addLog("System", `Connecting WebSocket: ${wsUrl}`, "info");
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            hostIdx = 0; // reset after successful connect
            wsStatusDot.className = "dot connected";
            wsStatusText.textContent = "Connected";
            addLog("System", "WebSocket connected successfully.", "success");
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleEvent(data);
                
                const now = new Date();
                lastUpdateTime.textContent = `Last update: ${now.toLocaleTimeString()}`;
            } catch (e) {
                console.error("Error parsing WS message", e);
            }
        };

        ws.onclose = () => {
            wsStatusDot.className = "dot disconnected";
            wsStatusText.textContent = "Disconnected";
            addLog("System", "WebSocket disconnected. Reconnecting...", "error");
            hostIdx += 1; // rotate host candidates on each failure
            setTimeout(connect, reconnectInterval);
        };

        ws.onerror = (err) => {
            console.error("WebSocket error", err);
            addLog("System", "WebSocket error (see Console). Rotating host...", "error");
            ws.close();
        };
    }

    function handleEvent(data) {
        if (!data.type) return;

        switch (data.type) {
            case "SCANNER_STATE":
                updateScannerState(data.payload);
                break;
            case "MARKET_TREND":
                updateMarketTrend(data.payload);
                break;
            case "MARKET_ATR":
                updateMarketAtr(data.payload);
                break;
            case "CHAIN_TICKER":
                updateChainTicker(data.payload);
                break;
            case "ACTIVE_TRADES":
                updateActiveTrades(data.payload);
                break;
            case "NEW_SIGNAL":
                addNewSignal(data.payload);
                break;
            case "LOG":
                addLog(data.payload.source, data.payload.message, data.payload.level);
                break;
        }
    }

    function updateScannerState(payload) {
        // payload: { status: 'SCANNING' | 'MUTED' | 'INACTIVE', mute_seconds_left: number }
        scannerState.textContent = payload.status;
        scannerState.className = `state-text ${payload.status.toLowerCase()}`;
        
        if (payload.status === "MUTED" && payload.mute_seconds_left) {
            const mins = Math.floor(payload.mute_seconds_left / 60).toString().padStart(2, '0');
            const secs = (payload.mute_seconds_left % 60).toString().padStart(2, '0');
            muteTimer.textContent = `${mins}:${secs}`;
        } else {
            muteTimer.textContent = "00:00";
        }
    }

    function updateMarketTrend(payload) {
        // payload: 'UP' | 'DOWN' | 'SIDEWAYS'
        marketTrend.textContent = payload;
        marketTrend.className = `state-text ${payload.toLowerCase()}`;
    }

    function updateMarketAtr(payload) {
        marketAtr.textContent = payload;
        marketAtr.className = "state-text active";
    }

    let currentSortColumn = 'oi'; // 'oi' or 'vol'
    let lastTickerPayload = null;

    const sortVolBtn = document.getElementById('sort-vol');
    const sortOiBtn = document.getElementById('sort-oi');

    if (sortVolBtn && sortOiBtn) {
        sortVolBtn.addEventListener('click', () => {
            currentSortColumn = 'vol';
            sortVolBtn.style.color = '#fff';
            sortOiBtn.style.color = '#888';
            if (lastTickerPayload) updateChainTicker(lastTickerPayload);
        });

        sortOiBtn.addEventListener('click', () => {
            currentSortColumn = 'oi';
            sortOiBtn.style.color = '#fff';
            sortVolBtn.style.color = '#888';
            if (lastTickerPayload) updateChainTicker(lastTickerPayload);
        });
    }

    function updateChainTicker(payload) {
        lastTickerPayload = payload;
        tickerSpot.textContent = `Spot: ${payload.spot.toFixed(2)}`;
        
        if (!payload.options || payload.options.length === 0) {
            tickerBody.innerHTML = `<tr class="empty-row"><td colspan="5">No strikes found near ATM.</td></tr>`;
            return;
        }

        let sortedOptions = [...payload.options];
        if (currentSortColumn === 'vol') {
            sortedOptions.sort((a, b) => (b.volume || 0) - (a.volume || 0));
        } else {
            // Default: Sort by OI Change percentage magnitude descending
            sortedOptions.sort((a, b) => Math.abs(b.oi_change_pct || 0) - Math.abs(a.oi_change_pct || 0));
        }

        tickerBody.innerHTML = "";
        sortedOptions.forEach(opt => {
            const tr = document.createElement("tr");
            
            // Format OI Change string: "Absolute (Percentage%)"
            const oiChangeSign = opt.oi_change > 0 ? "+" : "";
            const oiChangeClass = opt.oi_change > 0 ? "profit" : (opt.oi_change < 0 ? "loss" : "");
            const formattedOiChange = Number(opt.oi_change || 0).toLocaleString('en-IN');
            const oiText = `${oiChangeSign}${formattedOiChange} (${oiChangeSign}${Number(opt.oi_change_pct || 0).toFixed(1)}%)`;

            tr.innerHTML = `
                <td><strong>${opt.symbol}</strong></td>
                <td>${opt.ltp.toFixed(2)}</td>
                <td>${opt.volume.toLocaleString()}</td>
                <td class="${oiChangeClass}">${oiText}</td>
                <td><button class="action-btn buy-btn" onclick="testBuy('${opt.symbol}', '${opt.type}', ${opt.ltp})">Buy TEST</button></td>
            `;
            tickerBody.appendChild(tr);
        });
    }

    function updateActiveTrades(trades) {
        // trades: Array of { symbol, type, entry, target, sl, ltp, pnl }
        activeTradesCount.textContent = trades.length;

        if (!trades || trades.length === 0) {
            activeTradesBody.innerHTML = `<tr class="empty-row"><td colspan="8">No active trades currently.</td></tr>`;
            return;
        }

        activeTradesBody.innerHTML = "";
        trades.forEach(t => {
            const tr = document.createElement("tr");
            const pnlClass = t.pnl >= 0 ? "profit" : "loss";
            const pnlSign = t.pnl > 0 ? "+" : "";
            const badgeClass = t.type === 'CE' ? 'badge-ce' : 'badge-pe';
            
            tr.innerHTML = `
                <td><strong>${t.symbol}</strong> <span class="badge ${badgeClass}">${t.type}</span></td>
                <td>${t.type}</td>
                <td>${t.entry}</td>
                <td>${t.target}</td>
                <td>${t.sl}</td>
                <td>${t.ltp}</td>
                <td class="${pnlClass}">${pnlSign}${Math.abs(t.pnl).toFixed(2)}</td>
                <td><button class="action-btn sell-btn" onclick="testSell('${t.symbol}')">Sell TEST</button></td>
            `;
            activeTradesBody.appendChild(tr);
        });
    }

    function addNewSignal(signal) {
        // signal: { symbol, type, time, action }
        const emptyState = signalList.querySelector('.empty-state');
        if (emptyState) emptyState.remove();

        const li = document.createElement("li");
        li.className = `signal-item ${signal.action}`;
        const volFormatted = signal.vol ? Number(signal.vol).toLocaleString('en-IN') : '0';
        const oiFormatted = signal.oi_change ? Number(signal.oi_change).toLocaleString('en-IN') : '0';

        li.innerHTML = `
            <div>
                <span class="signal-symbol">${signal.symbol}</span>
                <span style="margin-left:8px; font-size:0.75rem;">${signal.type}</span>
                <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 4px;">
                    Vol: ${volFormatted} | OI: ${oiFormatted}
                </div>
            </div>
            <div style="text-align:right">
                <div style="font-weight:600">${signal.action}</div>
                <div class="signal-time">${signal.time}</div>
            </div>
        `;
        
        signalList.prepend(li);
        
        // Keep only last 10 signals
        if (signalList.children.length > 10) {
            signalList.removeChild(signalList.lastChild);
        }
    }

    function addLog(source, message, level = "info") {
        const div = document.createElement("div");
        div.className = "log-entry";
        
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour12: false });
        
        div.innerHTML = `
            <span class="log-time">[${timeStr}]</span>
            <span class="log-${level}">[${source}] ${message}</span>
        `;
        
        systemLogs.appendChild(div);
        systemLogs.scrollTop = systemLogs.scrollHeight;
    }

    // Initialize
    connect();
});

// Global functions for manual testing buttons
window.testBuy = function(symbol, type, ltp) {
    fetch('/api/test_buy', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({symbol: symbol, option_type: type, ltp: ltp})
    })
    .then(r => r.json())
    .then(data => console.log(data.message))
    .catch(e => console.error(e));
};

window.testSell = function(symbol) {
    fetch('/api/test_sell', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({symbol: symbol})
    })
    .then(r => r.json())
    .then(data => console.log(data.message))
    .catch(e => console.error(e));
};

window.submitManualOrder = function(action) {
    const exchange = document.getElementById('manual-exchange').value;
    const symbol = document.getElementById('manual-symbol').value.trim();
    
    if (!symbol) {
        alert("Please enter a Script Name (e.g. NIFTY 02 Jun 23500 CE)");
        return;
    }

    const payload = {
        exchange: exchange,
        symbol: symbol,
        action: action
    };

    fetch('/api/manual_order', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
        console.log(data.message);
        if (data.status === "error") {
            alert("BROKER ERROR: \n" + data.message);
        } else {
            alert("Success: " + data.message);
            document.getElementById('manual-symbol').value = ""; // clear after success
        }
    })
    .catch(e => {
        console.error("Error submitting manual order:", e);
        alert("Failed to submit order. Check console logs.");
    });
};

let searchTimeout;
window.searchInstruments = function(query) {
    if (query.length < 3) return; // Only search after 3 chars
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        fetch(`/api/search_symbols?q=${encodeURIComponent(query)}`)
            .then(r => r.json())
            .then(data => {
                const datalist = document.getElementById('instrument-list');
                datalist.innerHTML = '';
                if (data && data.length) {
                    data.forEach(sym => {
                        let option = document.createElement('option');
                        option.value = sym;
                        datalist.appendChild(option);
                    });
                }
            })
            .catch(e => console.error("Error searching symbols:", e));
    }, 300); // 300ms debounce
};

let ltpTimeout;
window.fetchLTP = function(symbol) {
    if (symbol.length < 5) {
        document.getElementById('manual-ltp-display').innerText = '--';
        return;
    }
    clearTimeout(ltpTimeout);
    ltpTimeout = setTimeout(() => {
        document.getElementById('manual-ltp-display').innerText = 'Loading...';
        fetch(`/api/get_ltp?symbol=${encodeURIComponent(symbol)}`)
            .then(r => r.json())
            .then(data => {
                if (data.status === 'ok') {
                    document.getElementById('manual-ltp-display').innerText = '₹ ' + data.ltp;
                } else {
                    document.getElementById('manual-ltp-display').innerText = '--';
                }
            })
            .catch(e => {
                console.error("Error fetching LTP:", e);
                document.getElementById('manual-ltp-display').innerText = 'Error';
            });
    }, 600); // debounce fetching LTP
};
