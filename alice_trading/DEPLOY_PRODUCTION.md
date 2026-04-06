# 🚀 Alice Trading / Antigravity AI - Deployment Guide

## 📡 System Architecture
This platform runs as a distributed system:
1. **Frontend/Core Engine (Python/FastAPI):** Port `8001`
2. **Auth & Profile Command Center (Node.js):** Port `3000`
3. **Database Layer:** Google Firebase / Firestore

---

## 🛠️ Deployment Steps (Production Server)

### 1. Environment Configuration
Ensure your `.env` file contains the following (copy from dev):
```bash
# ALICE BLUE API
USER_ID="YOUR_ID"
API_KEY="YOUR_KEY"
TOTP_SECRET="YOUR_TOTP"

# MODE (SIMULATION | PAPER | REAL)
EXECUTION_MODE="SIMULATION"
```

### 2. Launch the Auth Command Center
The UI relies on this for user profiles and dashboard security.
```bash
cd alice_trading
node auth_server.js
```

### 3. Launch the Trading Engine
Run this in a separate terminal or using a process manager like PM2.
```bash
cd alice_trading
python server.py
```

---

## 🧪 Reality Validation (Pre-Live Audit)
Before putting any capital at risk, run the **Reality Validation Stress Layer**:
```bash
# Run multi-scenario stress test
python run_stress_validation.py

# Expected Output: Report generated in 'reality_validation_report.json'
```

---

## 📈 Dashboard Access
- **Local:** `http://localhost:8001`
- **Network:** `http://[SERVER_IP]:8001`

**Deployment Stability Note:** The UI is now built with "Adaptive UX" scaling. It will adjust to any resolution from mobile to 4K ultra-wide monitors without overlapping boxes.
