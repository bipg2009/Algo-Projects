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

    function connect() {
        const host = window.location.host || "127.0.0.1:5173";
        ws = new WebSocket(`ws://${host}/ws`);

        ws.onopen = () => {
            wsStatusDot.className = "dot connected";
            wsStatusText.textContent = "Connected";
            addLog("System", "WebSocket connected successfully.", "success");
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleEvent(data);
                
            } catch (e) {
                console.error("Error parsing WS message", e);
            }
        };

        ws.onclose = () => {
            wsStatusDot.className = "dot disconnected";
            wsStatusText.textContent = "Disconnected";
            addLog("System", "WebSocket disconnected. Reconnecting...", "error");
            setTimeout(connect, reconnectInterval);
        };

        ws.onerror = (err) => {
            console.error("WebSocket error", err);
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
            // case "CHAIN_TICKER":
            //     updateChainTicker(data.payload);
            //     break;
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
        if (!payload) return;
        
        lastTickerPayload = payload;
        
        const spotVal = typeof payload.spot === 'number' ? payload.spot.toFixed(2) : (payload.spot ? parseFloat(payload.spot).toFixed(2) : "0.00");
        tickerSpot.textContent = `Spot: ${spotVal}`;
        
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
            if (!opt) return;
            const tr = document.createElement("tr");
            
            // Safe parsing for numeric values
            const ltpVal = typeof opt.ltp === 'number' ? opt.ltp.toFixed(2) : (opt.ltp ? parseFloat(opt.ltp).toFixed(2) : "0.00");
            const volVal = typeof opt.volume === 'number' ? opt.volume.toLocaleString() : (opt.volume ? parseInt(opt.volume).toLocaleString() : "0");
            const oiChange = opt.oi_change || 0;
            const oiChangePct = opt.oi_change_pct || 0;
            
            // Format OI Change string: "Absolute (Percentage%)"
            const oiChangeSign = oiChange > 0 ? "+" : "";
            const oiChangeClass = oiChange > 0 ? "profit" : (oiChange < 0 ? "loss" : "");
            const oiText = `${oiChangeSign}${oiChange.toLocaleString()} (${oiChangeSign}${oiChangePct.toFixed(1)}%)`;

            tr.innerHTML = `
                <td><strong>${opt.symbol || ''}</strong></td>
                <td>${ltpVal}</td>
                <td>${volVal}</td>
                <td class="${oiChangeClass}">${oiText}</td>
                <td><button class="action-btn buy-btn" onclick="testBuy('${opt.symbol || ''}', '${opt.type || ''}', ${parseFloat(ltpVal)})">Buy TEST</button></td>
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
        li.innerHTML = `
            <div>
                <span class="signal-symbol">${signal.symbol}</span>
                <span style="margin-left:8px; font-size:0.75rem;">${signal.type}</span>
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

    // Fetch and update ATM Option Chain from /api/atm_chain every 30 seconds
    function fetchAtmChainFromFile() {
        fetch('/api/atm_chain', { cache: 'no-store' })
            .then(r => r.json())
            .then(data => {
                if (data && data.options) {
                    updateChainTicker(data);
                    
                    // Only update the display date/time when the Option Chain successfully updates!
                    const now = new Date();
                    lastUpdateTime.textContent = `Last update: ${now.toLocaleTimeString()}`;
                }
            })
            .catch(e => console.error("Error fetching ATM chain from file:", e));
    }

    // Initialize
    connect();
    
    // Initial fetch from file and schedule 20s interval
    setTimeout(fetchAtmChainFromFile, 1000);
    setInterval(fetchAtmChainFromFile, 20000);
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
    const limitPriceStr = document.getElementById('manual-limit-price').value.trim();
    const limitPrice = parseFloat(limitPriceStr) || 0.0;
    
    if (!symbol) {
        alert("Please enter a Script Name (e.g. NIFTY 02 Jun 23500 CE)");
        return;
    }

    const payload = {
        exchange: exchange,
        symbol: symbol,
        action: action,
        limit_price: limitPrice
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
