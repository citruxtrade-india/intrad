/**
 * ANTIGRAVITY INSTITUTIONAL ALGO PLATFORM - CORE LOGIC
 */

const state = {
    isAuth: false,
    selectedMarket: 'NIFTY',
    selectedCommodity: 'GOLD',
    metrics: null,
    trades: [],
    logs: [],
    pnlHistory: [], // Will populate with real-time data
    pnlTimestamps: [], // Corresponding timestamps
    pnlFullTimestamps: [], // Full timestamp strings for tooltips
    chartTimeRange: '1D', // Default time range: 1 Day
    marketFeedStatus: 'DISCONNECTED', // CONNECTED | DISCONNECTED | CONNECTING | RECONNECTING
    executionMode: 'MOCK',
    marketBias: {
        'NIFTY': { bias: 'BULLISH', strength: 82 },
        'BANKNIFTY': { bias: 'BEARISH', strength: 65 },
        'SENSEX': { bias: 'BULLISH', strength: 71 },
        'COMMODITY': { bias: 'NEUTRAL', strength: 40 }
    },
    usageLimit: null,
    account_update: null, // Anti-Gravity Account Balance Data
    agentV2Status: {},
    auditTrail: [],
    theme: localStorage.getItem('theme') || 'dark',
    commodityFeedStatus: 'DISCONNECTED',  // CONNECTED | DISCONNECTED | CONNECTING | RECONNECTING
    commodityLastUpdate: null,
    deepTimeframe: '5m',
    ohlcChart: null
};

const agentMetadata = {
    'MarketContext': {
        name: "MarketContext",
        role: "Market Context Analyst",
        responsibilities: [
            "Analyze macro trend",
            "Detect volatility regime",
            "Identify session bias",
            "Monitor market sentiment"
        ],
        inputs: ["Live price feed", "Index data", "Volatility metrics"],
        outputs: ["Market bias (Bullish/Bearish/Neutral)", "Regime state"],
        dependencies: ["External Market Feed"],
        risk_impact: "LOW",
        execution_authority: false,
        visibility: "explainable"
    },
    'StructurePattern': {
        name: "StructurePattern",
        role: "Pattern Recognition Agent",
        responsibilities: [
            "Identify chart structures",
            "Detect breakout/breakdown zones",
            "Recognize continuation/reversal setups"
        ],
        inputs: ["OHLC data", "Structure rules"],
        outputs: ["Pattern classification", "Structural confidence"],
        dependencies: ["MarketContext"],
        risk_impact: "MEDIUM",
        execution_authority: false,
        visibility: "explainable"
    },
    'Validation': {
        name: "Validation",
        role: "Strategic Validator",
        responsibilities: [
            "Cross-check signals from MarketContext + StructurePattern",
            "Filter false positives",
            "Confirm multi-factor alignment"
        ],
        inputs: ["Context output", "Pattern output"],
        outputs: ["Validated trade signal (Yes/No)", "Confidence score"],
        dependencies: ["MarketContext", "StructurePattern"],
        risk_impact: "HIGH",
        execution_authority: false,
        visibility: "explainable"
    },
    'RiskCapital': {
        name: "RiskCapital",
        role: "Risk Management Officer",
        responsibilities: [
            "Position sizing",
            "Capital allocation",
            "Max drawdown enforcement",
            "Risk-reward validation"
        ],
        inputs: ["Validated signal", "Account balance"],
        outputs: ["Approved size", "SL/TP levels"],
        dependencies: ["Validation"],
        risk_impact: "CRITICAL",
        execution_authority: false,
        visibility: "explainable"
    },
    'Execution': {
        name: "Execution",
        role: "Execution Engine",
        responsibilities: [
            "Route orders (Paper or Live)",
            "Apply slippage model",
            "Confirm fill",
            "Update trade state"
        ],
        inputs: ["Risk-approved trade"],
        outputs: ["Order status", "Execution report"],
        dependencies: ["RiskCapital"],
        risk_impact: "CRITICAL",
        execution_authority: true,
        visibility: "explainable"
    },
    'AuditLogger': {
        name: "AuditLogger",
        role: "Governance & Transparency Agent",
        responsibilities: [
            "Record every decision",
            "Log signal trail",
            "Track performance metrics",
            "Maintain explainability history"
        ],
        inputs: ["All agent outputs"],
        outputs: ["Audit log", "Performance analytics"],
        dependencies: ["All Agents"],
        risk_impact: "LOW",
        execution_authority: false,
        visibility: "explainable"
    },
    'Guidance': {
        name: "Guidance",
        role: "AI Strategic Advisor",

        responsibilities: [
            "Provide meta-analysis",
            "Suggest optimizations",
            "Highlight anomalies",
            "Explain decision chain"
        ],
        inputs: ["Full agent network state"],
        outputs: ["Strategic insights", "Improvement suggestions"],
        dependencies: ["AuditLogger"],
        risk_impact: "LOW",
        execution_authority: false,
        visibility: "explainable"
    },
    'StrategySelector': {
        name: "StrategySelector",
        role: "Strategic Execution Guide",
        responsibilities: [
            "Monitor market mood & volatility",
            "Determine optimal strategy mode",
            "Provide bias guidance to agents",
            "Optimize tactical parameters"
        ],
        inputs: ["Market context", "Global volatility"],
        outputs: ["Active strategy regime", "Reasoning bias"],
        dependencies: ["MarketContext"],
        risk_impact: "MEDIUM",
        execution_authority: false,
        visibility: "explainable"
    },
    'LearningEngine': {
        name: "LearningEngine",
        role: "Meta-Intelligence & Self-Awareness",
        responsibilities: [
            "Monitor system health & drawdowns",
            "Compute predictive trade scores",
            "Track strategy/pattern performance",
            "Regulate global risk multipliers"
        ],
        inputs: ["Trade outcomes", "System health metrics"],
        outputs: ["Self-diagnostic score", "Global risk scaling"],
        dependencies: ["All Agents"],
        risk_impact: "CRITICAL",
        execution_authority: true,
        visibility: "explainable"
    }
};

let pnlChart = null;
let syncInterval = null;
let isDashboardInitialized = false;

function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    state.theme = savedTheme;
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
        document.getElementById('theme-icon').textContent = '🌙';
    } else {
        document.body.classList.remove('light-theme');
        document.getElementById('theme-icon').textContent = '☀️';
    }
}

function toggleTheme() {
    if (state.theme === 'dark') {
        state.theme = 'light';
        document.body.classList.add('light-theme');
        localStorage.setItem('theme', 'light');
        document.getElementById('theme-icon').textContent = '🌙';
    } else {
        state.theme = 'dark';
        document.body.classList.remove('light-theme');
        localStorage.setItem('theme', 'dark');
        document.getElementById('theme-icon').textContent = '☀️';
    }
    if (pnlChart) initAnalytics();
}

window.addEventListener('DOMContentLoaded', initTheme);
window.addEventListener('load', initTheme);

const MARKET_PATTERNS = {
    'NIFTY': [
        { name: 'EMA 20/50 Crossover', confidence: 'High (84%)', direction: 'LONG', time: '14:45' },
        { name: 'VWAP Pullback Setup', confidence: 'Medium (62%)', direction: 'SHORT', time: '14:30' }
    ],
    'BANKNIFTY': [
        { name: 'Support Bounce', confidence: 'High (78%)', direction: 'LONG', time: '14:50' },
        { name: 'Breakdown Pattern', confidence: 'Low (48%)', direction: 'SHORT', time: '14:15' }
    ],
    'SENSEX': [
        { name: 'Range Consolidation', confidence: 'Medium (55%)', direction: 'LONG', time: '14:25' }
    ],
    'COMMODITY': []
};

function toggleSettingsPanel() {
    const panel = document.getElementById('settings-panel');
    if (panel) panel.classList.toggle('open');
}

function showTab(el, tabId) {
    if (typeof toggleAgentDrawer === 'function') toggleAgentDrawer(false);
    
    document.querySelectorAll('.content-view').forEach(v => v.classList.add('hidden'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    const target = document.getElementById(`tab-${tabId}`);
    if (target) target.classList.remove('hidden');
    if (el) el.classList.add('active');

    if (tabId === 'performance') initAnalytics();

    if (tabId === 'admin') {
        if (typeof initAdminDashboard === 'function') initAdminDashboard();
    } else {
        if (typeof destroyAdminDashboard === 'function') destroyAdminDashboard();
    }

    if (tabId === 'profile') {
        if (typeof fetchUserProfile === 'function') fetchUserProfile();
    }
}

function showAuthPage(page) {
    const cards = ['login', 'register', 'otp', 'forgot'];
    cards.forEach(c => {
        const el = document.getElementById(`card-${c}`);
        if (el) el.classList.add('hidden');
    });

    const target = document.getElementById(`card-${page}`);
    if (target) target.classList.remove('hidden');
}

async function handleLogin() {
    const user_id = document.getElementById('login-id').value.trim();
    const api_key = document.getElementById('login-pass').value;
    const rememberMe = document.getElementById('remember-me').checked;

    const idRegex = /^[a-zA-Z0-9_]{4,20}$/;

    if (!user_id || !api_key) {
        return alert("Validation Error: Please enter both User ID and API Key");
    }

    if (!idRegex.test(user_id) && !user_id.includes('@')) {
        return alert("Validation Error: User ID must be 4-20 characters (alphanumeric) or a valid email.");
    }

    if (api_key.length < 5) {
        return alert("Validation Error: API Key/Password must be at least 5 characters.");
    }

    try {
        const res = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id, api_key })
        });

        const data = await res.json();

        if (res.ok && data.status === 'success') {
            state.isAuth = true;
            localStorage.setItem('antigravity_authenticated', 'true');
            localStorage.setItem('antigravity_user_id', user_id);
            // Store Firebase token if needed
            if (data.data && data.data.accessToken) {
                localStorage.setItem('firebase_token', data.data.accessToken);
            }

            // Remember Me Logic
            if (rememberMe) {
                localStorage.setItem('antigravity_user_id', user_id);
            } else {
                localStorage.removeItem('antigravity_user_id');
            }

            document.getElementById('auth-layer').classList.add('hidden');
            document.getElementById('app-layer').classList.remove('hidden');

            // Explicitly ensure side panels are closed on fresh login
            document.getElementById('settings-panel').classList.remove('open');

            initDashboard();
        } else {
            if (res.status === 403) {
                pendingAuthEmail = user_id;
                alert("Email Verification Required: A link has already been sent to your email. Please verify and then login.");
                showAuthPage('otp'); 
                // Update UI for Link Verification instead of OTP boxes
                const otpInputs = document.querySelector('.otp-inputs');
                if (otpInputs) otpInputs.style.display = 'none';
                const subtitle = document.querySelector('#card-otp .auth-subtitle');
                if (subtitle) subtitle.textContent = "Please check your inbox for the verification link.";
                const timerEl = document.getElementById('otp-timer');
                if (timerEl) timerEl.parentElement.style.display = 'none';
                const validateBtn = document.querySelector('#card-otp .auth-btn');
                if (validateBtn) {
                    validateBtn.textContent = "RETURN TO LOGIN";
                    validateBtn.onclick = () => showAuthPage('login');
                }
                return;
            }
            alert("Security Protocol: Access Denied. " + (data.message || "Invalid Credentials Provided."));
        }
    } catch (err) {
        alert("Institutional Network Error: Unable to reach Command Center.");
    }
}

// Auto-populate Remember Me & Auto-login
window.addEventListener('load', () => {
    const savedId = localStorage.getItem('antigravity_user_id');
    if (savedId) {
        const loginIdEl = document.getElementById('login-id');
        const rememberMeEl = document.getElementById('remember-me');
        if (loginIdEl) loginIdEl.value = savedId;
        if (rememberMeEl) rememberMeEl.checked = true;
    }

    // --- RECOVERY LOGIC: Check if session should persist ---
    if (localStorage.getItem('antigravity_authenticated') === 'true') {
        console.log("Session Recovery: Re-establishing institutional connection...");
        state.isAuth = true;

        const authLayer = document.getElementById('auth-layer');
        const appLayer = document.getElementById('app-layer');

        if (authLayer) authLayer.classList.add('hidden');
        if (appLayer) appLayer.classList.remove('hidden');

        initDashboard();
    }
});

let pendingAuthEmail = null;

async function handleSignup() {
    // Collect registration data
    const name = document.querySelector('#card-register input[placeholder="John Doe"]').value;
    const email = document.querySelector('#card-register input[placeholder="john@example.com"]').value;
    const phone = document.querySelector('#card-register input[placeholder="+91 98765 43210"]').value;
    const password = document.querySelector('#card-register input[type="password"]').value;

    if (!name || !email || !password) {
        return alert("Please fill in all institutional required fields.");
    }

    try {
        const res = await fetch('/api/v1/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, phone, password })
        });
        const data = await res.json();
        if (res.ok) {
            pendingAuthEmail = email; 
            alert("Account Created! A verification link has been sent to your email. Please verify before logging in.");
            showAuthPage('otp');
            
            // Re-label visual flow for Link verification
            const otpInputs = document.querySelector('.otp-inputs');
            if (otpInputs) otpInputs.style.display = 'flex';
            const subtitle = document.querySelector('#card-otp .auth-subtitle');
            if (subtitle) subtitle.textContent = "Verification link sent to " + email;
            const timerEl = document.getElementById('otp-timer');
            if (timerEl) timerEl.parentElement.style.display = 'none';
            const validateBtn = document.querySelector('#card-otp .auth-btn');
            if (validateBtn) {
                validateBtn.textContent = "VERIFY OTP";
                validateBtn.onclick = () => validateOTP();
            }
        } else {
            alert(data.message || "Signup Registration Failed");
        }
    } catch (err) {
        alert("Institutional Setup Connection Error");
    }
}

document.getElementById('btn-register-confirm').onclick = handleSignup;

let otpTimerInterval = null;

function startOTPTimer() {
    let timeLeft = 300; // 5 minutes
    const timerEl = document.getElementById('otp-timer');
    if (!timerEl) return;
    
    timerEl.style.cursor = 'default';
    timerEl.onclick = null;
    
    if (otpTimerInterval) clearInterval(otpTimerInterval);
    
    otpTimerInterval = setInterval(() => {
        const mins = Math.floor(timeLeft / 60);
        const secs = timeLeft % 60;
        timerEl.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        if (timeLeft <= 0) {
            clearInterval(otpTimerInterval);
            timerEl.textContent = "Click to Resend";
            timerEl.style.cursor = 'pointer';
            timerEl.onclick = handleResendOTP;
        }
        timeLeft--;
    }, 1000);
}

function moveOTP(input, next) {
    if (input.value.length === 1 && next <= 6) {
        const nextBox = document.querySelectorAll('.otp-box')[next];
        if (nextBox) nextBox.focus();
    }
}

async function handleResendOTP() {
    if (!pendingAuthEmail) return alert("Email missing.");
    try {
        const res = await fetch('/api/v1/auth/resend-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: pendingAuthEmail })
        });
        const data = await res.json();
        if (res.ok) {
            alert(data.message || "New OTP sent");
            startOTPTimer();
        } else {
            alert(data.message || "Failed to resend OTP");
        }
    } catch(e) {
        alert("Connection Error.");
    }
}

async function validateOTP() {
    const boxes = document.querySelectorAll('.otp-box');
    const otp = Array.from(boxes).map(b => b.value).join('');

    if (otp.length < 6) return alert("Please enter the full 6-digit secure code.");

    try {
        const res = await fetch('/api/v1/auth/verify-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: pendingAuthEmail, otp: otp })
        });
        const data = await res.json();
        
        if (res.ok) {
            alert(data.message || "Identity Verified. Account Activated.");
            showAuthPage('login');
            boxes.forEach(b => b.value = '');
        } else {
            alert(data.message || "Verify Failed.");
            boxes.forEach(b => b.value = '');
            if (boxes[0]) boxes[0].focus();
        }
    } catch(err) {
        alert("Network Error");
    }
}

async function handleForgotPassword() {
    const email = document.getElementById('forgot-email').value;
    if (!email || !email.includes('@')) {
        return alert("Please enter a valid institution email.");
    }

    try {
        const res = await fetch('http://localhost:3000/auth/forgot-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (res.ok) {
            alert(data.message || "Recovery link sent. Check your secure inbox.");
            showAuthPage('login');
        } else {
            alert("Recovery Protocol Failure");
        }
    } catch (err) {
        alert("Global Command Center Connection Error");
    }
}

function logout() {
    state.isAuth = false;
    localStorage.removeItem('antigravity_authenticated');
    document.getElementById('app-layer').classList.add('hidden');
    document.getElementById('auth-layer').classList.remove('hidden');
    // Clear sensitive inputs
    const loginPassEl = document.getElementById('login-pass');
    if (loginPassEl) loginPassEl.value = '';
    console.log("User logged out. Stopping agents.");
}

// --- DASHBOARD LOGIC ---

async function initDashboard() {
    if (isDashboardInitialized) return;
    isDashboardInitialized = true;

    fetchSystemData();
    if (syncInterval) clearInterval(syncInterval);
    syncInterval = setInterval(fetchSystemData, 2000);

    initSymbolSearch();
    initAnalytics();
    updateDetectedPatterns(state.selectedMarket); // Initialize pattern display
    initScrollShadow(); // Setup scroll shadow effect
    setupDashboardEvents();

    // --- ANTI-GRAVITY ACCOUNT UPDATE EVENT LISTENER ---
    window.addEventListener('ACCOUNT_UPDATE', (event) => {
        const data = event.detail;
        if (data && data.balance !== undefined) {
            const bal = parseFloat(data.balance);
            if (state.metrics) state.metrics.total_capital = bal;
            const topCapEl = document.getElementById('select-total-cap');
            if (topCapEl) {
                let exists = false;
                for (let i = 0; i < topCapEl.options.length; i++) {
                    if (topCapEl.options[i].value === bal.toString()) exists = true;
                }
                if (!exists) {
                    const opt = document.createElement('option');
                    opt.value = bal.toString();
                    opt.text = '₹' + fmtNum(bal) + (state.executionMode === 'REAL' ? ' (LIVE)' : '');
                    topCapEl.add(opt, topCapEl.options[1]);
                }
                topCapEl.value = bal.toString();
            }
            const capEl = document.getElementById('set-total-capital');
            if (capEl && document.activeElement !== capEl) capEl.value = bal;
            updateDashboardUI(); // Immediate refresh
        }
    });
}

function setupDashboardEvents() {
    // Market Tabs
    document.querySelectorAll('.market-tab').forEach(tab => {
        tab.onclick = () => {
            document.querySelectorAll('.market-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            state.selectedMarket = tab.dataset.market;

            // Toggle Commodity selector
            const commWrapper = document.getElementById('commodity-selector-wrapper');
            if (commWrapper) {
                if (state.selectedMarket === 'COMMODITY') {
                    commWrapper.classList.remove('hidden');
                } else {
                    commWrapper.classList.add('hidden');
                }
            }

            updateDetectedPatterns(state.selectedMarket); // Update patterns dynamically
            updateMonitoringScope(); // Sync with backend
            updateDashboardUI();
        };
    });

    // Commodity Selection
    const commSelect = document.getElementById('commodity-selector');
    if (commSelect) {
        commSelect.onchange = (e) => {
            state.selectedCommodity = e.target.value;
            console.log("Selected Commodity Switched:", state.selectedCommodity);
            updateMonitoringScope(); // Sync with backend
            updateDashboardUI();
        };
    }

    // Control Buttons
    document.getElementById('main-start').onclick = () => controlSystem('start');
    document.getElementById('main-emergency').onclick = () => controlSystem('square_off_all');
    document.getElementById('main-squareoff').onclick = () => controlSystem('square_off_all');

    // Risk Settings Trigger
    const riskBtn = document.querySelector('#tab-settings .auth-btn');
    if (riskBtn) riskBtn.onclick = saveInstitutionalSettings;

    // --- QUICK EXECUTION EVENTS ---
    const orderTypeSelect = document.getElementById('manual-order-type');
    if (orderTypeSelect) {
        orderTypeSelect.onchange = (e) => {
            const limitRow = document.getElementById('limit-price-row');
            if (limitRow) {
                limitRow.style.display = e.target.value === 'LIMIT' ? 'block' : 'none';
            }
        };
    }

    // Execution Mode Modal Triggers
    const sidebarModeBtn = document.getElementById('broker-mode-sidebar');
    if (sidebarModeBtn) sidebarModeBtn.onclick = openModeSelectionModal;

    // Mode Selection Buttons (Programmatic Binding)
    ['mock', 'simulation', 'paper', 'real'].forEach(mode => {
        const btn = document.getElementById(`mode-sel-${mode}`);
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log(`Mode button clicked: ${mode}`);
                confirmModeSwitch(mode.toUpperCase());
            });
            // Ensure pointer events are active
            btn.style.pointerEvents = 'auto';
        }
    });

    // Close Modal Button
    const closeBtn = document.querySelector('#mode-layer .nav-btn');
    if (closeBtn) {
        closeBtn.onclick = (e) => {
            e.preventDefault();
            closeModeModal();
        };
    }
}

async function fetchSystemData() {
    if (!state.isAuth) return;
    try {
        const mRes = await fetch('/api/v1/dashboard/metrics');
        const tRes = await fetch('/api/v1/trades/open');
        const lRes = await fetch('/api/v1/alerts/logs');
        const aRes = await fetch('/api/v1/account/balance');
        const mStatusRes = await fetch('/api/v1/market/status');

        if (mRes.ok) {
            const data = await mRes.json();
            state.metrics = data.metrics || data;
            if (data.market_data) state.market_data = data.market_data;
            if (data.data_engine_status) state.dataEngineStatus = data.data_engine_status;
            state.isRunning = data.is_running;
            state.executionMode = state.metrics.execution_mode || data.execution_mode;
        }
        if (tRes.ok) state.trades = await tRes.json();
        if (lRes.ok) state.logs = await lRes.json();
        if (aRes.ok) {
            state.account_update = await aRes.json();
            // EMIT SIMULATION: Trigger UI update for balance
            window.dispatchEvent(new CustomEvent('ACCOUNT_UPDATE', { detail: state.account_update }));
        }
        if (mStatusRes.ok) {
            const mStatus = await mStatusRes.json();
            state.marketFeedStatus = mStatus.status;
        }

        // --- AGENT V2 SYNC ---
        const sRes = await fetch('/api/v1/agents/status');
        const dRes = await fetch('/api/v1/agents/audit');
        if (sRes.ok) state.agentV2Status = await sRes.json();
        if (dRes.ok) state.auditTrail = await dRes.json();

        // Track PnL history for the chart (keep last 50 points, ~100 seconds of data)
        if (state.metrics) {
            const now = new Date();
            const fullTime = now.toLocaleString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, year: 'numeric', month: 'short', day: 'numeric' });
            const compressedTime = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

            state.pnlHistory.push(state.metrics.daily_pnl);
            state.pnlTimestamps.push(compressedTime);
            state.pnlFullTimestamps.push(fullTime);

            // Keep only last 900 data points (~30 minutes at 2s intervals) to prevent memory bloat
            const MAX_HISTORY = 900;
            if (state.pnlHistory.length > MAX_HISTORY) {
                state.pnlHistory.shift();
                state.pnlTimestamps.shift();
                state.pnlFullTimestamps.shift();
            }

            // Update chart if it exists and performance tab is active
            if (pnlChart && !document.getElementById('tab-performance').classList.contains('hidden')) {
                refreshChartData();
            }
        }

        // --- PAPER TRADING SYNC ---
        if (state.executionMode === 'PAPER') {
            try {
                const [pPosRes, pPnlRes, pTradeRes] = await Promise.all([
                    fetch('/paper/positions'),
                    fetch('/paper/pnl'),
                    fetch('/paper/trades')
                ]);

                if (pPosRes.ok) state.paperPositions = (await pPosRes.json()).positions;
                if (pPnlRes.ok) state.paperPnl = (await pPnlRes.json()).pnl;
                if (pTradeRes.ok) state.paperTrades = (await pTradeRes.json()).trades;
            } catch (e) { console.warn("Paper Data Sync Failed", e); }
        }

        // --- HOLDINGS SYNC (REAL/PAPER mode) ---
        if (state.executionMode === 'REAL' || state.executionMode === 'PAPER') {
            fetchHoldings();
        } else {
            renderHoldings(null); // Clear table in non-live modes
        }

        updateDashboardUI();
    } catch (err) { console.error("API Sync Failed", err); }
}

// ---- HOLDINGS PANEL ----

let _holdingsFetchInProgress = false;

async function fetchHoldings() {
    const btn = document.getElementById('btn-holdings-refresh');
    if (_holdingsFetchInProgress) return;
    _holdingsFetchInProgress = true;
    
    if (btn) {
        btn.textContent = '↻ REFRESHING...';
        btn.style.opacity = '0.5';
        btn.style.pointerEvents = 'none';
    }

    try {
        const res = await fetch('/api/v1/account/holdings');
        if (res.ok) {
            const data = await res.json();
            renderHoldings(data);
        }
    } catch (e) {
        console.warn('Holdings fetch failed', e);
    } finally {
        _holdingsFetchInProgress = false;
        if (btn) {
            btn.textContent = '↻ REFRESH';
            btn.style.opacity = '1';
            btn.style.pointerEvents = 'auto';
        }
    }
}

function renderHoldings(data) {
    const tbody = document.getElementById('holdings-table-body');
    const badge = document.getElementById('holdings-mode-badge');
    const investedEl = document.getElementById('hld-invested');
    const currentEl  = document.getElementById('hld-current');
    const pnlEl      = document.getElementById('hld-pnl');
    const pnlDayEl   = document.getElementById('hld-pnl-day');
    if (!tbody) return;

    // Update badge
    if (badge) {
        const mode = data ? data.mode : (state.executionMode || 'MOCK');
        const colors = { REAL: '#ff4757', PAPER: '#ffa502', MOCK: '#747d8c', SIMULATION: '#2ed573' };
        badge.textContent = mode;
        badge.style.background = `${colors[mode] || '#333'}22`;
        badge.style.color = colors[mode] || '#aaa';
    }

    if (!data || !data.holdings || data.holdings.length === 0) {
        const msg = !data || data.mode === 'MOCK' || data.mode === 'SIMULATION'
            ? 'Switch to REAL or PAPER mode to view holdings'
            : 'No holdings / open positions found';
        tbody.innerHTML = `<tr><td colspan="9" class="empty-cell">${msg}</td></tr>`;
        if (investedEl) investedEl.textContent = '₹0';
        if (currentEl)  currentEl.textContent  = '₹0';
        if (pnlEl)      pnlEl.textContent       = '₹0';
        if (pnlDayEl)   pnlDayEl.textContent    = '₹0';
        return;
    }

    const { holdings, summary } = data;

    // Summary bar
    if (investedEl) investedEl.textContent = '₹' + fmtNum(summary.total_invested);
    if (currentEl)  currentEl.textContent  = '₹' + fmtNum(summary.total_current_value);
    if (pnlEl) {
        const p = summary.total_pnl;
        pnlEl.textContent = (p >= 0 ? '+' : '') + '₹' + fmtNum(Math.abs(p)) + ` (${summary.pnl_pct}%)`;
        pnlEl.style.color = p >= 0 ? 'var(--success)' : 'var(--danger)';
    }
    if (pnlDayEl) {
        const pd = summary.total_pnl_day;
        pnlDayEl.textContent = (pd >= 0 ? '+' : '') + '₹' + fmtNum(Math.abs(pd)) + ` (${summary.pnl_day_pct}%)`;
        pnlDayEl.style.color = pd >= 0 ? 'var(--success)' : 'var(--danger)';
    }

    // Rows
    tbody.innerHTML = holdings.map(h => {
        const pnlNetColor = h.pnl >= 0 ? 'var(--success)' : 'var(--danger)';
        const pnlDayColor = h.pnl_day >= 0 ? 'var(--success)' : 'var(--danger)';
        
        const pnlNetSign  = h.pnl >= 0 ? '+' : '';
        const pnlDaySign  = h.pnl_day >= 0 ? '+' : '';
        
        const typeTag  = h.type ? `<span style="font-size:0.5rem;opacity:0.4;display:block;">${h.type}</span>` : '';
        
        return `
        <tr style="transition: background 0.2s;" onmouseenter="this.style.background='rgba(0,243,255,0.04)'" onmouseleave="this.style.background=''">
            <td style="line-height:1.2;">
                <div style="font-weight:700; color:var(--text-main);">${h.symbol}</div>
                ${typeTag}
            </td>
            <td style="font-weight:600;">${h.qty}</td>
            <td style="opacity:0.8;">₹${fmtNum(h.avg_price)}</td>
            <td style="color:var(--accent);">₹${fmtNum(h.ltp)}</td>
            <td style="font-weight:700;">₹${fmtNum(h.current_value)}</td>
            
            <td style="color:${pnlDayColor}; opacity:0.9;">${pnlDaySign}₹${fmtNum(Math.abs(h.pnl_day))}</td>
            <td style="color:${pnlDayColor};">${pnlDaySign}${h.pnl_day_pct}%</td>
            
            <td style="color:${pnlNetColor}; font-weight:800;">${pnlNetSign}₹${fmtNum(Math.abs(h.pnl))}</td>
            <td style="color:${pnlNetColor}; font-weight:700;">${pnlNetSign}${h.pnl_pct}%</td>
        </tr>`;
    }).join('');
}


async function fetchRiskRules() {
    try {
        const res = await fetch('/api/v1/risk/rules');
        if (res.ok) {
            const rules = await res.json();
            document.getElementById('rule-max-trades').textContent = rules.max_trades_per_day;
            document.getElementById('rule-risk-trade').textContent = `${rules.risk_per_trade_percent}%`;
            document.getElementById('rule-max-loss').textContent = `${rules.max_daily_loss_percent}%`;
        }
    } catch (err) { console.error("Risk Rule Sync Failed"); }
}

function handleCapitalChange(val) {
    const customInput = document.getElementById('custom-capital-input');
    if (val === 'custom') {
        customInput.classList.remove('hidden');
    } else {
        customInput.classList.add('hidden');
        applyCapitalPreset(val);
    }
}

async function applyCapitalPreset(amount) {
    try {
        const res = await fetch('/api/v1/settings/capital', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount: parseFloat(amount) })
        });
        if (res.ok) {
            console.log("Capital Allocation Updated:", amount);
            fetchSystemData();
        }
    } catch (err) { console.error("Capital Update Failed"); }
}

// Monitoring Scope Sync
async function updateMonitoringScope() {
    const instruments = ['NIFTY', 'BANKNIFTY', 'SENSEX'];
    if (state.selectedMarket === 'COMMODITY' || state.selectedCommodity) {
        instruments.push(state.selectedCommodity);
    }

    try {
        await fetch('/api/v1/market/monitor', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instruments })
        });
    } catch (e) { console.warn("Monitoring Scope Sync Failed"); }
}

// 1. Market Header & Context Flow Logic
async function updateMarketHeader() {
    if (!state.metrics) return;

    try {
        const r = await fetch(`/api/v1/market/data/${state.selectedMarket}`);
        const response = await r.json();

        const container = document.getElementById('dynamic-price-container');
        if (!container) return;

        if (response.status === 'MARKET_CLOSED') {
            container.innerHTML = `
                <div class="metric-item price-box" style="border: none;">
                    <span class="label">${state.selectedMarket}</span>
                    <span class="val huge" style="font-size: 0.9rem; color: var(--text-dim); opacity: 0.6;">MARKET CLOSED</span>
                </div>
            `;
            return;
        }

        if (response.status === 'DATA_UNAVAILABLE') {
            const warningEl = document.getElementById('system-health-notice');
            if (warningEl) {
                warningEl.classList.remove('hidden');
                warningEl.querySelector('span').textContent = `⚠️ NO LIVE FEED: ${response.reason}`;
            }
            return;
        }

        if (response.status === 'success') {
            // Track commodity live feed status
            if (state.selectedMarket === 'COMMODITY') {
                state.commodityFeedStatus = response.commodity_feed_status || 'DISCONNECTED';
                state.commodityLastUpdate = response.commodity_last_update || null;
            }

            let dataItems = Array.isArray(response.data) ? response.data : [response];

            if (state.selectedMarket === 'COMMODITY') {
                dataItems = dataItems.filter(item => item.instrument === state.selectedCommodity);
            }

            const existingBoxes = container.querySelectorAll('.price-box');
            if (existingBoxes.length !== dataItems.length) {
                container.innerHTML = '';
            }

            dataItems.forEach((item, index) => {
                let box = container.querySelectorAll('.price-box')[index];
                if (!box) {
                    box = document.createElement('div');
                    box.className = 'metric-item price-box';
                    box.innerHTML = `
                        <span class="label"></span>
                        <span class="val huge"></span>
                        <span class="change"></span>
                        <div class="data-pulse"></div>
                    `;
                    container.appendChild(box);
                }

                const labelEl = box.querySelector('.label');
                const ltpEl = box.querySelector('.val');
                const chgEl = box.querySelector('.change');
                let pulse = box.querySelector('.data-pulse');

                const symbol = item.instrument || state.selectedMarket;
                const ltp = (item.ltp === 0 || item.ltp === "0" || item.ltp === undefined) ? null : item.ltp;
                const close = item.close || ltp || 1.0;
                const change = (ltp !== null) ? (ltp - close) : 0;
                const pct = (close > 0 && ltp !== null) ? (change / close * 100).toFixed(2) : "--";
                const itemStatus = item.status || item.data_status || 'LIVE';

                // --- LOADING STATE PROTECTION ---
                if (ltp === null || ltp === undefined || itemStatus === 'LOADING') {
                    ltpEl.innerHTML = '<span class="shimmer-text">LOADING...</span>';
                    chgEl.textContent = "--%";
                    chgEl.style.background = 'rgba(255,255,255,0.05)';
                    labelEl.textContent = symbol;
                    return;
                }

                // --- SMOOTH FLASH EFFECT ---
                const oldLtp = parseFloat(ltpEl.getAttribute('data-last-ltp') || 0);
                if (oldLtp > 0 && ltp !== oldLtp) {
                    const flashClass = ltp > oldLtp ? 'price-flash-up' : 'price-flash-down';
                    box.classList.remove('price-flash-up', 'price-flash-down');
                    void box.offsetWidth; // Trigger reflow
                    box.classList.add(flashClass);
                }
                ltpEl.setAttribute('data-last-ltp', ltp);

                if (itemStatus === 'STALE' || itemStatus === 'MARKET_CLOSED') {
                    ltpEl.classList.add('stale-text');
                    if (pulse) pulse.style.background = 'var(--warning)';
                    labelEl.innerHTML = `${symbol} <span class="badge warning" style="font-size: 0.5rem; vertical-align: middle;">${itemStatus}</span>`;
                } else if (itemStatus === 'VIRTUAL') {
                    ltpEl.classList.remove('stale-text');
                    if (pulse) pulse.style.background = 'var(--accent)';
                    labelEl.innerHTML = `${symbol} <span class="badge" style="font-size: 0.5rem; vertical-align: middle; background: var(--border);">VIRTUAL</span>`;
                } else {
                    ltpEl.classList.remove('stale-text');
                    if (pulse) pulse.style.background = 'var(--success)';

                    // Show live source indicator for commodity data
                    if (state.selectedMarket === 'COMMODITY' && item.data_source && item.data_source !== 'CACHE') {
                        labelEl.innerHTML = `${symbol} <span class="badge success" style="font-size: 0.45rem; vertical-align: middle;">LIVE ${item.data_source}</span>`;
                    } else {
                        labelEl.textContent = symbol;
                    }
                }

                ltpEl.textContent = ltp.toLocaleString('en-IN', { minimumFractionDigits: 2 });
                chgEl.textContent = `${change >= 0 ? '+' : ''}${pct}%`;
                chgEl.style.color = change >= 0 ? 'var(--success)' : 'var(--danger)';
                chgEl.style.background = change >= 0 ? 'rgba(0,255,157,0.1)' : 'rgba(255,62,62,0.1)';
                ltpEl.style.color = change >= 0 ? 'var(--success)' : 'var(--danger)';

                // Show bid/ask/OI for commodity live data
                if (state.selectedMarket === 'COMMODITY' && item.bid && item.ask) {
                    let extraInfo = box.querySelector('.commodity-extra');
                    if (!extraInfo) {
                        extraInfo = document.createElement('div');
                        extraInfo.className = 'commodity-extra';
                        extraInfo.style.cssText = 'font-size: 0.6rem; color: var(--text-dim); margin-top: 2px; display: flex; gap: 8px;';
                        box.appendChild(extraInfo);
                    }
                    const bidAsk = (item.bid > 0 && item.ask > 0)
                        ? `B:${item.bid.toLocaleString('en-IN')} A:${item.ask.toLocaleString('en-IN')}`
                        : '';
                    const oiText = item.open_interest > 0 ? `OI:${item.open_interest.toLocaleString('en-IN')}` : '';
                    if (extraInfo) {
                        extraInfo.textContent = [bidAsk, oiText].filter(Boolean).join(' | ');
                    }
                }

                // --- QUICK EXECUTION SYNC ---
                if (symbol === state.selectedMarket) {
                    const buySub = document.getElementById('buy-ltp-sub');
                    const sellSub = document.getElementById('sell-ltp-sub');
                    const displayLtp = `LTP: ${ltp.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
                    if (buySub) buySub.textContent = displayLtp;
                    if (sellSub) sellSub.textContent = displayLtp;
                }
            });
        }
    } catch (e) {
        console.error("Market Feed Error:", e);
    }
}

// --- CAPITAL MANAGEMENT LOGIC ---
function updateCapitalSettings() {
    const capSelect = document.getElementById('select-total-cap');
    const usedInput = document.getElementById('input-used-cap-limit');

    let newVal = state.metrics ? state.metrics.total_capital : 100000;

    // Total Capital Handling
    if (capSelect.value === 'custom') {
        const customVal = prompt("Enter Custom Capital Amount (₹):", newVal);
        if (customVal !== null && !isNaN(parseFloat(customVal))) {
            newVal = parseFloat(customVal);
        } else {
            // Revert selector if cancelled
            if (state.metrics) {
                const presets = ['50000', '100000', '500000'];
                capSelect.value = presets.includes(state.metrics.total_capital.toString()) ? state.metrics.total_capital.toString() : 'custom';
            }
            return;
        }
    } else {
        newVal = parseFloat(capSelect.value);
    }

    if (state.metrics) {
        state.metrics.total_capital = newVal;
        // PERSISTENCE FIX: Ensure backend is aware of the new capital allocation
        applyCapitalPreset(newVal);
    }

    // Usage Limit Handling
    const limitVal = parseFloat(usedInput.value);
    state.usageLimit = (!isNaN(limitVal) && limitVal > 0) ? limitVal : null;

    updateDashboardUI();
}

async function applyCapitalPreset(amount) {
    try {
        await fetch('/api/v1/settings/capital', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount: amount })
        });
    } catch (e) {
        console.error("Failed to sync capital preset:", e);
    }
}

function updateDashboardUI() {
    const fmtNum = (val, fallback = '—') => {
        if (val === null || val === undefined || isNaN(val) || !isFinite(val)) return fallback;
        return val.toLocaleString('en-IN');
    };
    if (!state.metrics) return;

    // 0. System Health Monitoring
    const healthNotice = document.getElementById('system-health-notice');
    if (healthNotice) {
        if (state.metrics.system_health === 'DEGRADED') {
            healthNotice.classList.remove('hidden');
        } else {
            healthNotice.classList.add('hidden');
        }
    }

    if (state.executionMode) {
        updateExecutionModeUI(state.executionMode, state.dataEngineStatus);
    }

    // 0.2 Update Algo Engine Status
    const algoStatusEl = document.getElementById('header-algo-status');
    const quickAlgoEl = document.getElementById('quick-algo-status');
    if (algoStatusEl) {
        algoStatusEl.textContent = state.isRunning ? 'ACTIVE' : 'OFFLINE';
        algoStatusEl.className = 'val ' + (state.isRunning ? 'success-text' : 'danger-text');
    }
    if (quickAlgoEl) {
        quickAlgoEl.textContent = state.isRunning ? 'ALGO: ACTIVE' : 'ALGO: OFFLINE';
        quickAlgoEl.style.color = state.isRunning ? 'var(--success)' : 'var(--text-dim)';
        quickAlgoEl.style.background = state.isRunning ? 'rgba(0, 200, 110, 0.1)' : 'rgba(255, 255, 255, 0.05)';
    }

    // 1. Top Metrics & Capital Logic
    updateMarketHeader(); // Trigger async header update

    // Bias
    const biasEl = document.getElementById('mkt-bias');
    const labelEl = document.getElementById('mkt-symbol-label');
    if (labelEl) labelEl.textContent = state.selectedMarket;

    if (biasEl) {
        // Use global or selected market bias
        const bias = state.marketBias[state.selectedMarket]?.bias || 'NEUTRAL';
        biasEl.textContent = bias;
        biasEl.className = `val ${bias === 'BULLISH' ? 'success-text' : (bias === 'BEARISH' ? 'danger-text' : 'text-dim')}`;
    }

    // Capital
    const usedActual = state.metrics.used_capital_amount;
    let total = state.metrics.total_capital;
    if (state.executionMode === 'PAPER' && state.paperPnl) {
        total = state.paperPnl.virtual_capital;
    }
    const limit = state.usageLimit;

    // --- REACTION SYNC: Keep Selectors and Inputs aligned with single state source ---
    const topCapSelector = document.getElementById('select-total-cap');
    const settingsCapInput = document.getElementById('set-total-capital');
    if (topCapSelector && document.activeElement !== topCapSelector) {
        let exists = false;
        for (let i = 0; i < topCapSelector.options.length; i++) {
            if (topCapSelector.options[i].value === total.toString()) exists = true;
        }
        if (!exists) {
            const opt = document.createElement('option');
            opt.value = total.toString();
            opt.text = '₹' + fmtNum(total) + (state.executionMode === 'REAL' ? ' (LIVE)' : '');
            topCapSelector.add(opt, topCapSelector.options[1]);
        }
        topCapSelector.value = total.toString();
    }
    if (settingsCapInput && document.activeElement !== settingsCapInput) {
        settingsCapInput.value = total;
    }

    // Logic: If user sets a limit (Allocated), show that as the numerator.
    // User Request: "50000/100000" -> Limit / Total
    const displayNumerator = (limit && limit > 0) ? limit : usedActual;

    const exposureCardValue = document.getElementById('hud-used-cap');
    if (exposureCardValue) {
        exposureCardValue.textContent = `₹${fmtNum(displayNumerator)} / ₹${fmtNum(total)}`;
        const exposureCardLabel = exposureCardValue.previousElementSibling;
        if (exposureCardLabel) {
            exposureCardLabel.textContent = state.executionMode === 'PAPER' ? 'VIRTUAL CAPITAL (USED)' : 'CAPITAL EXPOSURE';
        }
    }

    // Calc Available (Free to allocate)
    const available = total - displayNumerator;
    const availLabel = document.querySelector('#hud-used-cap + .card-sub');
    if (availLabel) availLabel.textContent = `Available: ₹${fmtNum(available)}`;


    // 2. KPI Cards (with NaN protection)
    const dailyPnl = state.metrics.daily_pnl;
    const hudProfit = document.getElementById('hud-profit');
    if (dailyPnl !== null && dailyPnl !== undefined && !isNaN(dailyPnl)) {
        hudProfit.textContent = `₹${fmtNum(dailyPnl)}`;
        hudProfit.className = `card-val ${dailyPnl >= 0 ? 'success-text' : 'danger-text'}`;
    } else {
        hudProfit.textContent = '—';
        hudProfit.className = 'card-val';
    }

    const maxDrawdown = state.metrics.max_drawdown;
    const hudDrawdown = document.getElementById('hud-drawdown');
    if (maxDrawdown !== null && maxDrawdown !== undefined && !isNaN(maxDrawdown)) {
        hudDrawdown.textContent = `₹${fmtNum(Math.abs(maxDrawdown))}`;
    } else {
        hudDrawdown.textContent = '—';
    }

    // Risk Meter (with validation)
    const riskMeter = document.getElementById('hud-risk-meter');
    const riskPercent = state.metrics.risk_used_percent;
    if (riskPercent !== null && riskPercent !== undefined && !isNaN(riskPercent)) {
        riskMeter.textContent = `${fmtNum(riskPercent)}%`;
        riskMeter.className = `card-val ${riskPercent > 80 ? 'danger-text' : ''}`;
    } else {
        riskMeter.textContent = '—';
        riskMeter.className = 'card-val';
    }

    // 2. Agent Intelligence & Explainability
    updateAgentExplainabilityPanel();

    // Filtered trades for context-aware summaries
    const MARKET_SYMBOLS = {
        'NIFTY': ['NIFTY'],
        'BANKNIFTY': ['BANKNIFTY'],
        'SENSEX': ['SENSEX'],
        'COMMODITY': ['CRUDEOIL', 'GOLD', 'SILVER', 'NATGASMINI']
    };

    const relevantSymbols = (state.selectedMarket === 'COMMODITY')
        ? [state.selectedCommodity]
        : (MARKET_SYMBOLS[state.selectedMarket] || [state.selectedMarket]);

    const filteredTrades = state.trades.filter(t => relevantSymbols.some(s => t.instrument.includes(s)));

    // Header PnL & Points Summary (Safe checks for missing elements)
    const marketPnL = filteredTrades.reduce((acc, t) => acc + t.pnl, 0);
    const pnlSumEl = document.getElementById('sys-pnl-summary');
    if (pnlSumEl) {
        pnlSumEl.textContent = `${marketPnL >= 0 ? '+' : ''}₹${marketPnL.toLocaleString()}`;
        pnlSumEl.className = `val ${marketPnL >= 0 ? 'success-text' : 'danger-text'}`;
    }

    const marketPoints = filteredTrades.reduce((acc, t) => {
        const p = (t.current_price - t.entry_price) * (t.direction === 'LONG' ? 1 : -1);
        return acc + p;
    }, 0);
    const pointsSumEl = document.getElementById('sys-points-summary');
    if (pointsSumEl) {
        pointsSumEl.textContent = `${marketPoints >= 0 ? '+' : ''}${marketPoints.toFixed(1)} pts`;
        pointsSumEl.className = `val ${marketPoints >= 0 ? 'success-text' : 'danger-text'}`;
    }

    const marketExposure = filteredTrades.reduce((acc, t) => acc + (t.entry_price * t.quantity), 0);
    const exposureEl = document.getElementById('sys-exposure-summary');
    if (exposureEl) exposureEl.textContent = `₹${marketExposure.toLocaleString()}`;

    // Update Commodity Status Pill
    const commStatusPill = document.getElementById('commodity-status-pill');
    if (commStatusPill) {
        if (state.selectedMarket === 'COMMODITY') {
            commStatusPill.classList.remove('hidden');
            const hasPosition = filteredTrades.length > 0;

            // Show live feed connection status
            const feedStatus = state.commodityFeedStatus || 'DISCONNECTED';
            let pillClass = 'idle';
            let statusLabel = `${state.selectedCommodity}: IDLE`;

            if (feedStatus === 'CONNECTED') {
                pillClass = hasPosition ? 'active' : 'live';
                statusLabel = `${state.selectedCommodity}: ${hasPosition ? 'ACTIVE' : 'LIVE'}`;
            } else if (feedStatus === 'CONNECTING' || feedStatus === 'RECONNECTING') {
                pillClass = 'warning';
                statusLabel = `${state.selectedCommodity}: ${feedStatus}`;
            } else if (hasPosition) {
                pillClass = 'active';
                statusLabel = `${state.selectedCommodity}: ACTIVE`;
            }

            commStatusPill.className = `status-pill ${pillClass}`;
            const statusText = document.getElementById('commodity-status-text');
            if (statusText) statusText.textContent = statusLabel;
        } else {
            commStatusPill.classList.add('hidden');
        }
    }

    const agentContainer = document.getElementById('agents-v2-container');
    if (agentContainer && state.agentV2Status) {
        agentContainer.innerHTML = Object.entries(state.agentV2Status).map(([name, status]) => `
            <div class="status-row">
                <span class="agent-name">${name}</span>
                <span class="agent-badge status-${status.toLowerCase()}">${status}</span>
            </div>
        `).join('');
    }

    // 4. Signal Intelligence Panel
    const lastSignal = [...state.auditTrail].reverse().find(e => e.agent === 'StructurePatternAgent' && e.symbol === state.selectedMarket);
    const lastContext = [...state.auditTrail].reverse().find(e => e.agent === 'MarketContextAgent' && e.symbol === state.selectedMarket);

    if (lastContext) {
        const trendEl = document.getElementById('intel-trend');
        if (trendEl) {
            const mood = lastContext.payload.market_mood;
            trendEl.textContent = mood.toUpperCase();
            trendEl.className = `val ${mood.toLowerCase()}`;
        }
    }

    if (lastSignal) {
        const patEl = document.getElementById('intel-pattern');
        const confEl = document.getElementById('intel-confidence');
        const reasonEl = document.getElementById('intel-reason');

        if (patEl) patEl.textContent = lastSignal.payload.pattern;
        if (confEl) confEl.textContent = `${(lastSignal.confidence * 100).toFixed(0)}%`;

        // Find reason from either context or pattern
        const reason = lastSignal.payload.pattern !== 'None' ? `Detected ${lastSignal.payload.pattern} at ${lastSignal.payload.price_level}` : (lastContext ? lastContext.payload.reason : "");
        if (reasonEl) reasonEl.textContent = reason;
    }

    // 5. ChatGPT Guidance Advisor
    const lastAdvice = [...state.auditTrail].reverse().find(e => e.agent === 'GuidanceAgent');
    const adviceEl = document.getElementById('ai-guidance-text');
    if (adviceEl && lastAdvice) {
        adviceEl.textContent = lastAdvice.payload.advice;
    }

    // 6. Decision Audit Trail
    const auditContainer = document.getElementById('v2-audit-trail');
    if (auditContainer && state.auditTrail.length > 0) {
        const relevantAudit = state.auditTrail.slice(-20).reverse();
        auditContainer.innerHTML = relevantAudit.map(e => {
            let cleanData = e.reason || (e.payload ? (e.payload.advice || e.payload.reason || "Logic processed.") : "Awaiting reason...");
            const stateClass = e.state ? e.state.toLowerCase() : 'neutral';

            return `
                <div class="audit-row state-${stateClass}">
                    <span class="time">${e.timestamp.includes('T') ? e.timestamp.split('T')[1].split('.')[0] : e.timestamp}</span>
                    <span class="agent">${e.agent}</span>
                    <span class="data" title='Decision: ${e.state}\nContext: ${JSON.stringify(e.context || {})}\n\nFull Payload: ${JSON.stringify(e.payload || {})}'>${cleanData}</span>
                    <span class="conf ${(e.confidence || 0) > 85 ? 'high' : ''}">${(e.confidence || 0).toFixed(0)}%</span>
                </div>
            `;
        }).join('');
    }

    // 7. POSITIONS TABLE SYNC
    const posBody = document.getElementById('v3-positions-body');
    if (posBody) {
        let displayTrades = [];
        if (state.executionMode === 'PAPER' && state.paperPositions) {
            displayTrades = state.paperPositions.map(p => ({
                instrument: p.symbol,
                direction: p.side,
                qty: p.qty,
                entry_price: p.entry_price,
                current_price: state.market_data[p.symbol]?.ltp || p.entry_price,
                type: 'PAPER'
            }));
        } else {
            displayTrades = state.trades.filter(t => t.status !== 'CLOSED');
        }

        if (displayTrades.length === 0) {
            posBody.innerHTML = '<tr><td colspan="6" class="empty-cell">NO ACTIVE POSITIONS</td></tr>';
        } else {
            posBody.innerHTML = displayTrades.map(t => {
                const ltp = t.current_price || t.entry_price;
                const pnlPts = (ltp - t.entry_price) * (t.direction === 'BUY' || t.direction === 'LONG' ? 1 : -1);
                const pnlInr = pnlPts * (t.qty || t.quantity || 1);

                return `
                        <tr>
                            <td><span class="symbol-tag">${t.instrument}</span></td>
                            <td><span class="badge ${t.direction === 'BUY' || t.direction === 'LONG' ? 'success' : 'danger'}">${t.direction}</span></td>
                            <td>${t.qty || t.quantity || 0}</td>
                            <td class="mono">₹${fmtNum(t.entry_price)}</td>
                            <td class="mono ${pnlPts >= 0 ? 'success-text' : 'danger-text'}">₹${fmtNum(ltp)}</td>
                            <td class="mono ${pnlPts >= 0 ? 'success-text' : 'danger-text'}">${pnlPts.toFixed(2)}</td>
                        </tr>
                    `;
            }).join('');
        }
    }

    // 8. (PAPER METRICS OVERRIDE REMOVED - Backend is now authoritative)

    // 9. TERMINAL SYNC
    if (state.logs.length > 0) {
        const terminalEl = document.getElementById('v3-terminal');
        if (terminalEl) {
            const latestLogs = state.logs.slice(-20).reverse();
            terminalEl.innerHTML = latestLogs.map(l => `
                    <div class="t-row">
                        <span class="t-time">${l.timestamp.split('T')[1]?.split('.')[0] || ''}</span>
                        <span class="t-msg ${l.message.includes('Order') ? 'trade' : (l.message.includes('REJECTED') ? 'error' : '')}">${l.message}</span>
                    </div>
                `).join('');
        }
    }

    // 10. RECONCILIATION
    const reconBody = document.getElementById('recon-body');
    if (reconBody) {
        let closed = state.trades.filter(t => t.status === 'CLOSED');
        if (state.executionMode === 'PAPER' && state.paperTrades) {
            closed = state.paperTrades;
        }

        if (closed.length === 0) {
            reconBody.innerHTML = '<tr><td colspan="7" class="empty-msg">No closed sessions for today</td></tr>';
        } else {
            reconBody.innerHTML = closed.map(t => `
                    <tr>
                        <td>${t.timestamp?.includes('T') ? t.timestamp.split('T')[1].split('.')[0] : '--'}</td>
                        <td>${t.symbol || t.instrument}</td>
                        <td><span class="badge">${t.side || t.direction}</span></td>
                        <td>${fmtNum(t.entry_price)}</td>
                        <td>${fmtNum(t.exit_price || t.current_price)}</td>
                        <td>${(t.pnl_points || 0).toFixed(2)}</td>
                        <td style="text-align: right;" class="${(t.pnl || 0) >= 0 ? 'success-text' : 'danger-text'}">₹${fmtNum(t.pnl || 0)}</td>
                    </tr>
                `).join('');
        }
    }
}

async function resetPaperEngine() {
    if (!confirm("Are you sure you want to RESET the Paper Trading account?")) return;
    try {
        await fetch('/paper/reset', { method: 'POST' });
        alert("Account Reset Successful.");
        fetchSystemData();
    } catch (e) { console.error(e); }
}

function updateAgentExplainabilityPanel() {
    const container = document.getElementById('agent-explain-grid');
    if (!container || !state.agentV2Status) return;

    const agents = Object.entries(state.agentV2Status);
    container.innerHTML = agents.map(([name, status]) => {
        const meta = agentMetadata[name] || { role: 'Core Agent', description: 'Institutional Processing Unit' };

        // Find last decision for this agent
        const lastEvent = [...state.auditTrail].reverse().find(e => e.agent === name || e.agent.includes(name));
        const timestamp = lastEvent ? (lastEvent.timestamp.includes('T') ? lastEvent.timestamp.split('T')[1].split('.')[0] : lastEvent.timestamp) : '--:--:--';

        let task = lastEvent ? (lastEvent.reason || lastEvent.payload?.reason || lastEvent.payload?.advice || 'Scanning market triggers...') : 'Awaiting data cycle...';

        // Sanitize technical errors in task snapshot
        if (task.includes("insufficient_quota") || task.includes("429")) {
            task = "Awaiting API quota refresh or plan upgrade.";
        }

        const isPaused = status.includes("PAUSED");
        const cardState = lastEvent ? lastEvent.state?.toLowerCase() : 'neutral';

        return `
            <div class="agent-card-interactive" onclick="showAgentDetails('${name}')">
                <div class="card-header">
                    <h4>${name.toUpperCase().replace('AGENT', '')}</h4>
                    <span class="status-pill status-${cardState || 'idle'}">${status}</span>
                </div>
                <div class="context-line">${meta.role}</div>
                <div class="task-snapshot ${isPaused ? 'warning-text' : ''}">${task}</div>
                <div style="font-size: 0.6rem; color: var(--text-dim); margin-top: 12px;">Last Update: ${timestamp} | Conf: ${(lastEvent?.confidence || 0).toFixed(0)}%</div>
            </div>
            `;
    }).join('');

    const v2Container = document.getElementById('agents-v2-container');
    if (v2Container) {
        v2Container.innerHTML = agents.map(([name, status]) => {
            const meta = agentMetadata[name] || { role: 'Core Agent' };
            const lowerStatus = status.toLowerCase();
            let badgeClass = 'warning';
            if (lowerStatus.includes('active') || lowerStatus.includes('monitoring')) badgeClass = 'success';
            if (lowerStatus.includes('blocked') || lowerStatus.includes('offline') || lowerStatus.includes('error')) badgeClass = 'danger';

            return `
                <div class="status-row" onclick="showAgentDetails('${name}')" style="cursor: pointer; transition: background 0.2s;" onmouseover="this.style.background='rgba(0, 243, 255, 0.05)'" onmouseout="this.style.background='transparent'">
                    <div class="agent-icon" style="font-size:1.2rem; color: var(--primary);">🤖</div>
                    <div class="agent-meta" style="flex: 1;">
                        <span class="name">${name.replace('Agent', '').toUpperCase()}</span>
                        <span class="task" style="font-size:0.75rem; color: var(--text-dim); display:block; margin-top:4px;">${meta.role}</span>
                    </div>
                    <span class="agent-badge badge ${badgeClass}">${status}</span>
                </div>
            `;
        }).join('');
    }
}

function toggleAgentDrawer(open) {
    const drawer = document.getElementById('agent-detail-drawer');
    if (drawer) {
        if (open) drawer.classList.add('open');
        else drawer.classList.remove('open');
    }
}

function showAgentDetails(agentName) {
    // Robust key matching
    let meta = agentMetadata[agentName];
    if (!meta) {
        const key = Object.keys(agentMetadata).find(k =>
            k.toLowerCase() === agentName.toLowerCase() ||
            agentName.toLowerCase().includes(k.toLowerCase())
        );
        meta = agentMetadata[key];
    }

    if (!meta) {
        console.warn("Metadata not found for agent:", agentName);
        meta = { role: 'Core Agent', responsibilities: ['Institutional intelligence unit processing market structure logic.'] };
    }

    // Update Header
    document.getElementById('drawer-agent-name').textContent = meta.name || agentName.replace(/Agent$/, '');

    // Update Role & Responsibilities
    const respContainer = document.getElementById('drawer-responsibility');
    if (respContainer) {
        respContainer.innerHTML = `
            <div class="role-subtitle">${meta.role}</div>
            <ul class="resp-list">
                ${(meta.responsibilities || []).map(r => `<li>${r}</li>`).join('')}
            </ul>
        `;
    }

    // Update Telemetry/Metadata
    document.getElementById('drawer-inputs').textContent = (meta.inputs || []).join(', ') || 'Real-time Market Data';
    document.getElementById('drawer-outputs').textContent = (meta.outputs || []).join(', ') || 'Analytical Events & Bias';

    // Dependencies & Risk Impact (New fields)
    const telemetryBox = document.querySelector('.telemetry-box');
    if (telemetryBox) {
        let extraFields = document.getElementById('drawer-extra-meta');
        if (!extraFields) {
            extraFields = document.createElement('div');
            extraFields.id = 'drawer-extra-meta';
            extraFields.style.marginTop = '12px';
            telemetryBox.appendChild(extraFields);
        }
        extraFields.innerHTML = `
            <div class="snapshot-row" style="margin-bottom: 8px;">
                <span class="lbl">Dependencies</span>
                <span class="val" style="font-size: 0.75rem; color: var(--accent);">${(meta.dependencies || []).join(', ') || 'None'}</span>
            </div>
            <div class="snapshot-row">
                <span class="lbl">Risk Impact</span>
                <span class="val" style="font-size: 0.75rem; color: ${meta.risk_impact === 'CRITICAL' ? 'var(--danger)' : 'var(--warning)'}; font-weight: 700;">${meta.risk_impact || 'LOW'}</span>
            </div>
        `;
    }

    // Status Update
    const status = (typeof state.agentV2Status[agentName] === 'object' ? state.agentV2Status[agentName].status : state.agentV2Status[agentName]) || 'IDLE';
    const statusTag = document.getElementById('drawer-agent-status-tag');
    statusTag.textContent = status;
    statusTag.className = `status-pill status-${status.toLowerCase()}`;

    // Find last event for decisions
    const lastEvent = [...state.auditTrail].reverse().find(e => e.agent === agentName || e.agent.includes(agentName) || (meta.name && (e.agent === meta.name || e.agent.includes(meta.name))));

    if (lastEvent) {
        document.getElementById('drawer-current-task').textContent = lastEvent.reason || lastEvent.payload?.reason || lastEvent.payload?.advice || 'Actively monitoring market triggers.';

        // Snapshot
        const payload = lastEvent.payload || {};
        const eventState = lastEvent.state || 'NEUTRAL';

        document.getElementById('snapshot-signal').textContent = eventState;
        document.getElementById('snapshot-reason').textContent = lastEvent.reason || payload.reason || payload.advice || 'Confluence scan completed.';

        // Confidence
        const confText = document.getElementById('snapshot-conf');
        if (confText) {
            confText.textContent = `${(lastEvent.confidence || 0).toFixed(0)}%`;
        } else {
            const decBox = document.querySelector('.decision-snapshot');
            const confRow = document.createElement('div');
            confRow.className = 'snapshot-row';
            confRow.innerHTML = `<span class="lbl">Confidence</span><span class="val" id="snapshot-conf">${(lastEvent.confidence || 0).toFixed(0)}%</span>`;
            decBox.appendChild(confRow);
        }

        document.getElementById('snapshot-time').textContent = lastEvent.timestamp.includes('T') ? lastEvent.timestamp.split('T')[1].split('.')[0] : lastEvent.timestamp;
    } else {
        document.getElementById('drawer-current-task').textContent = 'Waiting for next market execution cycle.';
        document.getElementById('snapshot-signal').textContent = '--';
        document.getElementById('snapshot-reason').textContent = 'N/A';
        document.getElementById('snapshot-time').textContent = '--:--:--';
        if (document.getElementById('snapshot-conf')) document.getElementById('snapshot-conf').textContent = '0%';
    }

    toggleAgentDrawer(true);
}

async function requestAiAdvice() {
    const adviceEl = document.getElementById('ai-guidance-text');
    if (!adviceEl) return;

    const originalText = adviceEl.textContent;
    adviceEl.textContent = "🧠 AI is analyzing institutional context... please wait.";
    adviceEl.style.opacity = "0.7";

    try {
        const res = await fetch('/api/v1/agents/guidance/on-demand', { method: 'POST' });
        const data = await res.json();

        if (data.status === 'success') {
            adviceEl.textContent = data.advice;
            adviceEl.style.opacity = "1";
        } else {
            adviceEl.textContent = "Strategic Link Failure. Try again.";
            adviceEl.style.opacity = "1";
        }
    } catch (err) {
        adviceEl.textContent = "Signal Interference. Check backend connection.";
        adviceEl.style.opacity = "1";
    }
}

function navigateToMarketDetail(symbol) {
    const sym = symbol || state.selectedMarket;
    const titleEl = document.getElementById('detail-market-title');
    if (titleEl) titleEl.innerHTML = `${sym} <span style="font-weight: 300; opacity: 0.5;">FUTURES</span>`;

    // Dynamic Specs
    const lotSizes = { 'NIFTY': '50', 'BANKNIFTY': '25', 'COMMODITY': '100', 'SENSEX': '10' };
    const lotEl = document.getElementById('detail-lot-size');
    if (lotEl) lotEl.textContent = `${lotSizes[sym] || '50'} units(1x)`;

    showTab(null, 'market-detail');

    // Initialize Deep Analytics Chart
    initOhlcChart(sym, state.deepTimeframe);
}

function navigateToAgentDetail(name) {
    const titleEl = document.getElementById('detail-agent-title');
    if (titleEl) titleEl.innerHTML = `${name.toUpperCase()} <span style="font-weight: 300; opacity: 0.5;">CORE LOGIC</span>`;
    showTab(null, 'agent-detail');
}

// --- SYSTEM CONTROLS ---
function setExecutionMode(mode) {
    // 1. Update UI (Scoped to settings toggle only)
    const settingsGrid = document.querySelector('#tab-settings .mode-toggles');
    if (settingsGrid) {
        settingsGrid.querySelectorAll('.mode-option').forEach(el => el.classList.remove('selected'));
    }

    const target = document.getElementById(mode === 'AUTO' ? 'mode-auto' : 'mode-manual');
    if (target) target.classList.add('selected');

    console.log(`Execution Preference Switched to: ${mode} `);
    // Optional: await fetch('/api/v1/settings/pref-mode', ... ); 
}

async function controlSystem(action) {
    if (action === 'reset') {
        if (!confirm("⚠️ SYSTEM RESET\n\nThis will clear strictly local session logs and chart history. Continue?")) return;
        // Mock Reset
        state.logs = [];
        state.pnlHistory = [];
        // fetchSystemData() will effectively reload state
        alert("Session Reset Initiated.");
        window.location.reload();
        return;
    }

    const route = action === 'start' ? 'system/start' :
        (action === 'square_off_all' ? 'system/square_off_all' : 'system/pause');

    await fetch(`/api/v1/${route}`, { method: 'POST' });
    fetchSystemData();
}


function getComputedColor(varName) {
    return getComputedStyle(document.body).getPropertyValue(varName).trim();
}

async function updateDeepTimeframe(tf) {
    state.deepTimeframe = tf;
    document.querySelectorAll('#tab-market-detail .time-range-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tf === tf);
    });

    const sym = document.getElementById('detail-market-title').textContent.split(' ')[0];
    initOhlcChart(sym, tf);
}

async function initOhlcChart(symbol, timeframe) {
    const canvas = document.getElementById('ohlcChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    if (state.ohlcChart) state.ohlcChart.destroy();

    try {
        const res = await fetch(`/api/v1/market/history/${symbol}?timeframe=${timeframe}`);
        const data = await res.json();

        if (data.status !== 'success') {
            console.error("Failed to fetch OHLC history");
            return;
        }

        const ohlc = data.ohlc;
        const patterns = data.patterns;

        const labels = ohlc.map(c => {
            const date = new Date(c.timestamp);
            return timeframe.endsWith('d') ? date.toLocaleDateString() : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        });

        // Map colors for candles
        const colors = ohlc.map(c => c.close >= c.open ? getComputedColor('--success') : getComputedColor('--danger'));

        state.ohlcChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Wicks',
                        data: ohlc.map(c => [c.low, c.high]),
                        backgroundColor: colors,
                        borderColor: colors,
                        borderWidth: 1,
                        barThickness: 2,
                        order: 2
                    },
                    {
                        label: 'Real Body',
                        data: ohlc.map(c => [Math.min(c.open, c.close), Math.max(c.open, c.close)]),
                        backgroundColor: colors,
                        borderColor: colors,
                        borderWidth: 1,
                        barPercentage: 0.8,
                        order: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        left: 10,
                        right: 10,
                        top: 20,
                        bottom: 10
                    }
                },
                scales: {
                    x: { stacked: true, grid: { display: false }, ticks: { color: getComputedColor('--text-dim'), font: { size: 10 } } },
                    y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: getComputedColor('--text-dim'), font: { size: 10 } } }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const idx = ctx.dataIndex;
                                const c = ohlc[idx];
                                return [`O: ${c.open}`, `H: ${c.high}`, `L: ${c.low}`, `C: ${c.close}`];
                            }
                        }
                    }
                }
            },
            plugins: [{
                id: 'patternOverlay',
                afterDraw: (chart) => {
                    const ctx = chart.ctx;
                    patterns.forEach(p => {
                        const meta = chart.getDatasetMeta(1);
                        const element = meta.data[p.index];
                        if (!element) return;

                        const { x, y } = element;
                        ctx.save();
                        ctx.fillStyle = getComputedColor('--accent');
                        ctx.font = 'bold 10px Outfit';
                        ctx.textAlign = 'center';
                        ctx.fillText(p.type, x, y - 15);

                        // Draw a small indicator circle
                        ctx.beginPath();
                        ctx.arc(x, y - 5, 3, 0, 2 * Math.PI);
                        ctx.fill();
                        ctx.restore();
                    });
                }
            }]
        });

    } catch (err) {
        console.error("Deep Analytics Engine Error:", err);
    }
}

function initAnalytics() {
    const ctx = document.getElementById('pnlChart').getContext('2d');
    if (pnlChart) pnlChart.destroy();

    const { labels, data, fullTimestamps } = getFilteredChartData();

    // Theme Colors
    const primary = getComputedColor('--primary');
    const textDim = getComputedColor('--text-dim');
    const border = getComputedColor('--border');
    const glow = getComputedColor('--primary-glow');

    // Adjust colors for background/grid based on theme state
    const isLight = state.theme === 'light';
    const gridColor = isLight ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)';
    const tooltipBg = isLight ? 'rgba(255,255,255,0.95)' : 'rgba(10, 14, 26, 0.95)';
    const tooltipText = isLight ? '#000' : '#fff';

    pnlChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels.length > 0 ? labels : ['Awaiting data...'],
            datasets: [{
                label: 'Intraday PnL (₹)',
                data: data,
                borderColor: primary,
                backgroundColor: glow, // Uses the variable now
                borderWidth: 2,
                tension: 0.3,
                fill: true,
                pointRadius: (context) => (labels.length > 100 ? 0 : 3), // Hide points if too many
                pointHoverRadius: 6,
                pointBackgroundColor: primary,
                pointBorderColor: isLight ? '#fff' : '#000',
                pointBorderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 400 },
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: true,
                    backgroundColor: tooltipBg,
                    titleColor: primary,
                    bodyColor: tooltipText,
                    borderColor: primary,
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        title: (context) => fullTimestamps[context[0].dataIndex] || 'N/A',
                        label: (context) => `PnL: ₹${context.parsed.y.toLocaleString()} `
                    }
                }
            },
            scales: {
                y: {
                    grid: { color: gridColor },
                    ticks: {
                        color: textDim,
                        font: { size: 10 },
                        callback: (value) => '₹' + value.toLocaleString()
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: {
                        color: textDim,
                        font: { size: 10 },
                        maxRotation: 0,
                        minRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 12
                    }
                }
            }
        }
    });

    updateChartContainerWidth(labels.length);
}

function updateChartContainerWidth(pointCount) {
    const container = document.querySelector('.chart-canvas-container');
    const wrapper = document.querySelector('.chart-scroll-wrapper');
    if (!container || !wrapper) return;

    const minWidthPerPoint = 15; // px per data point
    const minTotalWidth = wrapper.clientWidth;
    const calculatedWidth = pointCount * minWidthPerPoint;

    if (calculatedWidth > minTotalWidth) {
        container.style.width = calculatedWidth + 'px';
        // Auto-scroll to end on new data
        if (state.chartTimeRange === '1D') {
            wrapper.scrollLeft = calculatedWidth;
        }
    } else {
        container.style.width = '100%';
    }
}


async function saveInstitutionalSettings() {
    const config = {
        total_capital: parseFloat(document.getElementById('set-total-capital').value),
        max_daily_loss_percent: parseFloat(document.getElementById('set-max-loss').value),
        risk_per_trade_percent: parseFloat(document.getElementById('set-risk-trade').value),
        max_trades_per_day: parseInt(document.getElementById('set-max-trades').value)
    };

    try {
        const res = await fetch('/api/v1/settings/risk', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        if (res.ok) {
            alert("Strategic Risk Protocols Updated Successfully");
            fetchSystemData();
        } else {
            const errData = await res.json();
            alert("Risk Protocol Rejection: " + (errData.detail || "Invalid Parameters"));
        }
    } catch (err) {
        alert("Global Command Center: Connectivity Failure");
    }
}

// --- ADMIN USER MANAGEMENT FLOW ---

function openAddUserModal() {
    document.getElementById('add-user-modal').classList.remove('hidden');
}

function closeAddUserModal() {
    document.getElementById('add-user-modal').classList.add('hidden');
    // Clear potentially sensitive inputs immediately
    document.getElementById('add-user-id').value = '';
    document.getElementById('add-user-pass').value = '';
    document.getElementById('add-user-api').value = '';
    document.getElementById('add-user-secret').value = '';
    const brokerEl = document.getElementById('add-user-broker');
    if (brokerEl) brokerEl.value = 'ALICE_BLUE';
}

async function submitAddUser() {
    const userId = document.getElementById('add-user-id').value;
    const password = document.getElementById('add-user-pass').value;
    const apiKey = document.getElementById('add-user-api').value;
    const secretKey = document.getElementById('add-user-secret').value;
    const brokerEl = document.getElementById('add-user-broker');
    const broker = brokerEl ? brokerEl.value : 'ALICE_BLUE';

    if (!userId || !password || !apiKey || !secretKey) {
        alert("Validation Error: All credential fields are mandatory for secure onboarding.");
        return;
    }

    try {
        const response = await fetch('/api/v1/admin/users/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                password: password,
                api_key: apiKey,
                secret_key: secretKey,
                broker: broker
            })
        });

        if (response.ok) {
            alert(`Secure Handshake Successful: User onboarded on ${broker}.`);
            closeAddUserModal();
            fetchManagedUsers();
        } else {
            const err = await response.json();
            alert("Onboarding Rejected: " + (err.detail || "Invalid Credentials"));
        }
    } catch (err) {
        alert("Connectivity Error: Failed to establish secure handshake with auth server.");
    }
}

async function fetchManagedUsers() {
    try {
        const res = await fetch('/api/v1/admin/users/list');
        const data = await res.json();
        if (data.status === 'success') {
            updateTradersTable(data.users);
        }
    } catch (err) {
        console.error("Admin Console: Failed to sync managed entities");
    }
}

function updateTradersTable(users) {
    const tbody = document.getElementById('admin-traders-body');
    if (!tbody) return;

    tbody.innerHTML = users.map(user => {
        const statusClass = user.status === 'ACTIVE' || user.status === 'CONNECTED' ? 'success-text' : 'danger-text';
        const broker = user.broker || 'ALICE_BLUE';
        const brokerBadgeClass = broker === 'ALICE_BLUE' ? 'accent-text' : 'warning-text';
        return `
            <tr>
                <td>${user.user_id}</td>
                <td><span class="accent-text">${user.role}</span></td>
                <td><span class="${brokerBadgeClass}">${broker.replace('_', ' ')}</span></td>
                <td><span class="${statusClass}">${user.status}</span></td>
                <td style="text-align: right; cursor: pointer;">⚙️</td>
            </tr>
            `;
    }).join('');
}



function setUsageLimit(val) {
    if (!val) return;
    state.usageLimit = parseFloat(val);
    alert(`Deployment Limit Set: ₹${state.usageLimit.toLocaleString()} `);
    updateDashboardUI();
}

// --- CHART TIME RANGE FILTERING ---
function setChartTimeRange(range) {
    state.chartTimeRange = range;
    document.querySelectorAll('.time-range-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-range="${range}"]`).classList.add('active');
    if (pnlChart) refreshChartData();
}

function refreshChart() {
    if (pnlChart) refreshChartData();
}
function refreshChartData() {
    const { labels, data, fullTimestamps } = getFilteredChartData();
    pnlChart.data.labels = labels;
    pnlChart.data.datasets[0].data = data;
    pnlChart.options.plugins.tooltip.callbacks.title = (context) => fullTimestamps[context[0].dataIndex] || '';
    pnlChart.update('none'); // Update without animation for smoother live feed
    updateChartContainerWidth(labels.length);
}

function getFilteredChartData() {
    const rangeConfig = {
        '1D': { points: 500, step: 1 },
        '5D': { points: 1500, step: 2 },
        '1M': { points: 3000, step: 5 },
        '3M': { points: 5000, step: 10 },
        '6M': { points: 8000, step: 20 },
        '1Y': { points: 12000, step: 50 }
    };

    const cfg = rangeConfig[state.chartTimeRange] || rangeConfig['1D'];
    const limit = cfg.points;
    const step = cfg.step;

    let history = state.pnlHistory;
    let timestamps = state.pnlTimestamps;
    let fullTs = state.pnlFullTimestamps;

    // Simulate historical data if history is too short for long ranges
    if (history.length < 50 && state.chartTimeRange !== '1D') {
        return mockHistoricalData(state.chartTimeRange);
    }

    const startIdx = Math.max(0, history.length - limit);
    let slicedData = history.slice(startIdx);
    let slicedTimestamps = timestamps.slice(startIdx);
    let slicedFullTimestamps = fullTs.slice(startIdx);

    // Apply Downsampling (Dynamic Compression)
    if (step > 1) {
        slicedData = slicedData.filter((_, i) => i % step === 0);
        slicedTimestamps = slicedTimestamps.filter((_, i) => i % step === 0);
        slicedFullTimestamps = slicedFullTimestamps.filter((_, i) => i % step === 0);
    }

    return { labels: slicedTimestamps, data: slicedData, fullTimestamps: slicedFullTimestamps };
}

function mockHistoricalData(range) {
    // Generate some fake data to show the layout even with no history
    const pointsCount = 100;
    const data = [];
    const labels = [];
    const fullTs = [];
    let base = 500;
    const now = new Date();

    for (let i = 0; i < pointsCount; i++) {
        base += (Math.random() - 0.45) * 50;
        data.push(base);
        const d = new Date(now.getTime() - (pointsCount - i) * 3600000); // 1h intervals
        labels.push(d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
        fullTs.push(d.toLocaleString());
    }
    return { labels, data, fullTimestamps: fullTs };
}

// --- DYNAMIC PATTERN DETECTION ---
function updateDetectedPatterns(market) {
    const patterns = MARKET_PATTERNS[market] || [];
    const container = document.getElementById('detected-patterns');
    if (!container) return;
    if (patterns.length === 0) {
        container.innerHTML = `<div class="empty-msg">No active patterns detected for ${market}</div>`;
        return;
    }
    container.innerHTML = patterns.map(p => `<div class="pattern-card" data-direction="${p.direction}">
            <div class="pattern-header">
                <span class="pattern-name">${p.name}</span>
                <span class="pattern-direction ${p.direction.toLowerCase()}">${p.direction}</span>
            </div>
            <div class="pattern-meta">
                <span class="confidence">${p.confidence}</span>
                <span class="time-detected">Detected at ${p.time} IST</span>
            </div>
            <button class="auth-link" style="font-size: 0.6rem; margin-top: 8px; justify-content: flex-end;" onclick="navigateToAgentDetail('Market Context')">VIEW REASONING →</button>
        </div> `).join('');
}

// --- SCROLL SHADOW EFFECT ---
function initScrollShadow() {
    const mainContent = document.querySelector('.main-content-v2');
    const header = document.querySelector('.market-selector');
    if (!mainContent || !header) return;
    mainContent.addEventListener('scroll', () => {
        if (mainContent.scrollTop > 10) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    });
}

// --- DEFAULT MARKET PREFERENCE HANDLER ---
function updateDefaultMarket() {
    const dropdown = document.getElementById('default-market-select');
    if (!dropdown) return;

    const newMarket = dropdown.value;

    // Update state
    state.selectedMarket = newMarket;

    // Update active tab visually
    document.querySelectorAll('.market-tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.dataset.market === newMarket) {
            tab.classList.add('active');
        }
    });

    // Refresh dashboard UI with new market
    updateDetectedPatterns(newMarket);
    updateDashboardUI();

    // Automatically switch to Main Dashboard to show the change
    showTab(null, 'dashboard');

    // Update the active nav button
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.includes('Main Dashboard')) {
            btn.classList.add('active');
        }
    });

    // User feedback
    alert(`✓ Default market changed to ${newMarket} \nDashboard updated and refreshed!`);

    console.log(`✓ Default market updated to: ${newMarket}. Dashboard refreshed.`);
}

// --- EXECUTION MODE LOGIC ---

function openModeSelectionModal() {
    const modal = document.getElementById('mode-layer');
    if (modal) modal.classList.remove('hidden');
}

function closeModeModal() {
    const modal = document.getElementById('mode-layer');
    if (modal) modal.classList.add('hidden');
}

let isSwitchingMode = false;

async function confirmModeSwitch(mode) {
    if (isSwitchingMode) {
        alert("Mode change unavailable at this time (Operation in progress)");
        return;
    }

    // Safety check for REAL mode
    if (mode === 'REAL') {
        const confirmed = confirm("⚠️ CRITICAL WARNING: You are about to enable REAL TRADING with live capital.\n\nAre you absolutely sure you want to proceed?");
        if (!confirmed) return;
    }

    isSwitchingMode = true;

    // Immediate UI feedback for selection
    const modalGrid = document.querySelector('#mode-layer .mode-grid');
    if (modalGrid) {
        modalGrid.querySelectorAll('.mode-option').forEach(opt => opt.classList.remove('selected'));
        const activeOpt = document.getElementById(`mode-sel-${mode.toLowerCase()}`);
        if (activeOpt) activeOpt.classList.add('selected');
    }

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

        const res = await fetch('/api/v1/system/mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: mode }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        // Check if response is ok
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({ detail: `HTTP ${res.status} ` }));
            throw new Error(errorData.detail || `Server error: ${res.status} `);
        }

        const data = await res.json();

        if (data.status === 'success') {
            // Update UI immediately with data status
            updateExecutionModeUI(data.mode, data.data_status);
            closeModeModal();

            // Log mode change with timestamp
            console.log(`[MODE SWITCH] ${new Date().toISOString()} - Changed to ${data.mode} `);

            // Show data connection status for Paper/Real modes
            if (mode === 'PAPER' || mode === 'REAL') {
                // Check data connection status after a brief delay
                setTimeout(() => {
                    const dataStatus = state.market_data && Object.keys(state.market_data).length > 0
                        ? 'Connected' : 'Connecting...';
                    console.log(`[DATA STATUS] Market data: ${dataStatus} `);
                }, 1000);
            }

            // Refresh system data
            fetchSystemData();
        } else {
            // Server returned success:false with a reason
            const reason = data.detail || data.message || "Unknown error";
            alert(`Mode switch blocked: ${reason} `);
        }
    } catch (e) {
        console.error("[MODE SWITCH ERROR]", e);

        // Provide specific error messages
        let errorMessage = "Could not switch execution mode.";

        if (e.name === 'AbortError') {
            errorMessage = "Request timed out. Server took too long to respond.";
        } else if (e.message.includes('Failed to fetch') || e.message.includes('NetworkError')) {
            errorMessage = "Connection error: Could not reach the server. Please check if the server is running.";
        } else if (e.message.includes('JSON')) {
            errorMessage = "Server response error: Invalid data format received.";
        } else if (e.message) {
            errorMessage = `Mode switch error: ${e.message} `;
        }

        alert(errorMessage);
    } finally {
        isSwitchingMode = false;
    }
}

function handleHeaderModeChange() {
    const mode = document.getElementById('header-execution-mode-select').value;
    confirmModeSwitch(mode);
}

function updateExecutionModeUI(mode, dataStatus) {
    state.executionMode = mode;
    const btn = document.getElementById('broker-mode-sidebar');
    const label = document.getElementById('broker-mode-label');
    const headerModeSelect = document.getElementById('header-execution-mode-select');
    const headerData = document.getElementById('header-data-status');
    const simBadge = document.querySelector('.simulation-mode-badge');

    if (btn) {
        btn.textContent = mode + " MODE";
        btn.className = 'status-badge'; // Reset base
    }

    if (label) {
        label.textContent = `${mode} EXECUTION`;
        label.className = 'badge'; // Reset base
    }

    if (headerModeSelect) {
        headerModeSelect.value = mode;
        headerModeSelect.className = 'val ' + (mode === 'REAL' ? 'danger-text' : (mode === 'MOCK' ? 'accent-text' : 'warning-text'));
    }

    // Modal Option Highlighting
    const modalGrid = document.querySelector('#mode-layer .mode-grid');
    if (modalGrid) {
        modalGrid.querySelectorAll('.mode-option').forEach(opt => opt.classList.remove('selected'));
        const modalOpt = document.getElementById(`mode-sel-${mode.toLowerCase()}`);
        if (modalOpt) modalOpt.classList.add('selected');
    }

    if (mode === 'MOCK') {
        if (btn) btn.classList.add('warning');
        if (label) label.classList.add('warning');
        if (simBadge) simBadge.style.display = 'none';
        if (headerData) {
            headerData.textContent = "INTERNAL FEED";
            headerData.className = "val accent-text";
        }
    } else if (mode === 'SIMULATION') {
        if (btn) {
            btn.classList.add('active');
            btn.style.background = 'rgba(0, 243, 255, 0.1)';
            btn.style.color = 'var(--accent)';
            btn.style.border = '1px solid var(--accent)';
        }
        if (label) label.classList.add('warning');
        if (simBadge) {
            simBadge.style.display = 'block';
            simBadge.textContent = "SIMULATION ACTIVE";
        }
        if (headerData) {
            headerData.textContent = "HISTORICAL REPLAY";
            headerData.className = "val warning-text";
        }
    } else if (mode === 'PAPER' || mode === 'REAL') {
        const isReal = mode === 'REAL';
        if (btn) {
            btn.className = 'status-badge ' + (isReal ? 'danger pulse-animation' : 'warning');
            btn.textContent = isReal ? "🔴 LIVE TRADING" : "PAPER TRADING";
            if (isReal) {
                btn.style.background = 'rgba(255, 62, 62, 0.1)';
                btn.style.color = 'var(--danger)';
                btn.style.border = '1px solid var(--danger)';
            } else {
                btn.style.background = 'rgba(255, 193, 7, 0.1)';
                btn.style.color = 'var(--warning)';
                btn.style.border = '1px solid var(--warning)';
            }
        }
        if (label) label.className = 'badge ' + (isReal ? 'success' : 'warning');
        if (simBadge) {
            simBadge.style.display = 'block';
            simBadge.textContent = isReal ? "⚠️ LIVE TRADING ACTIVE ⚠️" : "PAPER MODE - VIRTUAL EXECUTION";
            simBadge.style.background = isReal ? 'linear-gradient(135deg, #FF2D55 0%, #DC143C 100%)' : 'linear-gradient(135deg, #FFB800 0%, #FF8C00 100%)';
        }
        if (headerData) {
            const displayStatus = state.marketFeedStatus || dataStatus || 'LIVE DATA';
            headerData.textContent = displayStatus;
            headerData.className = "val " + (displayStatus === 'CONNECTED' ? 'success-text' : (displayStatus === 'CONNECTING' || displayStatus === 'RECONNECTING' ? 'warning-text' : 'danger-text'));
        }
    }

    // Update state for reference
    if (state.metrics) {
        state.metrics.execution_mode = mode;
    }

    // Log data status if provided
    if (dataStatus) {
        console.log(`[DATA CONNECTION] ${dataStatus}`);
    }
}

// Initialize default market dropdown on load
window.addEventListener('load', () => {
    const dropdown = document.getElementById('default-market-select');
    if (dropdown) {
        dropdown.value = state.selectedMarket;
    }
});

// --- UNIVERSAL SYMBOL SEARCH ---
let searchDebounce = null;
let searchSelectedIdx = -1;

function initSymbolSearch() {
    const searchInput = document.getElementById('symbol-search-input');
    const resultsDropdown = document.getElementById('search-results-dropdown');
    const loadingSpinner = document.getElementById('search-loading-spinner');

    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        clearTimeout(searchDebounce);

        if (query.length < 2) {
            resultsDropdown.classList.add('hidden');
            return;
        }

        searchDebounce = setTimeout(async () => {
            if (loadingSpinner) loadingSpinner.classList.remove('hidden');
            try {
                const res = await fetch(`/api/v1/market/search?q=${encodeURIComponent(query)}`);
                const data = await res.json();

                if (data.status === 'success') {
                    renderSearchResults(data.results);
                }
            } catch (err) {
                console.error("Search failed:", err);
            } finally {
                if (loadingSpinner) loadingSpinner.classList.add('hidden');
            }
        }, 300);
    });

    // Close dropdown on click outside
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !resultsDropdown.contains(e.target)) {
            resultsDropdown.classList.add('hidden');
        }
    });

    // Keyboard navigation
    searchInput.addEventListener('keydown', (e) => {
        if (resultsDropdown.classList.contains('hidden')) return;

        const items = resultsDropdown.querySelectorAll('.search-result-item');
        if (e.key === 'ArrowDown') {
            searchSelectedIdx = (searchSelectedIdx + 1) % items.length;
            updateSearchSelection(items);
            e.preventDefault();
        } else if (e.key === 'ArrowUp') {
            searchSelectedIdx = (searchSelectedIdx - 1 + items.length) % items.length;
            updateSearchSelection(items);
            e.preventDefault();
        } else if (e.key === 'Enter' && searchSelectedIdx > -1) {
            items[searchSelectedIdx].click();
            e.preventDefault();
        }
    });
}

function renderSearchResults(results) {
    const dropdown = document.getElementById('search-results-dropdown');
    if (!dropdown) return;

    if (results.length === 0) {
        dropdown.innerHTML = '<div style="padding: 12px; color: var(--text-dim); font-size: 0.8rem;">No results found</div>';
    } else {
        dropdown.innerHTML = results.map((item, idx) => `
            <div class="search-result-item" onclick="handleSymbolSelection('${item.symbol}', '${item.exch}')">
                <div class="result-main">
                    <span class="result-symbol">${item.symbol}</span>
                    <span class="result-name">${item.name}</span>
                </div>
                <div class="result-meta">
                    <span class="type-badge">${item.type || 'EQ'}</span>
                    <span class="exch-badge ${item.exch ? item.exch.toLowerCase() : 'nse'}">${item.exch || 'NSE'}</span>
                </div>
            </div>
            `).join('');
    }

    dropdown.classList.remove('hidden');
    searchSelectedIdx = -1;
}

function updateSearchSelection(items) {
    items.forEach((item, idx) => {
        if (idx === searchSelectedIdx) {
            item.classList.add('selected');
            item.scrollIntoView({ block: 'nearest' });
        } else {
            item.classList.remove('selected');
        }
    });
}

async function handleSymbolSelection(symbol, exchange) {
    console.log(`Selecting symbol: ${symbol} (${exchange})`);

    // UI Update immediate
    const searchInput = document.getElementById('symbol-search-input');
    const dropdown = document.getElementById('search-results-dropdown');
    if (searchInput) searchInput.value = symbol;
    if (dropdown) dropdown.classList.add('hidden');

    try {
        const res = await fetch('/api/v1/market/select', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, exchange })
        });

        const data = await res.json();
        if (data.status === 'success') {
            state.selectedMarket = symbol;

            // Remove active class from hardcoded tabs
            document.querySelectorAll('.market-tab').forEach(t => t.classList.remove('active'));

            // Toggle Commodity selector
            const commWrapper = document.getElementById('commodity-selector-wrapper');
            if (commWrapper) commWrapper.classList.add('hidden');

            // Re-sync and update
            updateMarketHeader();
            updateDetectedPatterns(symbol);

            console.log(`Successfully switched to ${symbol} `);
        }
    } catch (err) {
        console.error("Selection failed:", err);
    }
}

// --- QUICK EXECUTION LOGIC ---
async function executeManualTrade(side) {
    const symbol = state.selectedMarket;
    const type = document.getElementById('manual-order-type').value;
    const qty = parseInt(document.getElementById('manual-order-qty').value);
    const price = parseFloat(document.getElementById('manual-order-price').value);
    const statusMsg = document.getElementById('manual-order-status');

    if (isNaN(qty) || qty <= 0) {
        alert("Please enter a valid quantity.");
        return;
    }

    if (type === 'LIMIT' && (isNaN(price) || price <= 0)) {
        alert("Please enter a valid limit price.");
        return;
    }

    // Visual feedback for placing order
    if (statusMsg) {
        statusMsg.textContent = `Dispatching ${side} ${qty} for ${symbol}...`;
        statusMsg.className = "order-status-msg active";
    }

    try {
        const res = await fetch('/api/v1/order/manual', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: symbol,
                side: side,
                qty: qty,
                type: type,
                price: price
            })
        });

        const data = await res.json();

        if (data.status === 'success') {
            if (statusMsg) {
                statusMsg.textContent = `✓ ${side} Order Filled: ${symbol} @ ${qty} units.`;
                statusMsg.className = "order-status-msg success-text";
            }
            // Trigger feedback sound or visual cue if desired
            console.log("Manual Trade Success:", data.result);

            // Refresh trades list
            if (typeof fetchSystemData === 'function') {
                setTimeout(() => fetchSystemData(), 500);
            }
        } else {
            throw new Error(data.detail || "Execution failed");
        }
    } catch (err) {
        if (statusMsg) {
            statusMsg.textContent = `✕ Error: ${err.message}`;
            statusMsg.className = "order-status-msg danger-text";
        }
        console.error("Manual Trade Error:", err);
    }
}

/* ============================================================
   ADMIN OVERSIGHT DASHBOARD
   Auto-refreshes every 5 s when the admin tab is visible.
   ============================================================ */

let _adminPnlChart = null;
let _adminPollTimer = null;

/** Called by showTab() when the admin tab becomes active */
function initAdminDashboard() {
    fetchAdminOverview();
    if (!_adminPollTimer) {
        _adminPollTimer = setInterval(fetchAdminOverview, 5000);
    }
}

/** Called by showTab() when leaving the admin tab */
function destroyAdminDashboard() {
    clearInterval(_adminPollTimer);
    _adminPollTimer = null;
}

async function fetchAdminOverview() {
    try {
        const res = await fetch('/api/v1/admin/overview');
        if (!res.ok) return;
        const data = await res.json();
        if (data.status !== 'success') return;
        renderAdminOverview(data);
    } catch (e) {
        console.warn('[Admin] Overview fetch failed:', e);
    }
}

function renderAdminOverview(data) {
    const { summary, clients } = data;

    // ── KPI Cards ─────────────────────────────────────────
    setText('admin-kpi-clients', summary.total_clients);
    setText('admin-kpi-aum', `₹${fmtNum(summary.total_aum)}`);

    const pnlEl = document.getElementById('admin-kpi-pnl');
    if (pnlEl) {
        const p = summary.total_pnl;
        pnlEl.textContent = `${p >= 0 ? '+' : ''}₹${fmtNum(Math.abs(p))}`;
        pnlEl.style.color = p >= 0 ? 'var(--success)' : 'var(--danger)';
    }
    setText('admin-kpi-alerts', summary.risk_alerts);

    // System health sidebar
    setText('admin-sys-sessions', summary.total_clients);
    setText('admin-sys-blocks', summary.risk_alerts);
    setText('admin-sys-trades', summary.total_trades);

    // Timestamp
    setText('admin-last-refresh', new Date().toLocaleTimeString('en-IN'));

    // ── Client Table ──────────────────────────────────────
    const tbody = document.getElementById('admin-client-table');
    if (!tbody) return;

    if (!clients || clients.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;color:var(--text-dim);padding:30px;">
            No active sessions yet — clients appear after first login.</td></tr>`;
    } else {
        tbody.innerHTML = clients.map(c => {
            const pnlSign = c.daily_pnl >= 0 ? '+' : '';
            const pnlColor = c.daily_pnl >= 0 ? 'var(--success)' : 'var(--danger)';
            const pctSign = c.pnl_pct >= 0 ? '+' : '';
            const riskColor = c.risk_status === 'BLOCKED' ? 'var(--danger)' :
                c.risk_status === 'ACTIVE' ? 'var(--success)' : 'var(--text-dim)';
            const modeBadge = modeColor(c.mode);

            return `<tr>
                <td style="font-weight:600;font-size:.8rem;">${escHtml(c.user_id)}</td>
                <td>₹${fmtNum(c.capital)}</td>
                <td>${c.open_positions}</td>
                <td style="font-weight:700;color:${pnlColor};">
                    ${pnlSign}₹${fmtNum(Math.abs(c.daily_pnl))}
                </td>
                <td style="color:${pnlColor};">${pctSign}${c.pnl_pct}%</td>
                <td><span style="color:${riskColor};font-weight:700;">${c.risk_status}</span></td>
                <td><span class="badge" style="background:${modeBadge.bg};color:${modeBadge.fg};font-size:.65rem;">${c.mode}</span></td>
                <td style="text-align:right;">
                    <button onclick="adminImpersonate('${escHtml(c.user_id)}')"
                        style="background:transparent;border:1px solid var(--border);color:var(--text);border-radius:6px;padding:4px 10px;cursor:pointer;font-size:.7rem;">
                        VIEW
                    </button>
                </td>
            </tr>`;
        }).join('');
    }

    // ── P&L Bar Chart ─────────────────────────────────────
    renderAdminPnlChart(clients);
}

function renderAdminPnlChart(clients) {
    const canvas = document.getElementById('admin-pnl-chart');
    if (!canvas || !window.Chart) return;

    const labels = clients.map(c => c.user_id.split('@')[0]);  // short name
    const values = clients.map(c => c.daily_pnl);
    const colors = values.map(v => v >= 0 ? 'rgba(0,200,110,0.75)' : 'rgba(255,70,70,0.75)');
    const borders = values.map(v => v >= 0 ? '#00c86e' : '#ff4646');

    if (_adminPnlChart) {
        _adminPnlChart.data.labels = labels;
        _adminPnlChart.data.datasets[0].data = values;
        _adminPnlChart.data.datasets[0].backgroundColor = colors;
        _adminPnlChart.data.datasets[0].borderColor = borders;
        _adminPnlChart.update('none');
        return;
    }

    _adminPnlChart = new Chart(canvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Daily P&L (₹)',
                data: values,
                backgroundColor: colors,
                borderColor: borders,
                borderWidth: 1,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ₹${ctx.raw >= 0 ? '+' : ''}${fmtNum(Math.abs(ctx.raw))}`
                    }
                }
            },
            scales: {
                x: { ticks: { color: 'var(--text-dim)', font: { size: 10 } }, grid: { display: false } },
                y: {
                    ticks: { color: 'var(--text-dim)', font: { size: 10 }, callback: v => `₹${fmtNum(Math.abs(v))}` },
                    grid: { color: 'rgba(255,255,255,0.04)' }
                }
            }
        }
    });
}

async function adminOnboardClient() {
    const uid = document.getElementById('new-client-id')?.value?.trim();
    const cap = parseFloat(document.getElementById('new-client-capital')?.value || '0');
    const statusEl = document.getElementById('onboard-status');

    if (!uid) { if (statusEl) statusEl.textContent = '⚠ Enter a valid client ID.'; return; }
    if (cap <= 0) { if (statusEl) statusEl.textContent = '⚠ Enter a valid capital amount.'; return; }

    if (statusEl) statusEl.textContent = 'Provisioning…';

    try {
        // 1. Login to provision session
        await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: uid, password: 'managed' })
        });

        // 2. Set capital
        await fetch('/api/v1/settings/capital', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-User-ID': uid },
            body: JSON.stringify({ amount: cap })
        });

        if (statusEl) statusEl.textContent = `✅ ${uid} onboarded with ₹${fmtNum(cap)}`;
        document.getElementById('new-client-id').value = '';
        document.getElementById('new-client-capital').value = '';
        fetchAdminOverview();
    } catch (e) {
        if (statusEl) statusEl.textContent = `❌ Error: ${e.message}`;
    }
}

async function adminForceStopAll() {
    if (!confirm('⚠ Force-stop ALL client sessions?')) return;
    for (const [uid,] of Object.entries({})) {  // iterate via overview
        try {
            await fetch('/api/v1/system/square_off_all', {
                method: 'POST',
                headers: { 'X-User-ID': uid }
            });
        } catch (e) { }
    }
    // Also stop own session
    await fetch('/api/v1/system/square_off_all', { method: 'POST' });
    fetchAdminOverview();
}

function adminImpersonate(uid) {
    // Switch local session header context to view as that client
    window._currentUserOverride = uid;
    alert(`Viewing as: ${uid}\nSwitch back to admin by refreshing.`);
}

// ── Helpers ───────────────────────────────────────────────
function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function fmtNum(n) {
    if (n === null || n === undefined || isNaN(n)) return '—';
    if (Math.abs(n) >= 1e7) return (n / 1e7).toFixed(2) + 'Cr';
    if (Math.abs(n) >= 1e5) return (n / 1e5).toFixed(2) + 'L';
    return Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function modeColor(mode) {
    const map = {
        PAPER: { bg: 'rgba(0,200,255,0.15)', fg: '#00c8ff' },
        REAL: { bg: 'rgba(0,200,110,0.15)', fg: '#00c86e' },
        SIMULATION: { bg: 'rgba(255,180,0,0.15)', fg: '#ffb400' },
        MOCK: { bg: 'rgba(120,120,120,0.15)', fg: '#888' },
    };
    return map[mode] || map.MOCK;
}

function escHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
// --- USER PROFILE LOGIC ---

async function fetchUserProfile() {
    try {
        const res = await fetch('http://localhost:3000/user/profile');
        if (!res.ok) throw new Error("Could not fetch profile.");
        const data = await res.json();
        
        if (data.status === 'success') {
            const profile = data.data;
            
            // Update UI Fields
            setText('profile-id-metric', profile.uid.substring(0, 8).toUpperCase());
            setText('profile-created-date', new Date(profile.creationTime).toLocaleDateString());
            setText('profile-email-display', profile.email || localStorage.getItem('antigravity_user_id') || 'Institutional User');
            setText('profile-last-login', new Date(profile.lastSignInTime).toLocaleTimeString());
            setText('profile-execution-mode', state.executionMode || 'MOCK');
            const totalProfit = state.metrics ? (state.metrics.daily_pnl || 0) : 0;
            const profitEl = document.getElementById('profile-total-profits');
            if (profitEl) {
                profitEl.textContent = `₹${totalProfit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
                profitEl.className = `val ${totalProfit >= 0 ? 'success-text' : 'danger-text'}`;
            }

            const nameInput = document.getElementById('profile-name-input');
            if (nameInput) nameInput.value = profile.displayName || '';
            
            const badge = document.getElementById('profile-verification-badge');
            if (badge) {
                badge.textContent = profile.emailVerified ? 'VERIFIED' : 'NOT VERIFIED';
                badge.className = `badge ${profile.emailVerified ? 'success' : 'danger'}`;
            }
            
            // Activity Log (Simplified)
            const logBody = document.getElementById('profile-activity-log');
            if (logBody) {
                const now = new Date();
                logBody.innerHTML = `
                    <tr>
                        <td>LOGIN_SUCCESS</td>
                        <td>Session established via Email/Password Auth</td>
                        <td>${new Date(profile.lastSignInTime).toLocaleString()}</td>
                        <td><span style="color: var(--success); font-weight: 700;">OK</span></td>
                    </tr>
                `;
            }
        }
    } catch (err) {
        console.error("Profile Fetch Error:", err);
    }
}

async function updateProfileName() {
    const name = document.getElementById('profile-name-input').value.trim();
    if (!name) return alert("Please enter a display name.");
    
    try {
        const res = await fetch('http://localhost:3000/user/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const data = await res.json();
        if (res.ok) {
            alert("✓ Display name updated successfully.");
            fetchUserProfile(); // Refresh
        } else {
            alert(`✕ Update failed: ${data.message}`);
        }
    } catch (err) {
        console.error("Update Name Error:", err);
    }
}

async function updateProfilePassword() {
    const newPass = document.getElementById('profile-new-password').value;
    if (newPass.length < 6) return alert("Password must be at least 6 characters.");
    
    if (!confirm("⚠️ This will update your platform master password. Continue?")) return;

    try {
        const res = await fetch('http://localhost:3000/user/update-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ newPassword: newPass })
        });
        const data = await res.json();
        if (res.ok) {
            alert("✓ Password updated successfully.");
            document.getElementById('profile-new-password').value = '';
        } else {
            alert(`✕ Password update failed: ${data.message}`);
        }
    } catch (err) {
        console.error("Update Password Error:", err);
    }
}
