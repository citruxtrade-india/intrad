# 🧪 Execution Mode System - Manual Testing Guide

## Prerequisites
✅ Server running at `http://127.0.0.1:8000`  
✅ Browser open (Chrome, Firefox, or Edge recommended)

---

## Test Plan

### **Test 1: Initial State Verification**

**Steps**:
1. Open browser and navigate to `http://127.0.0.1:8000`
2. Login with any credentials (e.g., `admin` / `admin`)
3. Look at the **left sidebar** at the bottom

**Expected Result**:
- ✅ You should see a badge that says **"MOCK MODE"**
- ✅ Badge should have a gray/neutral color
- ✅ Badge should be clickable (cursor changes to pointer on hover)

**Screenshot**: Take a screenshot showing the left sidebar with the MOCK MODE badge

---

### **Test 2: Mode Selection Modal**

**Steps**:
1. Click on the **"MOCK MODE"** badge in the left sidebar
2. Observe the modal that appears

**Expected Result**:
- ✅ A modal overlay should appear with title **"SYSTEM MODE"**
- ✅ Subtitle should say **"Select Execution Environment"**
- ✅ You should see **4 mode options**:
  - **MOCK MODE** (gray/neutral)
  - **SIMULATION** (blue/cyan color)
  - **PAPER TRADING** (yellow/warning color)
  - **🛑 REAL TRADING** (red background with warning icon)
- ✅ Each option should have a description below the title
- ✅ There should be a **CANCEL** button at the bottom

**Screenshot**: Take a screenshot of the mode selection modal

---

### **Test 3: Switch to SIMULATION Mode**

**Steps**:
1. With the modal open, click on **"SIMULATION"** option
2. Observe the sidebar badge

**Expected Result**:
- ✅ Modal should close automatically
- ✅ Sidebar badge should now show **"SIMULATION MODE"**
- ✅ Badge should have **blue/cyan background** with accent color
- ✅ Badge border should be blue/cyan

**Screenshot**: Take a screenshot showing the badge in SIMULATION mode

**API Verification**:
Open browser console (F12) and run:
```javascript
fetch('/api/v1/dashboard/metrics')
  .then(r => r.json())
  .then(d => console.log('Current Mode:', d.execution_mode));
```
Expected output: `Current Mode: SIMULATION`

---

### **Test 4: Switch to PAPER TRADING Mode**

**Steps**:
1. Click the badge again to open the modal
2. Click on **"PAPER TRADING"** option
3. Observe the sidebar badge

**Expected Result**:
- ✅ Modal should close
- ✅ Badge should now show **"PAPER TRADING"**
- ✅ Badge should have **yellow/orange background**
- ✅ Badge border should be yellow/warning color

**Screenshot**: Take a screenshot showing the badge in PAPER mode

**API Verification**:
```javascript
fetch('/api/v1/dashboard/metrics')
  .then(r => r.json())
  .then(d => console.log('Current Mode:', d.execution_mode));
```
Expected output: `Current Mode: PAPER`

---

### **Test 5: REAL Mode Critical Warning**

**Steps**:
1. Click the badge to open the modal
2. Click on **"🛑 REAL TRADING"** option
3. Observe what happens

**Expected Result**:
- ✅ A **browser alert/confirm dialog** should appear
- ✅ Dialog should say: **"⚠️ CRITICAL WARNING: You are about to enable REAL TRADING with live capital."**
- ✅ Dialog should ask: **"Are you absolutely sure you want to proceed?"**
- ✅ Dialog should have **OK** and **Cancel** buttons

**Screenshot**: Take a screenshot of the warning dialog (if possible)

**Action**: Click **Cancel** to dismiss the warning

**Expected Result After Cancel**:
- ✅ Badge should remain in **PAPER TRADING** mode (no change)
- ✅ Modal should remain open

---

### **Test 6: REAL Mode Activation (Optional - BE CAREFUL)**

⚠️ **WARNING**: Only perform this test if you understand that it will enable live trading mode. No actual trades will execute unless the system is running and generating signals.

**Steps**:
1. Click on "🛑 REAL TRADING" again
2. Click **OK** on the warning dialog

**Expected Result**:
- ✅ Badge should change to **"🔴 LIVE TRADING"**
- ✅ Badge should have **red background**
- ✅ Badge should have a **pulsing animation**
- ✅ Badge text should include the red circle emoji 🔴

**Screenshot**: Take a screenshot showing LIVE TRADING mode

**API Verification**:
```javascript
fetch('/api/v1/dashboard/metrics')
  .then(r => r.json())
  .then(d => console.log('Current Mode:', d.execution_mode));
```
Expected output: `Current Mode: REAL`

---

### **Test 7: Return to MOCK Mode**

**Steps**:
1. Click the badge to open the modal
2. Click on **"MOCK MODE"**

**Expected Result**:
- ✅ Badge returns to **"MOCK MODE"**
- ✅ Badge styling returns to gray/neutral
- ✅ No warning dialog (MOCK is safe)

---

### **Test 8: Live Market Data Verification**

**Steps**:
1. Look at the **top bar** of the dashboard
2. Find the market data boxes (NIFTY, BANKNIFTY, etc.)

**Expected Result**:
- ✅ You should see **live prices** (not zeros)
- ✅ Prices should have a **pulsing green indicator** (data-pulse)
- ✅ If data is stale (>10 seconds old), you might see an orange pulse or "STALE" badge
- ✅ If using virtual feed, you might see a "VIRTUAL" badge

**Screenshot**: Take a screenshot showing live market data

---

### **Test 9: Mode Persistence**

**Steps**:
1. Switch to **SIMULATION** mode
2. **Refresh the page** (F5 or Ctrl+R)
3. Look at the sidebar badge after page loads

**Expected Result**:
- ✅ Badge should still show **"SIMULATION MODE"**
- ✅ Mode should persist across page refreshes

---

### **Test 10: Audit Trail Logging**

**Steps**:
1. Switch between modes a few times (MOCK → SIMULATION → PAPER → MOCK)
2. Scroll down to the **"Decision Audit Trail"** section at the bottom of the dashboard
3. Look for mode change entries

**Expected Result**:
- ✅ You should see log entries like:
  - `"SYSTEM MODE CHANGED: MOCK -> SIMULATION (Positions Purged for Isolation)"`
  - `"SYSTEM MODE CHANGED: SIMULATION -> PAPER (Positions Purged for Isolation)"`
- ✅ Each entry should have a timestamp

**Screenshot**: Take a screenshot showing audit trail with mode changes

---

## API Testing (Alternative to Browser)

If you prefer to test via command line, use these curl commands:

### Check Current Mode
```bash
curl -s http://127.0.0.1:8000/api/v1/dashboard/metrics | python -m json.tool | findstr execution_mode
```

### Switch to SIMULATION
```bash
curl -X POST -H "Content-Type: application/json" -d "{\"mode\": \"SIMULATION\"}" http://127.0.0.1:8000/api/v1/system/mode
```

### Switch to PAPER
```bash
curl -X POST -H "Content-Type: application/json" -d "{\"mode\": \"PAPER\"}" http://127.0.0.1:8000/api/v1/system/mode
```

### Switch to REAL
```bash
curl -X POST -H "Content-Type: application/json" -d "{\"mode\": \"REAL\"}" http://127.0.0.1:8000/api/v1/system/mode
```

### Switch to MOCK
```bash
curl -X POST -H "Content-Type: application/json" -d "{\"mode\": \"MOCK\"}" http://127.0.0.1:8000/api/v1/system/mode
```

---

## Troubleshooting

### Issue: Badge not updating after mode switch
**Solution**: Hard refresh the page (Ctrl+F5)

### Issue: Modal doesn't open when clicking badge
**Solution**: 
1. Check browser console for JavaScript errors (F12 → Console tab)
2. Verify `app.js` is loaded (F12 → Network tab)
3. Clear browser cache and reload

### Issue: Mode switch returns error
**Solution**: 
1. Check server logs in the terminal
2. Verify server is running on port 8000
3. Check for typos in mode name (must be uppercase: MOCK, SIMULATION, PAPER, REAL)

### Issue: REAL mode doesn't show warning
**Solution**: Check browser console for errors in `confirmModeSwitch()` function

---

## Success Criteria

✅ All 10 tests pass  
✅ Mode badge updates correctly for each mode  
✅ REAL mode shows critical warning  
✅ Mode persists across page refresh  
✅ Audit trail logs mode changes  
✅ Live market data is visible  
✅ No JavaScript errors in console  

---

## Report Template

After completing the tests, fill out this report:

**Test Date**: _____________  
**Browser**: _____________  
**Server Version**: _____________  

| Test # | Test Name | Status | Notes |
|--------|-----------|--------|-------|
| 1 | Initial State | ✅ / ❌ | |
| 2 | Mode Selection Modal | ✅ / ❌ | |
| 3 | Switch to SIMULATION | ✅ / ❌ | |
| 4 | Switch to PAPER | ✅ / ❌ | |
| 5 | REAL Mode Warning | ✅ / ❌ | |
| 6 | REAL Mode Activation | ✅ / ❌ | |
| 7 | Return to MOCK | ✅ / ❌ | |
| 8 | Live Market Data | ✅ / ❌ | |
| 9 | Mode Persistence | ✅ / ❌ | |
| 10 | Audit Trail Logging | ✅ / ❌ | |

**Overall Result**: ✅ PASS / ❌ FAIL  
**Issues Found**: ___________________________  
**Screenshots Attached**: ___________________________

---

**Last Updated**: 2026-02-09  
**Version**: 2.0 (Multi-Mode Architecture)
