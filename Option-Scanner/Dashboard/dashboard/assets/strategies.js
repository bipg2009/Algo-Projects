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
                }
                break;
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

    // Initialization
    connect();
});
