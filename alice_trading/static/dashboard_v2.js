document.addEventListener('DOMContentLoaded', () => {
    async function fetchMetrics() {
        try {
            const response = await fetch('/api/v1/dashboard/metrics');
            if (response.ok) {
                const data = await response.json();
                
                // Update Health
                const healthSpan = document.querySelector('.status-indicator span:last-child');
                healthSpan.textContent = `SYSTEM HEALTH: ${data.metrics.system_health}% | MODE: ${data.metrics.system_mode}`;
                
                // Update Capital
                const capitalEl = document.querySelector('.big-number');
                const pnl = data.metrics.daily_pnl || 0;
                capitalEl.textContent = `₹${(data.metrics.total_capital + pnl).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
                
                // Update Trend
                const trendEl = document.querySelector('.trend');
                trendEl.textContent = pnl >= 0 ? `▲ +₹${pnl.toLocaleString('en-IN')}` : `▼ -₹${Math.abs(pnl).toLocaleString('en-IN')}`;
                trendEl.className = `trend ${pnl >= 0 ? 'up' : 'down'}`;
                
                // Update Signals (Market data)
                const signalList = document.querySelector('.signal-list');
                signalList.innerHTML = '';
                
                Object.entries(data.market_data || {}).slice(0, 5).forEach(([symbol, info]) => {
                    if(!info.ltp) return;
                    const li = document.createElement('li');
                    
                    // Simple mock signal generation based on price relation to close
                    let signal = 'HOLD';
                    let cls = 'hold';
                    if (info.ltp > info.close) { signal = 'BUY'; cls = 'buy'; }
                    else if (info.ltp < info.close) { signal = 'SELL'; cls = 'sell'; }

                    li.innerHTML = `
                        <span class="badge ${cls}">${signal}</span> 
                        <strong>${symbol}</strong> 
                        <span class="price">₹${info.ltp.toLocaleString('en-IN')}</span>
                    `;
                    signalList.appendChild(li);
                });
            }
        } catch (error) {
            console.error('Failed to fetch dashboard metrics:', error);
        }
    }

    // Refresh every 2 seconds
    fetchMetrics();
    setInterval(fetchMetrics, 2000);
});
