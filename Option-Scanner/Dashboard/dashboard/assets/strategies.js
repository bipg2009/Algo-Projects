document.addEventListener("DOMContentLoaded", () => {
    const wsStatusDot = document.getElementById("ws-status-dot");
    const wsStatusText = document.getElementById("ws-status-text");
    const lastUpdateTime = document.getElementById("last-update-time");
    const scannerState = document.getElementById("scanner-state");
    const marketTrendDisplay = document.getElementById("market-trend");

    // Strategy DOM Elements
    const elements = {
        "Uptrend": { card: document.getElementById("card-uptrend"), stats: document.getElementById("stats-uptrend"), status: document.getElementById("status-uptrend") },
        "Downtrend": { card: document.getElementById("card-downtrend"), stats: document.getElementById("stats-downtrend"), status: document.getElementById("status-downtrend") },
        "Chop_Mode": { card: document.getElementById("card-chop"), stats: document.getElementById("stats-chop"), status: document.getElementById("status-chop") },
        "Theta_Dodge": { card: document.getElementById("card-theta"), stats: document.getElementById("stats-theta"), status: document.getElementById("status-theta") },
        "Order_Book_Imbalance": { card: document.getElementById("card-obi"), stats: document.getElementById("stats-obi"), status: document.getElementById("status-obi") }
    };

    let currentTrend = "WAITING";
    let ws;
    let reconnectInterval = 2000;

    // 1. Fetch initial statistics from the backend tracking logic
    function fetchInitialStats() {
        fetch('/api/strategy_stats')
            .then(res => res.json())
            .then(data => {
                for (const [strategy, count] of Object.entries(data)) {
                    if (elements[strategy]) {
                        elements[strategy].stats.textContent = `${count} Signals`;
                    }
                }
            })
            .catch(e => console.error("Error fetching stats:", e));
    }

    // 2. Connect WebSocket to listen to Live trend and dynamic signals
    function connect() {
        ws = new WebSocket(`ws://${window.location.host}/ws`);

        ws.onopen = () => {
            wsStatusDot.className = "dot connected";
            wsStatusText.textContent = "Connected";
            fetchInitialStats(); // Refresh stats on connection
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
                scannerState.textContent = data.payload.status;
                scannerState.className = `state-text ${data.payload.status.toLowerCase()}`;
                break;
            case "MARKET_TREND":
                currentTrend = data.payload;
                marketTrendDisplay.textContent = currentTrend;
                marketTrendDisplay.className = `state-text ${currentTrend.toLowerCase()}`;
                updateStrategyStatuses();
                break;
            case "LOG":
                if (data.payload && data.payload.message) {
                    const msg = data.payload.message;
                    // Show all messages to prove it's ticking!
                    appendLog(msg, data.payload.level || "info");
                }
                break;
            case "NEW_SIGNAL":
                // Dynamically increment UI count based on incoming signal event
                if (data.payload && data.payload.strategy) {
                    const strat = data.payload.strategy;
                    if (elements[strat]) {
                        // Very simple visual bounce effect
                        elements[strat].card.style.transform = "scale(1.02)";
                        elements[strat].card.style.borderColor = "#4ade80";
                        setTimeout(() => {
                            elements[strat].card.style.transform = "";
                            elements[strat].card.style.borderColor = "";
                        }, 500);

                        // We can either parse the integer or just fetch latest stats to be safe
                        fetchInitialStats(); 
                    }
                    
                    appendLog(`🔥 APPROVED SIGNAL: ${data.payload.action} ${data.payload.symbol}`, "success");
                }
                break;
        }
    }
    
    function appendLog(message, level) {
        const container = document.getElementById("live-events-container");
        if (!container) return;
        
        // Remove the placeholder if it exists
        if (container.children.length === 1 && container.children[0].innerText.includes("Awaiting")) {
            container.innerHTML = "";
        }
        
        const div = document.createElement("div");
        div.className = "log-entry";
        
        let typeClass = "log-info";
        let icon = "ℹ️";
        if (message.includes("reject")) {
            typeClass = "log-reject";
            icon = "❌";
        } else if (message.includes("Watchlist")) {
            typeClass = "log-watchlist";
            icon = "👀";
        } else if (level === "success" || message.includes("APPROVED")) {
            typeClass = "log-approve";
            icon = "✅";
        } else if (level === "error") {
            typeClass = "log-error";
            icon = "⚠️";
        }
        
        div.classList.add(typeClass);
        
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], {hour12: false});
        
        div.innerHTML = `<span class="log-time">[${timeStr}]</span> <span>${icon} ${message}</span>`;
        container.appendChild(div);
        
        // Auto scroll
        container.scrollTop = container.scrollHeight;
        
        // Keep max 100 logs to prevent memory leaks
        if (container.children.length > 100) {
            container.removeChild(container.firstChild);
        }
    }

    function updateStrategyStatuses() {
        // Reset all to Standby first
        Object.values(elements).forEach(el => {
            el.status.textContent = "STANDBY";
            el.status.className = "status-tag status-standby";
        });

        // Apply dynamic highlighting based on the Market Trend
        if (currentTrend === "UP") {
            elements["Uptrend"].status.textContent = "ACTIVE";
            elements["Uptrend"].status.className = "status-tag status-active";
        } else if (currentTrend === "DOWN") {
            elements["Downtrend"].status.textContent = "ACTIVE";
            elements["Downtrend"].status.className = "status-tag status-active";
        } else if (currentTrend === "SIDEWAYS" || currentTrend === "CHOPPY") {
            elements["Chop_Mode"].status.textContent = "ACTIVE";
            elements["Chop_Mode"].status.className = "status-tag status-active";
        }

        // Theta and OBI are always active regardless of trend, as they rely on immediate micro-structure
        elements["Theta_Dodge"].status.textContent = "SCANNING";
        elements["Theta_Dodge"].status.className = "status-tag status-active";
        
        elements["Order_Book_Imbalance"].status.textContent = "SCANNING";
        elements["Order_Book_Imbalance"].status.className = "status-tag status-active";
    }

    function renderSector(containerId, sectors) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        // Convert to array and sort by total weight
        const sortedSectors = Object.entries(sectors).sort((a, b) => {
            const wA = a[1].components.reduce((acc, c) => acc + c.weight, 0);
            const wB = b[1].components.reduce((acc, c) => acc + c.weight, 0);
            return wB - wA;
        });

        container.innerHTML = "";
        
        sortedSectors.forEach(([secName, data]) => {
            const safeName = secName.replace(/_/g, ' ');
            const pct = data.bullish_pct.toFixed(1);
            
            // Build tooltip with component details
            let tooltipText = "";
            data.components.forEach(c => {
                const icon = c.status === "BULLISH" ? "🟢" : "🔴";
                tooltipText += `${icon} ${c.name} (${c.weight}%)\n`;
            });
            
            const div = document.createElement("div");
            div.style.marginBottom = "8px";
            div.title = tooltipText;
            div.innerHTML = `
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 4px; color: var(--text-secondary);">
                    <span>${safeName}</span>
                    <span style="color: ${pct > 50 ? 'var(--success)' : (pct == 50 ? 'var(--warning)' : 'var(--danger)')}">${pct}% Bullish</span>
                </div>
                <div style="width: 100%; height: 6px; background: rgba(239, 68, 68, 0.3); border-radius: 3px; overflow: hidden; display: flex;">
                    <div style="width: ${pct}%; height: 100%; background: var(--success); transition: width 0.5s ease;"></div>
                </div>
            `;
            container.appendChild(div);
        });
    }

    function fetchSectorOutlook() {
        fetch('/api/sector_outlook')
            .then(res => res.json())
            .then(data => {
                const updateEl = document.getElementById("sector-update-time");
                if (updateEl) updateEl.textContent = `Last yfinance fetch: ${data.last_updated}`;
                
                // Nifty
                const nTotalEl = document.getElementById("nifty-total-score");
                if (nTotalEl) {
                    const health = data.nifty_total_weight > 0 ? (data.nifty_total_bullish / data.nifty_total_weight) * 100 : 0;
                    nTotalEl.textContent = `Overall Health: ${health.toFixed(1)}% Bullish`;
                    nTotalEl.style.color = health > 50 ? "var(--success)" : "var(--danger)";
                }
                if (Object.keys(data.nifty_sectors || {}).length > 0) {
                    renderSector("nifty-sectors-container", data.nifty_sectors);
                }
                
                // Sensex
                const sTotalEl = document.getElementById("sensex-total-score");
                if (sTotalEl) {
                    const health = data.sensex_total_weight > 0 ? (data.sensex_total_bullish / data.sensex_total_weight) * 100 : 0;
                    sTotalEl.textContent = `Overall Health: ${health.toFixed(1)}% Bullish`;
                    sTotalEl.style.color = health > 50 ? "var(--success)" : "var(--danger)";
                }
                if (Object.keys(data.sensex_sectors || {}).length > 0) {
                    renderSector("sensex-sectors-container", data.sensex_sectors);
                }
            })
            .catch(e => console.error("Error fetching sector outlook:", e));
    }

    function fetchDhanStatus() {
        fetch('/api/dhan_status')
            .then(res => res.json())
            .then(data => {
                const statusEl = document.getElementById("dhan-status");
                const balEl = document.getElementById("dhan-balance");
                const pnlEl = document.getElementById("dhan-pnl");
                const timeEl = document.getElementById("dhan-update-time");
                
                if (statusEl) {
                    statusEl.textContent = data.status;
                    if (data.status.includes("Connected")) {
                        statusEl.style.color = "var(--success)";
                    } else if (data.status.includes("Error") || data.status.includes("Disconnected")) {
                        statusEl.style.color = "var(--danger)";
                    }
                }
                
                if (balEl) {
                    balEl.textContent = "₹" + (data.balance || 0).toLocaleString('en-IN', {maximumFractionDigits: 2});
                }
                
                if (pnlEl) {
                    const pnl = data.pnl || 0;
                    pnlEl.textContent = "₹" + pnl.toLocaleString('en-IN', {maximumFractionDigits: 2});
                    pnlEl.style.color = pnl >= 0 ? "var(--success)" : "var(--danger)";
                }
                
                if (timeEl) {
                    timeEl.textContent = `Last sync: ${data.last_updated}`;
                }
            })
            .catch(e => console.error("Error fetching Dhan status:", e));
    }

    // Initialization
    connect();
    fetchSectorOutlook();
    fetchDhanStatus();
    setInterval(fetchSectorOutlook, 5000);
    setInterval(fetchDhanStatus, 5000);
});
