document.addEventListener('DOMContentLoaded', () => {
    const runBtn = document.getElementById('run-test-btn');
    const fileInput = document.getElementById('csv-upload');
    const testType = document.getElementById('test-type');
    const statusDiv = document.getElementById('test-status');
    const logOut = document.getElementById('test-output-log');
    const resultsPanel = document.getElementById('results-panel');

    runBtn.addEventListener('click', async () => {
        if (!fileInput.files || fileInput.files.length === 0) {
            alert("Please select a CSV file first!");
            return;
        }

        const file = fileInput.files[0];
        if (!file.name.endsWith('.csv')) {
            alert("File must be a .csv");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);
        formData.append("test_type", testType.value);

        statusDiv.style.display = 'block';
        resultsPanel.style.display = 'none';
        logOut.style.color = '#a1a1aa';
        logOut.innerText = `Uploading ${file.name} and starting simulation...\n`;

        runBtn.disabled = true;
        runBtn.innerText = "Running...";

        try {
            const response = await fetch('/api/run_csv_test', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            
            if (!response.ok || data.status === 'error') {
                logOut.style.color = 'var(--danger-color)';
                logOut.innerText += `\nError: ${data.message || 'Server returned an error'}`;
            } else {
                logOut.style.color = 'var(--success-color)';
                logOut.innerText += `\nSimulation completed successfully!\n\nMessage: ${data.message}`;
                
                // Show results
                if (data.results) {
                    document.getElementById('res-total-trades').innerText = data.results.total_trades || 0;
                    document.getElementById('res-win-rate').innerText = (data.results.win_rate || 0) + '%';
                    
                    const pnl = data.results.net_pnl || 0;
                    const pnlEl = document.getElementById('res-pnl');
                    pnlEl.innerText = `₹ ${pnl.toFixed(2)}`;
                    pnlEl.style.color = pnl >= 0 ? 'var(--success-color)' : 'var(--danger-color)';
                    
                    const dd = data.results.max_drawdown || 0;
                    document.getElementById('res-drawdown').innerText = `₹ ${dd.toFixed(2)}`;
                    
                    resultsPanel.style.display = 'block';
                }
            }
        } catch (error) {
            logOut.style.color = 'var(--danger-color)';
            logOut.innerText += `\nNetwork/Execution Error: ${error.message}`;
        } finally {
            runBtn.disabled = false;
            runBtn.innerText = "Run Simulator";
        }
    });
});
