document.addEventListener('DOMContentLoaded', () => {
    const navBtns = document.querySelectorAll('.nav-btn');
    const tabBtns = document.querySelectorAll('.tab-btn');
    const timeBtns = document.querySelectorAll('.time-btn');
    const tableHead = document.getElementById('table-head');
    const tableBody = document.getElementById('table-body');
    const loader = document.getElementById('loader');

    let currentScanner = 'breakout';
    let currentCategory = 'Large_Cap';
    let currentTimeframe = 'daily';

    // Initialize
    fetchData();

    // Event Listeners
    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            navBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentScanner = btn.dataset.scanner;
            fetchData();
        });
    });

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentCategory = btn.dataset.cat;
            fetchData();
        });
    });

    timeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            timeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentTimeframe = btn.dataset.time;
            fetchData();
        });
    });

    async function fetchData() {
        tableBody.innerHTML = '';
        loader.style.display = 'block';

        try {
            const response = await fetch(`/api/${currentScanner}/${currentCategory}?timeframe=${currentTimeframe}`);
            const data = await response.json();
            
            loader.style.display = 'none';
            renderTable(data.data);
        } catch (error) {
            console.error('Error fetching data:', error);
            loader.style.display = 'none';
            tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center; color: var(--danger);">Error fetching data</td></tr>';
        }
    }

    function renderTable(data) {
        // Always set Headers based on scanner type first, regardless of results
        if (currentScanner === 'breakout') {
            tableHead.innerHTML = `
                <th>Rank</th>
                <th>Symbol</th>
                <th>Sector</th>
                <th>CMP</th>
                <th>52W High</th>
                <th>Volume Surge</th>
            `;
        } else {
            tableHead.innerHTML = `
                <th>Rank</th>
                <th>Symbol</th>
                <th>Sector</th>
                <th>CMP</th>
                <th>52W Low</th>
                <th>Distance to Low</th>
            `;
        }

        if (!data || data.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center; color: var(--text-muted); padding: 2rem;">No stocks met the Momentum Breakout criteria today.</td></tr>';
            return;
        }

        // Fill Data
        tableBody.innerHTML = data.map(row => {
            if (currentScanner === 'breakout') {
                return `
                    <tr>
                        <td class="rank">#${row.Rank}</td>
                        <td class="symbol">${row.Symbol}</td>
                        <td>${row.Sector}</td>
                        <td style="color: var(--success); font-weight: 600;">${row.CMP}</td>
                        <td>${row['52W_High'] === 'New High' ? '<span style="color: var(--accent);">New High 🚀</span>' : row['52W_High']}</td>
                        <td style="color: ${parseFloat(row.Volume_Surge) > 2 ? 'var(--accent)' : 'var(--text-main)'}">${row.Volume_Surge}</td>
                    </tr>
                `;
            } else {
                return `
                    <tr>
                        <td class="rank">#${row.Rank}</td>
                        <td class="symbol">${row.Symbol}</td>
                        <td>${row.Sector}</td>
                        <td style="color: var(--success); font-weight: 600;">${row.CMP}</td>
                        <td>${row['52W_Low']}</td>
                        <td style="color: var(--accent);">${row.Distance}</td>
                    </tr>
                `;
            }
        }).join('');
    }
});
