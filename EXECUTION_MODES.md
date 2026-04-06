# 🎯 Multi-Mode Execution System

## Overview

The Antigravity Trading Platform now supports **four distinct execution modes**, each designed for specific use cases in the trading strategy lifecycle. This architecture ensures complete isolation between environments, preventing accidental live trades and enabling safe strategy validation.

---

## 🔄 Execution Modes

### 1️⃣ MOCK MODE (Default)
**Purpose**: Internal logic testing with zero external dependencies

**Characteristics**:
- ✅ No market data required
- ✅ No broker API calls
- ✅ Pure analytical engine testing
- ✅ Signals logged but not executed
- ✅ Zero financial risk

**Use Cases**:
- Initial system exploration
- Agent logic debugging
- UI/UX testing
- Offline development

**Trade Execution**: Signals are logged to the audit trail with `[MOCK]` prefix. No positions are created.

---

### 2️⃣ SIMULATION MODE
**Purpose**: Historical data replay with virtual fills

**Characteristics**:
- 📊 Uses historical or delayed market data
- 🔄 Simulates order fills and slippage
- 📈 Tracks virtual P&L
- 🚫 No broker interaction
- ✅ Zero financial risk

**Use Cases**:
- Backtesting strategies
- Performance analysis
- Risk parameter tuning
- Training and education

**Trade Execution**: Virtual positions created with `SIM-XXX` trade IDs. P&L calculated based on simulated fills.

---

### 3️⃣ PAPER TRADING MODE ⚠️
**Purpose**: Live market validation with virtual execution

**Characteristics**:
- 📡 **Live market data** from broker feed
- 🎯 Virtual order fills at real prices
- 💰 Simulated capital tracking
- 🛡️ Full risk rule enforcement
- ✅ Zero financial risk

**Use Cases**:
- Strategy validation in live conditions
- Real-time performance monitoring
- Pre-production testing
- Confidence building before live trading

**Trade Execution**: Virtual positions created with `PAP-XXX` trade IDs. Fills use actual live market prices but no real orders are placed.

**⚠️ Important**: While this mode uses live data, **NO REAL CAPITAL IS AT RISK**. All trades are simulated.

---

### 4️⃣ REAL TRADING MODE 🔴
**Purpose**: Live institutional execution with real capital

**Characteristics**:
- 📡 Live market data
- 💸 **Real broker order placement**
- 💰 **Actual capital at risk**
- 🛡️ Strict risk enforcement
- ⚠️ Requires broker authentication

**Use Cases**:
- Production trading
- Institutional execution
- Real P&L generation

**Trade Execution**: Actual orders placed via Alice Blue API. Real positions, real fills, real P&L.

**🚨 CRITICAL SAFETY**:
- Requires explicit user confirmation
- Blocked if broker connection is unavailable
- All orders logged to audit trail
- Kill-switch always active

---

## 🏗️ Architecture

### Backend Components

#### 1. Global State (`server.py`)
```python
class GlobalExchangeState:
    def __init__(self):
        self.execution_mode = "MOCK"  # MOCK | SIMULATION | PAPER | REAL
        # ... other state
```

#### 2. Execution Router (`execution_engine.py`)
```python
def route_execution(self, symbol, ltp, signal, state):
    mode = state.execution_mode
    
    if mode == "MOCK":
        return self.execute_mock(...)
    elif mode == "SIMULATION":
        return self.execute_simulation(...)
    elif mode == "PAPER":
        return self.execute_paper(...)
    elif mode == "REAL":
        return self.execute_real(...)
```

#### 3. Mode-Specific Handlers
- `execute_mock()`: Logs signal, no action
- `execute_simulation()`: Creates virtual trade with SIM prefix
- `execute_paper()`: Creates virtual trade with PAP prefix using live prices
- `execute_real()`: Places actual broker order via Alice Blue API

### Frontend Components

#### 1. Mode Selection Modal (`index.html`)
- Visual grid with 4 mode options
- Color-coded for safety (Red for REAL)
- Clear descriptions for each mode

#### 2. Mode Badge (`broker-mode-sidebar`)
- Always visible in left sidebar
- Dynamically styled based on active mode
- Clickable to open mode selection

#### 3. Mode Switching Logic (`app.js`)
- `openModeSelectionModal()`: Opens selection UI
- `confirmModeSwitch(mode)`: Validates and switches mode
- `updateExecutionModeUI(mode)`: Updates visual indicators

---

## 🔐 Safety Mechanisms

### 1. Isolation Enforcement
When switching modes, the system automatically:
- ✅ Purges all active positions
- ✅ Resets trade history
- ✅ Logs the transition to audit trail
- ✅ Prevents cross-contamination of P&L

**Code**:
```python
with state.lock:
    old_mode = state.execution_mode
    state.execution_mode = new_mode
    state.trades = []  # Isolation purge
    state.add_log(f"SYSTEM MODE CHANGED: {old_mode} -> {new_mode}")
```

### 2. Real Mode Protection
- **Double Confirmation**: User must confirm critical warning dialog
- **Broker Validation**: Blocked if `state.alice` is None
- **Audit Logging**: All real orders logged with `[REAL]` prefix
- **Visual Alert**: Red pulsing badge when active

### 3. Mode Persistence
- Mode state stored in backend
- Survives page refreshes
- Exposed via `/api/v1/dashboard/metrics`

---

## 📡 API Reference

### Switch Execution Mode
**Endpoint**: `POST /api/v1/system/mode`

**Request**:
```json
{
  "mode": "PAPER"
}
```

**Valid Modes**: `MOCK`, `SIMULATION`, `PAPER`, `REAL`

**Response**:
```json
{
  "status": "success",
  "mode": "PAPER"
}
```

**Error Response**:
```json
{
  "status": "error",
  "detail": "Invalid Mode"
}
```

### Get Current Mode
**Endpoint**: `GET /api/v1/dashboard/metrics`

**Response**:
```json
{
  "total_capital": 100000.0,
  "execution_mode": "MOCK",
  ...
}
```

---

## 🎨 UI Visual Guide

### Mode Badge Styling

| Mode | Background | Text Color | Border | Special |
|------|-----------|-----------|--------|---------|
| MOCK | `var(--bg-card)` | `var(--text-dim)` | `var(--border)` | - |
| SIMULATION | `rgba(0, 243, 255, 0.1)` | `var(--accent)` | `var(--accent)` | Blue glow |
| PAPER | `rgba(255, 193, 7, 0.1)` | `var(--warning)` | `var(--warning)` | Yellow |
| REAL | `rgba(255, 62, 62, 0.1)` | `var(--danger)` | `var(--danger)` | Red + pulse |

---

## 🧪 Testing Checklist

### ✅ Mode Switching
- [ ] Can switch from MOCK to SIMULATION
- [ ] Can switch from SIMULATION to PAPER
- [ ] REAL mode shows critical warning
- [ ] Badge updates immediately after switch
- [ ] Trades are purged on mode change

### ✅ Execution Behavior
- [ ] MOCK: Signals logged, no trades created
- [ ] SIMULATION: Virtual trades with SIM prefix
- [ ] PAPER: Virtual trades with PAP prefix using live prices
- [ ] REAL: Blocked if broker disconnected

### ✅ UI Consistency
- [ ] Badge always reflects backend state
- [ ] Modal opens/closes correctly
- [ ] Mode persists across page refresh
- [ ] Visual styling matches mode

---

## 🚀 Usage Workflow

### Recommended Progression

1. **Start in MOCK** (Default)
   - Verify agent logic
   - Test UI interactions
   - Confirm system stability

2. **Move to SIMULATION**
   - Validate strategy with historical data
   - Tune risk parameters
   - Analyze virtual P&L

3. **Advance to PAPER TRADING**
   - Test with live market conditions
   - Verify execution timing
   - Build confidence in strategy

4. **Deploy to REAL** (Production)
   - Only after thorough paper trading
   - Start with minimal capital
   - Monitor closely

---

## 🛡️ Best Practices

1. **Never skip Paper Trading**: Always validate strategies with live data before risking real capital
2. **Monitor Audit Logs**: Review decision trail in all modes
3. **Test Mode Switches**: Verify behavior when switching between modes
4. **Respect Isolation**: Understand that switching modes clears positions
5. **Use Kill-Switch**: Emergency stop available in all modes

---

## 📝 Audit Trail Examples

### MOCK Mode
```
[MOCK] Signal BUY detected for NIFTY @ 25831.15. No action taken.
```

### SIMULATION Mode
```
[SIMULATION] Virtual fill confirmed: SIM-001 for NIFTY
```

### PAPER Mode
```
[PAPER] Virtual fill confirmed: PAP-001 for NIFTY
```

### REAL Mode
```
[REAL] >>> PLACING LIVE BROKER ORDER: NIFTY | BUY @ 25831.15
[REAL] BROKER CONFIRMATION: Order ID 240209001 FILLED
```

---

## 🔧 Troubleshooting

### Issue: Mode badge not updating
**Solution**: Hard refresh browser (Ctrl+F5) to clear cached JavaScript

### Issue: Cannot switch to REAL mode
**Possible Causes**:
1. Broker not connected (check logs for "Broker Engine Connected")
2. Invalid API credentials in `.env`
3. Network connectivity issues

### Issue: Trades not appearing after mode switch
**Expected Behavior**: Switching modes intentionally purges all positions for isolation

---

## 📚 Related Documentation

- `server.py`: Backend execution router
- `execution_engine.py`: Mode-specific execution handlers
- `app.js`: Frontend mode switching logic
- `index.html`: Mode selection modal UI

---

**Last Updated**: 2026-02-09  
**Version**: 2.0 (Multi-Mode Architecture)  
**Status**: ✅ Production Ready
