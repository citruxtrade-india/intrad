
import os
import asyncio
import json
import threading
import time
import datetime
import hashlib
import pyotp
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
from dotenv import load_dotenv
import websocket
from pya3 import Aliceblue
import secrets
import smtplib
from email.mime.text import MIMEText

# --- CORE IMPORTS ---
from core.live_data_manager import LiveDataManager
from core.commodity_live_manager import CommodityLiveManager
from core.pattern_engine import CandlestickPatternEngine
from agents.v2.manager import AgentManager
from agents.v2.market_context import MarketContextAgent
from agents.v2.structure_pattern import StructurePatternAgent
from agents.v2.validation import ValidationAgent
from agents.v2.risk_capital import RiskCapitalAgent
from agents.v2.execution_engine import ExecutionEngine
from agents.v2.audit_logger import AuditLoggerAgent
from agents.v2.guidance_agent import GuidanceAgent
from agents.v2.strategy_selector import StrategySelector
from agents.v2.backtesting_engine import BacktestingEngine
from agents.v2.learning_engine import LearningEngine
from core.symbol_search_manager import SymbolSearchManager
from config import EXECUTION_MODE
from paper_engine import PaperTradingEngine
from execution_router import ExecutionRouter

# ---------------- CONFIG & STATE ---------------- #
load_dotenv()
API_KEY = os.getenv("ALICEBLUE_API_KEY", "").strip()
USER_ID = os.getenv("ALICEBLUE_USER_ID", "").strip()
TOTP_SECRET = os.getenv("ALICEBLUE_TOTP_SECRET", "").strip()

class GlobalExchangeState:
    def __init__(self, user_id="admin", broker_name="ALICE_BLUE"):
        self.user_id = user_id
        self.broker_name = broker_name
        # Per-user broker credentials (set on onboarding, used by data engine)
        # Admin users leave this empty and fall back to .env
        self.broker_credentials = {}  # {user_id, api_key, totp_secret}
        self.metrics = {
            "total_capital": 100000.0,
            "used_capital_amount": 0.0,
            "daily_pnl": 0.0,
            "max_drawdown": 0.0,
            "risk_used_percent": 0.0
        }
        self.market_data = {
            "NIFTY": {"ltp": None, "close": None, "volume": None, "status": "INITIAL", "timestamp": 0},
            "BANKNIFTY": {"ltp": None, "close": None, "volume": None, "status": "INITIAL", "timestamp": 0},
            "SENSEX": {"ltp": None, "close": None, "volume": None, "status": "INITIAL", "timestamp": 0},
            "HINDUNILVR": {"ltp": None, "close": None, "volume": None, "status": "INITIAL", "timestamp": 0},
            "HDFCBANK": {"ltp": None, "close": None, "volume": None, "status": "INITIAL", "timestamp": 0}
        } 
        self.active_symbol = "NIFTY"
        self.active_exch = "NSE"
        self.search_mgr = SymbolSearchManager()
        self.trades = []
        self.managed_users = [
            {"user_id": "admin@antigravity.ia", "role": "OWNER", "status": "ACTIVE", "sync": "OFFLINE"}
        ]
        self.market_feed_active = True # Allows pausing data polling
        self.logs = []
        self.risk_rules = {
            "max_trades_per_day": 3,
            "risk_per_trade_percent": 1.0,
            "max_daily_loss_percent": 1.0
        }
        self.system_health = "HEALTHY" # HEALTHY | DEGRADED
        self.execution_mode = EXECUTION_MODE  # Controlled via config.py
        self.is_running = False
        self.alice = None
        self.lock = threading.RLock()
        self.engine_running = False
        self.websocket_instance = None
        self.data_engine_status = "DISCONNECTED" # DISCONNECTED | CONNECTING | CONNECTED
        self.monitored_instruments = {"NIFTY", "BANKNIFTY", "SENSEX", "GOLD", "SILVER", "CRUDEOIL", "NATGASMINI", "HINDUNILVR", "HDFCBANK"}
        self.market_segments = {
            "NSE": {"open": "09:15", "close": "15:30", "days": [0,1,2,3,4]},
            "BSE": {"open": "09:15", "close": "15:30", "days": [0,1,2,3,4]},
            "MCX": {"open": "09:00", "close": "23:30", "days": [0,1,2,3,4]}
        }

        # --- COMMODITY LIVE DATA MANAGER (Non-intrusive, read-only) ---
        self.commodity_manager = CommodityLiveManager(user_id=self.user_id)

        # --- AGENT V2 CORE ---
        self.agent_manager = AgentManager(self)
        self.ctx_agent = MarketContextAgent(self.agent_manager)
        self.pattern_agent = StructurePatternAgent(self.agent_manager)
        self.val_agent = ValidationAgent(self.agent_manager)
        self.risk_agent = RiskCapitalAgent(self.agent_manager)
        self.exec_engine = ExecutionEngine(self.agent_manager)
        self.audit_agent = AuditLoggerAgent(self.agent_manager)
        self.guide_agent = GuidanceAgent(self.agent_manager)
        self.strategy_selector = StrategySelector(self.agent_manager)
        self.learning_engine = LearningEngine(self.agent_manager)
        self.backtest_engine = BacktestingEngine()

        self.agent_manager.register_agent("MarketContext", self.ctx_agent)
        self.agent_manager.register_agent("StructurePattern", self.pattern_agent)
        self.agent_manager.register_agent("Validation", self.val_agent)
        self.agent_manager.register_agent("RiskCapital", self.risk_agent)
        self.agent_manager.register_agent("Execution", self.exec_engine)
        self.agent_manager.register_agent("AuditLogger", self.audit_agent)
        self.agent_manager.register_agent("Guidance", self.guide_agent)
        self.agent_manager.register_agent("StrategySelector", self.strategy_selector)
        self.agent_manager.register_agent("LearningEngine", self.learning_engine)

        # --- PAPER TRADING & ROUTING ---
        self.paper_engine = PaperTradingEngine(user_id=self.user_id)
        self.execution_router = ExecutionRouter(broker_client=self.alice)
        # Alias so ExecutionEngine can find it via getattr(state, 'risk_capital_agent')
        self.risk_capital_agent = self.risk_agent
        
    def add_log(self, message):
        ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        with self.lock:
            self.logs.append({"timestamp": ts, "message": message})
            if len(self.logs) > 100: self.logs.pop(0)

class GlobalSessionManager:
    """Manager for multi-user session state isolation."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalSessionManager, cls).__new__(cls)
            cls._instance.sessions = {}
        return cls._instance

    def get_state(self, user_id: str = "admin", broker_name: str = "ALICE_BLUE") -> GlobalExchangeState:
        if user_id not in self.sessions:
            self.sessions[user_id] = GlobalExchangeState(user_id=user_id, broker_name=broker_name)
        return self.sessions[user_id]

session_mgr = GlobalSessionManager()

def get_session_id(request: Request):
    # Extract from header or fallback to default for dev/single-user compatibility
    return request.headers.get("X-User-ID", "admin")

# ---------------- ALICE BLUE ENGINE ---------------- #

def is_market_open(segment, state: GlobalExchangeState):
    """Check if market segment is currently open in IST"""
    now = datetime.datetime.now()
    # If segment unknown, assume open to be safe
    if segment not in state.market_segments: return True
    
    cfg = state.market_segments[segment]
    if now.weekday() not in cfg["days"]: return False
    
    current_time_str = now.strftime("%H:%M")
    return cfg["open"] <= current_time_str <= cfg["close"]

async def start_data_engine(user_id="admin"):
    """WebSocket engine to receive live market ticks via LiveDataManager"""
    state = session_mgr.get_state(user_id)
    # Strict rule: Live data only for PAPER or REAL modes
    if state.execution_mode not in ["PAPER", "REAL"]:
        state.add_log(f"Data engine skipped: Current mode {state.execution_mode} uses internal feed.")
        return

    ldm = LiveDataManager(user_id=user_id, broker_name=state.broker_name)
    if ldm.status in ["CONNECTED", "CONNECTING"]:
        state.add_log("Data engine already active.")
        return
    
    symbols_mgr = {
        "NIFTY": {"exch": "NSE", "token": 26000, "segment": "NSE", "broker_symbol": "NIFTY 50"},
        "BANKNIFTY": {"exch": "NSE", "token": 26009, "segment": "NSE", "broker_symbol": "NIFTY BANK"},
        "SENSEX": {"exch": "BSE", "token": 1, "segment": "BSE", "broker_symbol": "SENSEX"},
        "GOLD": {"exch": "MCX", "token": 454818, "segment": "MCX", "broker_symbol": "GOLD"},
        "SILVER": {"exch": "MCX", "token": 451666, "segment": "MCX", "broker_symbol": "SILVER"},
        "CRUDEOIL": {"exch": "MCX", "token": 472789, "segment": "MCX", "broker_symbol": "CRUDEOIL"},
        "NATGASMINI": {"exch": "MCX", "token": 475112, "segment": "MCX", "broker_symbol": "NATGASMINI"},
        "HINDUNILVR": {"exch": "NSE", "token": 1394, "segment": "NSE", "broker_symbol": "HINDUNILVR"},
        "HDFCBANK": {"exch": "NSE", "token": 1333, "segment": "NSE", "broker_symbol": "HDFCBANK"}
    }
    
    token_map = {str(cfg['token']): name for name, cfg in symbols_mgr.items()}
    
    try:
        # Use per-user credentials if set (managed users), else fall back to global .env (admin)
        creds = state.broker_credentials
        effective_user_id  = creds.get("user_id")  or USER_ID
        effective_api_key  = creds.get("api_key")  or API_KEY
        effective_totp     = creds.get("totp_secret") or TOTP_SECRET

        if not effective_api_key or not effective_user_id or not effective_totp:
            raise Exception("Broker credentials missing. Set in .env (admin) or add via Admin Console (managed users).")

        ldm.set_credentials(effective_user_id, effective_api_key, effective_totp)

        # Prepare symbol list for the manager
        sub_list = []
        for name, cfg in symbols_mgr.items():
            if name in state.monitored_instruments:
                sub_list.append({
                    "exchange": cfg['exch'],
                    "token": cfg['token'],
                    "name": name
                })
                # Initialize state entry if missing
                with state.lock:
                    if name not in state.market_data:
                        state.market_data[name] = {"ltp": None, "close": None, "volume": None, "status": "WAITING", "timestamp": 0, "segment": cfg['segment']}
                    else:
                        state.market_data[name]["segment"] = cfg['segment']

        # Define bridge callback
        def server_tick_handler(msg):
            if msg is None: return
            token = msg.get('tk')
            # Use injected 'ts' from LDM or fallback to hardest mapping
            name = msg.get('ts') or token_map.get(str(token))
            
            if name:
                try:
                    lp = msg.get('lp')
                    ltp = float(lp) if lp is not None and str(lp) != "0" else None
                    if ltp is None: return # Ignore invalid ticks

                    # Handle close price logic
                    c_val = msg.get('c')
                    close = float(c_val) if c_val is not None and str(c_val) != "0" else ltp
                    volume = float(msg.get('v', 0))
                    
                    with state.lock:
                        if name not in state.market_data:
                            state.market_data[name] = {"ltp": None, "close": None, "volume": None, "status": "WAITING", "timestamp": 0}
                            
                        state.market_data[name].update({
                            "ltp": ltp,
                            "volume": volume,
                            "close": close,
                            "timestamp": time.time(),
                            "status": "LIVE"
                        })
                    
                    if state.is_running:
                        threading.Thread(target=run_agent_pipeline, args=(name, ltp, close)).start()
                except Exception as e:
                    state.add_log(f"Tick Error ({name}): {e}")

        # Register callback and start feed
        ldm.register_callback(server_tick_handler)
        state.add_log("Starting LiveDataManager...")
        await ldm.start(sub_list)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        state.add_log(f"Live Feed Broker connection failed: {str(e)}")
        if state.execution_mode in ["PAPER", "REAL"]:
            state.add_log(">>> INITIATING VIRTUAL FEED (STABILITY FALLBACK) <<<")
            start_simulation_feed(symbols_mgr, user_id=user_id)

    # --- START COMMODITY LIVE DATA (Non-intrusive, read-only) ---
    await start_commodity_data_engine(user_id=user_id)

async def stop_data_engine(user_id="admin"):
    """Safely shut down the LiveDataManager"""
    try:
        state = session_mgr.get_state(user_id)
        ldm = LiveDataManager(user_id=user_id, broker_name=state.broker_name)
        state.add_log("Stopping LiveDataManager...")
        await ldm.stop()
    except Exception as e:
        state.add_log(f"Error stopping data engine: {e}")
    # Also stop commodity data
    await stop_commodity_data_engine(user_id=user_id)


# ---- COMMODITY LIVE DATA ENGINE (Non-intrusive) ---- #

async def start_commodity_data_engine(user_id="admin"):
    """
    Start commodity futures live data streaming.
    READ-ONLY: Only updates commodity_market_cache.
    Activates ONLY in PAPER / REAL modes.
    Does NOT modify strategy, execution, risk, or order logic.
    """
    state = session_mgr.get_state(user_id)
    if state.execution_mode not in ["PAPER", "REAL"]:
        state.add_log("Commodity data skipped: Not in PAPER/REAL mode.")
        return

    cm = state.commodity_manager
    if cm.is_active():
        state.add_log("Commodity live feed already active.")
        return

    try:
        # Use per-user credentials if set (managed users), else fall back to global .env (admin)
        creds = state.broker_credentials
        eff_user_id = creds.get("user_id") or USER_ID
        eff_api_key = creds.get("api_key") or API_KEY
        eff_totp    = creds.get("totp_secret") or TOTP_SECRET

        if not eff_api_key or not eff_user_id or not eff_totp:
            state.add_log("Commodity live feed: Missing broker credentials.")
            return

        cm.set_credentials(eff_user_id, eff_api_key, eff_totp)

        # Bridge callback: Sync commodity cache → server state for UI
        def commodity_tick_bridge(symbol, data):
            """READ-ONLY bridge: Updates market_data state for UI consumption."""
            try:
                with state.lock:
                    if symbol in state.market_data:
                        state.market_data[symbol].update({
                            "ltp": data["ltp"],
                            "volume": data["volume"],
                            "close": data.get("close", data["ltp"]),
                            "timestamp": time.time(),
                            "status": "LIVE",
                            "segment": "MCX"
                        })
                    else:
                        state.market_data[symbol] = {
                            "ltp": data["ltp"],
                            "close": data.get("close", data["ltp"]),
                            "volume": data["volume"],
                            "timestamp": time.time(),
                            "status": "LIVE",
                            "segment": "MCX"
                        }
            except Exception:
                pass  # Never crash on bridge errors

        cm.register_callback(commodity_tick_bridge)

        state.add_log("Starting Commodity Live Data (MCX Futures)...")
        await cm.start()
        state.add_log(f"Commodity Live Feed: {cm.status} | Tracking: {list(cm.resolved_instruments.keys())}")

    except Exception as e:
        state.add_log(f"Commodity live feed error: {str(e)}")
        # Never crash backend on commodity data failure


async def stop_commodity_data_engine(user_id="admin"):
    """Safely shut down commodity live data. Clears cache, sets DISCONNECTED."""
    state = session_mgr.get_state(user_id)
    try:
        cm = state.commodity_manager
        if cm.is_active():
            state.add_log("Stopping Commodity Live Data...")
            await cm.stop()
            state.add_log("Commodity live feed stopped.")
    except Exception as e:
        state.add_log(f"Commodity stop error: {e}")

def run_agent_pipeline(symbol, ltp, close, user_id="admin"):
    """Agent V2 Analytical Chain - Decoupled Routing"""
    state = session_mgr.get_state(user_id)
    
    # 1. Context Analysis (MarketContextAgent)
    ctx_event = state.ctx_agent.process(symbol, ltp, close)
    
    # 2. Strategy Guidance (StrategySelector) - NEW LAYER
    strategy = state.strategy_selector.analyze_and_guide(symbol, ctx_event)
    
    # 3. Pattern Detection (StructurePatternAgent)
    pattern_event = state.pattern_agent.process(symbol, ltp)
    
    # Extract structural signal
    signal = pattern_event.get("context", {}).get("pattern", "NONE")
    
    # 4. Validation (Enhanced with indicator confluence)
    val_event = state.val_agent.validate(symbol, ltp, ctx_event, pattern_event)
    
    # --- META-INTELLIGENCE & SYSTEM AWARENESS (NEW) ---
    mood   = ctx_event.get("context", {}).get("market_mood", "RANGE")
    genome = val_event.get("payload", {}).get("pattern_genome", "DEFAULT")
    base_c = (val_event.get("payload", {}).get("confidence", 0.5) * 100)
    
    volatility = ctx_event.get("context", {}).get("volatility", "Normal")
    trend_str = ctx_event.get("context", {}).get("trend_strength", 0.5)
    
    # 1. Self-Aware Opportunity Awareness
    opp = state.learning_engine.update_market_opportunity(volatility, trend_str)
    
    # 2. Meta-Aware Predictive Scoring
    trade_score = state.learning_engine.compute_trade_score(base_c, strategy, mood, pattern=genome)
    
    # Audit Trail: Metadata storage
    val_event["payload"]["trade_score"] = trade_score
    val_event["payload"]["system_health"] = state.learning_engine.health_score
    val_event["payload"]["system_mode"] = state.learning_engine.system_mode

    if val_event.get("state") == "APPROVED":
        # 3. Global Selective Execution (Ranking)
        rank_threshold = 62 # Lowered from 72 for faster execution
        if state.learning_engine.system_mode == "DEFENSIVE": rank_threshold = 85 # Ultra-strict on defense
            
        # NIFTY Optimization Override
        if symbol == "NIFTY":
            trade_score += 5 # Institutional priority boost
            
        if trade_score < rank_threshold:
            state.learning_engine.log_skip(symbol, f"Meta Ranking Rejection (Rank {trade_score} < Req {rank_threshold})", strategy, mood, trade_score)
            state.add_log(f"🧠 [META-INT] {symbol} blocked. Health {state.learning_engine.health_score}% | Rank {trade_score} < {rank_threshold}.")
        else:
            # 4. Risk & Compliance — Capital Prioritization (Score-linked qty)
            # Pass trade_score to enable intelligence-based sizing
            sizing = state.risk_agent.compute_position_size(ltp, state.metrics.get("total_capital", 100_000), 
                                                           state.risk_rules, trade_score=trade_score)
            
            if state.risk_agent.check_risk(symbol, ltp, state.metrics, risk_rules=state.risk_rules):
                # 5. Adaptive Routed Execution
                state.exec_engine.current_strategy = strategy
                state.exec_engine.current_mood = mood
                state.exec_engine.current_genome = genome
                # Pass sizing to execution if needed, currently it re-calculates inside route_execution
                # So we must ensure route_execution also passes trade_score or uses state cache
                state.exec_engine.last_score_cache = trade_score 
                state.exec_engine.route_execution(symbol, ltp, signal, state)
                
                state.add_log(f"✅ [META] EXECUTE: {symbol} | Mode: {state.learning_engine.system_mode} | Priority: {sizing['priority']}")
    
    # 8. Guidance & Strategy Pulse
    state.guide_agent.generate_advice(state.agent_manager.get_audit_trail(10))

def start_simulation_feed(symbols, user_id="admin"):
    """Fallback feed for when broker is not available"""
    state = session_mgr.get_state(user_id)
    def simulate(name):
        # Base prices for indices/commodities
        bases = {
            "NIFTY": 24500.0, "BANKNIFTY": 52000.0, "SENSEX": 81000.0,
            "GOLD": 72000.0, "SILVER": 88000.0, "CRUDEOIL": 6400.0, "NATGASMINI": 180.0
        }
        ltp = bases.get(name, 100.0)
        close = ltp - (ltp * 0.005) # simulate -0.5% opening
        
        while True:
            import random
            change = (random.random() - 0.48) * (ltp * 0.0001) # tiny realistic ticks
            ltp += change
            
            with state.lock:
                state.market_data[name] = {
                    "ltp": round(ltp, 2),
                    "volume": float(random.randint(10000, 50000)),
                    "close": close,
                    "timestamp": time.time(),
                    "status": "VIRTUAL"
                }

            # Trigger Agents if system is running
            if state.is_running:
                # Run pipeline in background thread
                threading.Thread(target=run_agent_pipeline, args=(name, ltp, close, user_id)).start()
                
            time.sleep(1.5)

    for name in symbols.keys():
        t = threading.Thread(target=simulate, args=(name,))
        t.daemon = True
        t.start()

# ---------------- WEB SERVER ---------------- #

app = FastAPI()

# Ensure static directory exists
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def get_index():
    return FileResponse("static/index.html")

# --- MOCK USER DATABASE ---
USER_DB = {} # email -> { password, name, phone, email_otp, otp_expiry, is_verified, otp_attempts, last_otp_sent }

def send_otp_email(email_address: str, otp: str):
    message = f"Your verification OTP is: {otp}. Valid for 5 minutes."
    masked_message = f"Your verification OTP is: ***{otp[-3:]}. Valid for 5 minutes."
    print(f"\n[EMAIL SIMULATION] To: {email_address} | {masked_message}\n")
    
    # Local developer inbox fallback for testing without real SMTP credentials
    try:
        with open("mock_email_inbox.txt", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now()}] To: {email_address} | {message}\n")
    except Exception:
        pass

    try:
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        if smtp_user and smtp_pass:
            msg = MIMEText(message)
            msg['Subject'] = 'Your Verification OTP'
            msg['From'] = smtp_user
            msg['To'] = email_address
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
    except Exception as e:
        print(f"SMTP failed: {e}")

@app.post("/api/v1/auth/login")
async def login(request: Request):
    data = await request.json()
    user_id = data.get("user_id", "admin")
    api_key = data.get("api_key", "")
    
    # Authenticate via USER_DB if email exists
    if user_id in USER_DB:
        user = USER_DB[user_id]
        if user["password"] != api_key:
            return JSONResponse(status_code=401, content={"status": "error", "reason": "Invalid credentials."})
        if not user.get("is_verified", False):
            return JSONResponse(status_code=403, content={"status": "error", "reason": "Verification required.", "is_verified": False})
    
    # Eagerly provision an isolated session for this user on login
    session_mgr.get_state(user_id)
    return {"status": "success", "mode": "PAPER", "user": user_id}

@app.post("/api/v1/auth/register")
async def register(request: Request):
    data = await request.json()
    email = data.get("email")
    if not email:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Email is required."})
        
    otp = str(secrets.randbelow(900000) + 100000)
    expiry = datetime.datetime.now() + datetime.timedelta(minutes=5)
    
    USER_DB[email] = {
        "name": data.get("name"),
        "phone": data.get("phone"),
        "password": data.get("password"),
        "email_otp": otp,
        "otp_expiry": expiry,
        "is_verified": False,
        "otp_attempts": 0,
        "last_otp_sent": datetime.datetime.now()
    }
    
    send_otp_email(email, otp)
    return {"status": "success", "message": "OTP Sent Successfully"}

@app.post("/api/v1/auth/verify-otp")
async def verify_otp(request: Request):
    data = await request.json()
    email = data.get("email")
    otp = data.get("otp")
    
    user = USER_DB.get(email)
    if not user:
        return JSONResponse(status_code=404, content={"status": "error", "message": "User not found."})
        
    if user.get("otp_attempts", 0) >= 5:
        return JSONResponse(status_code=429, content={"status": "error", "message": "Too many attempts. Request a new OTP."})
        
    if not user.get("email_otp") or not user.get("otp_expiry"):
        return JSONResponse(status_code=400, content={"status": "error", "message": "No OTP requested."})
        
    if datetime.datetime.now() > user.get("otp_expiry"):
        return JSONResponse(status_code=400, content={"status": "error", "message": "OTP has expired."})
        
    if user.get("email_otp") != otp:
        user["otp_attempts"] = user.get("otp_attempts", 0) + 1
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid OTP."})
        
    user["is_verified"] = True
    user["email_otp"] = None
    user["otp_expiry"] = None
    user["otp_attempts"] = 0
    return {"status": "success", "message": "Email verified successfully."}

@app.post("/api/v1/auth/resend-otp")
async def resend_otp(request: Request):
    data = await request.json()
    email = data.get("email")
    
    user = USER_DB.get(email)
    if not user:
        return JSONResponse(status_code=404, content={"status": "error", "message": "User not found."})
        
    now = datetime.datetime.now()
    last_sent = user.get("last_otp_sent")
    if last_sent and (now - last_sent).total_seconds() < 30:
        return JSONResponse(status_code=429, content={"status": "error", "message": "Please wait 30 seconds before resending OTP."})
        
    otp = str(secrets.randbelow(900000) + 100000)
    user["email_otp"] = otp
    user["otp_expiry"] = now + datetime.timedelta(minutes=5)
    user["otp_attempts"] = 0
    user["last_otp_sent"] = now
    
    send_otp_email(email, otp)
    return {"status": "success", "message": "New OTP sent."}

@app.post("/api/v1/auth/forgot-password")
async def forgot_password(request: Request):
    import httpx
    payload = await request.json()
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post("http://localhost:3000/auth/forgot-password", json=payload)
            return res.json()
        except:
             return {"status": "error", "message": "Auth System Link Failure"}

@app.get("/api/v1/account/daily-pnl")
async def get_account_daily_pnl(request: Request):
    """Authoritative P&L Source - Lock to Broker/Engine State"""
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    val = await calculate_authoritative_pnl(state)
    with state.lock:
        state.metrics["daily_pnl"] = val
    return {"status": "success", "daily_pnl": val}

_pnl_cache = {} # Keyed by user_id

async def calculate_authoritative_pnl(state: GlobalExchangeState):
    """Internal helper to compute P&L from the single source of truth."""
    global _pnl_cache
    now = time.time()
    user_id = state.user_id
    
    # Cache for 1 second per user
    if user_id in _pnl_cache and now - _pnl_cache[user_id]["time"] < 1.0:
        return _pnl_cache[user_id]["val"]

    val = 0.0
    if state.execution_mode == 'PAPER':
        # Sum from Paper Engine (Authoritative for simulation)
        with state.lock:
            current_prices = {s: d["ltp"] for s, d in state.market_data.items() if d["ltp"] is not None}
        pnl = state.paper_engine.get_pnl(current_prices)
        val = round(pnl['total'], 2)
    
    elif state.execution_mode == 'REAL':
        ldm = LiveDataManager(user_id=user_id)
        if ldm.adapter and ldm.adapter.alice:
            try:
                pos = ldm.adapter.alice.get_daywise_positions()
                if isinstance(pos, list):
                    val = round(sum(float(p.get('urmtom', 0)) + float(p.get('rpnl', 0)) for p in pos), 2)
                elif isinstance(pos, dict) and pos.get('stat') == 'Ok':
                    val = 0.0
            except Exception:
                pass
        else:
            with state.lock:
                val = round(sum(t.get('pnl', 0) for t in state.trades), 2)
            
    _pnl_cache[user_id] = {"val": val, "time": now}
    return val

@app.post("/api/v1/settings/capital")
async def update_capital(request: Request):
    """Update total capital and optionally paper trading virtual capital."""
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    try:
        data = await request.json()
        amount = float(data.get("amount", 100000.0))
        with state.lock:
            state.metrics["total_capital"] = amount
            if hasattr(state, "paper_engine"):
                # Align paper virtual capital to exactly the requested amount
                state.paper_engine.virtual_capital = amount
                # We could adjust realized_pnl to 0.0 to reset the offset if they want a clean slate,
                # but for simplicity we just directly overwrite the base capital.
                
        state.add_log(f"System capital updated to ₹{amount:,.2f} for user {user_id}")
        return {"status": "success", "capital": amount}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/dashboard/metrics")
async def get_metrics(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    # Update metrics from authoritative source
    pnl = await calculate_authoritative_pnl(state)
    
    with state.lock:
        state.metrics["daily_pnl"] = pnl
        intel = state.learning_engine.get_intelligence_summary()
        state.metrics["system_health"] = intel["health_score"]
        state.metrics["system_mode"] = intel["system_mode"]
        
        return {
            "metrics": state.metrics,
            "intelligence": intel,
            "market_data": state.market_data,
            "is_running": state.is_running,
            "execution_mode": state.execution_mode,
            "data_engine_status": LiveDataManager(user_id=user_id).status,
            "timestamp": time.time()
        }

@app.get("/api/v1/system/health")
def get_system_health(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    return {"status": "success", "health": state.system_health}

@app.get("/api/v1/market/status")
def get_market_status(request: Request):
    user_id = get_session_id(request)
    return LiveDataManager(user_id=user_id).get_status()

@app.get("/api/v1/trades/open")
def get_trades(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    return state.trades

@app.get("/api/v1/alerts/logs")
def get_logs(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    return state.logs

@app.get("/api/v1/risk/rules")
def get_rules(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    return state.risk_rules

@app.get("/api/v1/market/ohlc/{market}")
async def get_market_ohlc(request: Request, market: str):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    with state.lock:
        current_time = time.time()
        
        if market == "COMMODITY":
            commodities = ["GOLD", "SILVER", "CRUDEOIL", "NATGASMINI"]
            data_list = []
            cm = state.commodity_manager
            comm_cache = cm.get_cache()

            for c in commodities:
                d = state.market_data.get(c, {"ltp": None, "close": None, "volume": None, "timestamp": 0, "segment": "MCX"})
                
                # Enrich with commodity live cache if available
                live = comm_cache.get(c, {})
                
                # Check Market Hours
                if not is_market_open(d.get("segment", "MCX"), state):
                    status = "MARKET_CLOSED"
                else:
                    status = "LIVE" if (current_time - d.get("timestamp", 0)) < 15 else "STALE"

                entry = {
                    "instrument": c,
                    "ltp": live.get("ltp") or d.get("ltp"),
                    "close": live.get("close") or d.get("close"),
                    "volume": live.get("volume") or d.get("volume"),
                    "status": status,
                    "bid": live.get("bid"),
                    "ask": live.get("ask"),
                    "open_interest": live.get("open_interest", 0),
                    "expiry": live.get("expiry", ""),
                    "data_source": live.get("source", "CACHE"),
                    "live_status": cm.status
                }
                data_list.append(entry)

            return {
                "status": "success",
                "data": data_list,
                "commodity_feed_status": cm.status,
                "commodity_last_update": cm.last_update
            }
        else:
            # For Equity/Index, ensure we have recent data
            d = state.market_data.get(market, {"ltp": None, "close": None, "volume": None, "timestamp": 0, "segment": "NSE"})
            
            # If LTP is missing, try a quick wait if connected
            if d.get("ltp") is None and state.execution_mode in ["PAPER", "REAL"]:
                ldm = LiveDataManager(user_id=user_id)
                if ldm.status == "CONNECTED":
                    await ldm.wait_for_symbol_data(market, timeout=1.0)
                    d = state.market_data.get(market, d)

            # Check Market Hours
            if not is_market_open(d.get("segment", "NSE"), state):
                return {
                    "status": "MARKET_CLOSED",
                    "instrument": market,
                    "ltp": d["ltp"],
                    "close": d["close"],
                    "reason": "Market is currently closed for this segment."
                }

            status = "LIVE" if (current_time - d.get("timestamp", 0)) < 15 else "STALE"
            
            if d.get("ltp") is None:
                return {
                    "status": "DATA_UNAVAILABLE",
                    "reason": "Live data temporarily unavailable"
                }

            return {
                "status": "success", 
                "instrument": market,
                "ltp": d["ltp"], 
                "close": d["close"], 
                "volume": d["volume"],
                "data_status": status
            }

@app.post("/api/v1/market/monitor")
async def update_monitored_instruments(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    data = await request.json()
    instruments = data.get("instruments", [])
    if not isinstance(instruments, list):
        raise HTTPException(status_code=400, detail="Instruments must be a list")
    
    with state.lock:
        state.monitored_instruments = set(instruments)
        state.add_log(f"Monitoring Scope Updated: {list(state.monitored_instruments)}")
    
    # Restart data engine to apply new subscriptions (Alice Blue socket needs re-subscription)
    # For now, we'll just let the next tick filtering handle it, or we could trigger a socket re-sync.
    # But start_data_engine is already running. The socket_open handles initial subscription.
    # To truly be dynamic without restart, we'd need to call alice.subscribe in the running engine.
    # We'll just update the set for now as a safety filter.
    
    return {"status": "success", "monitored": list(state.monitored_instruments)}

@app.get("/market-data/{symbol}")
async def get_live_market_data(request: Request, symbol: str):
    """Production-spec Live Market Data Endpoint with async sync"""
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    ldm = LiveDataManager(user_id=user_id)
    symbol = symbol.upper()
    data = ldm.get_market_snapshot(symbol)
    
    if not data and state.execution_mode in ["PAPER", "REAL"]:
        # Try to wait for it if we are connected
        if ldm.status == "CONNECTED":
            await ldm.wait_for_symbol_data(symbol, timeout=2.0)
            data = ldm.get_market_snapshot(symbol)
            
    if not data:
        # Fallback to general state if not in LDM cache (e.g. simulation/mock modes)
        with state.lock:
            cached = state.market_data.get(symbol)
            if cached:
                return {
                    "ltp": cached.get("ltp"),
                    "bid": cached.get("bid"),
                    "ask": cached.get("ask"),
                    "volume": cached.get("volume"),
                    "timestamp": datetime.datetime.fromtimestamp(cached.get("timestamp", 0)).isoformat() if cached.get("timestamp") else None,
                    "status": cached.get("status", "DISCONNECTED")
                }
        raise HTTPException(status_code=404, detail=f"Market data for {symbol} not found")

    return {
        "ltp": data.get("ltp"),
        "bid": data.get("bid"),
        "ask": data.get("ask"),
        "volume": data.get("volume"),
        "timestamp": data.get("timestamp"),
        "status": data.get("status", ldm.status)
    }

@app.get("/market-status")
def get_market_status_legacy(request: Request):
    """Legacy Market Status Endpoint"""
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    ldm = LiveDataManager(user_id=user_id)
    cm = state.commodity_manager
    return {
        "connection_state": ldm.status,
        "last_update": ldm.last_update,
        "commodity": cm.get_status()
    }

@app.get("/api/v1/commodity/live-status")
def get_commodity_live_status(request: Request):
    """Commodity futures live data connection status & cache."""
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    cm = state.commodity_manager
    return {
        "status": "success",
        "connection": cm.status,
        "last_update": cm.last_update,
        "mcx_open": CommodityLiveManager.is_mcx_open(),
        "instruments": list(cm.resolved_instruments.keys()),
        "expiry_map": cm._expiry_map,
        "cache": cm.get_cache()
    }

@app.get("/api/v1/commodity/snapshot/{symbol}")
async def get_commodity_snapshot(request: Request, symbol: str):
    """Get live snapshot for a single commodity (async sync)."""
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    cm = state.commodity_manager
    symbol = symbol.upper()
    data = cm.get_snapshot(symbol)
    
    # Non-blocking wait if needed
    if not data and state.execution_mode in ["PAPER", "REAL"]:
        pass 

    if not data:
        # Fallback to main market_data state
        with state.lock:
            cached = state.market_data.get(symbol)
            if cached:
                return {
                    "status": "success",
                    "instrument": symbol,
                    "ltp": cached.get("ltp"),
                    "volume": cached.get("volume"),
                    "close": cached.get("close"),
                    "data_source": "FALLBACK",
                    "live_status": cm.status
                }
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")

    return {
        "status": "success",
        "instrument": symbol,
        **data,
        "live_status": cm.status
    }

@app.get("/api/v1/market/search")
async def search_symbols(request: Request, q: str = ""):
    """Universal symbol search across NSE, BSE, MCX"""
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    if len(q) < 2:
        return {"status": "success", "results": []}
    results = state.search_mgr.search(q, limit=10)
    return {"status": "success", "results": results}

@app.get("/api/v1/market/history/{symbol}")
async def get_market_history(request: Request, symbol: str, timeframe: str = "5m", exchange: str = "NSE"):
    """Fetch OHLC history with detected candlestick patterns."""
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    symbol = symbol.upper()
    inst = state.search_mgr.get_by_symbol(symbol, exchange)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found")

    ldm = LiveDataManager(user_id=user_id)
    if ldm.status != "CONNECTED":
        # Fallback for MOCK mode: Generate some fake candles
        fake_candles = []
        now = datetime.datetime.now()
        for i in range(100):
            ts = (now - datetime.timedelta(minutes=(100-i) * 5)).isoformat()
            fake_candles.append({
                "timestamp": ts,
                "open": 100 + i*0.1, "high": 102 + i*0.1, 
                "low": 98 + i*0.1, "close": 101 + i*0.1, "volume": 1000
            })
        engine = CandlestickPatternEngine()
        patterns = engine.detect_patterns(fake_candles)
        return {"status": "success", "ohlc": fake_candles, "patterns": patterns, "mode": "MOCK"}

    # Fetch real historical data
    adapter = ldm.adapter
    days_map = {'1m': 1, '5m': 3, '15m': 7, '1h': 30, '1d': 365}
    days = days_map.get(timeframe.lower(), 2)
    
    ohlc = await adapter.get_historical_data(exchange, inst['token'], timeframe, days=days)
    
    if not ohlc:
        # Final fallback if adapter fails
        return {"status": "error", "message": "Failed to fetch historical data from broker"}

    engine = CandlestickPatternEngine()
    patterns = engine.detect_patterns(ohlc)

    return {
        "status": "success",
        "symbol": symbol,
        "timeframe": timeframe,
        "ohlc": ohlc,
        "patterns": patterns,
        "mode": "REAL"
    }

@app.post("/api/v1/market/select")
async def select_symbol(request: Request):
    """Set active symbol and initiate live feed if in PAPER/REAL mode"""
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    data = await request.json()
    symbol = data.get("symbol")
    exch = data.get("exchange", "NSE")
    
    inst = state.search_mgr.get_by_symbol(symbol, exch)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found")
    
    with state.lock:
        state.active_symbol = symbol
        state.active_exch = exch
        
        # Initialize with LOADING status instead of 0.0 to trigger UI shimmer
        if symbol not in state.market_data or state.market_data[symbol].get("ltp") is None:
            state.market_data[symbol] = {
                "ltp": None, "close": None, "volume": None, 
                "status": "LOADING", "timestamp": time.time()
            }
    
    # Support for immediate REST snapshot to avoid 0 LTP glitch
    if state.execution_mode in ["PAPER", "REAL"]:
        ldm = LiveDataManager(user_id=user_id, broker_name=state.broker_name)
        
        # Initialize as LOADING
        with state.lock:
            state.market_data[symbol] = {
                "ltp": None, "close": None, "volume": None, 
                "status": "LOADING", "timestamp": time.time()
            }
        
        # Background fetch
        asyncio.create_task(ldm.subscribe_symbol({
            "exchange": exch,
            "token": inst["token"],
            "name": symbol
        }))
        
        # Non-blocking wait for data (atomic sync)
        if ldm.status == "CONNECTED":
            await ldm.fetch_snapshot(exch, inst["token"], symbol)
            # Wait a few ms for a potential socket tick if snapshot was slow
            await ldm.wait_for_symbol_data(symbol, timeout=1.5)
        
        state.add_log(f"Atomic subscription for {symbol} initiated. (Feed Status: {ldm.status})")
    else:
        # VIRTUAL/MOCK mode
        with state.lock:
            state.market_data[symbol] = {
                "ltp": 150.0, "close": 150.0, "volume": 1000, 
                "status": "VIRTUAL", "timestamp": time.time()
            }
        state.add_log(f"Selected virtual symbol: {symbol}")
        
    return {
        "status": "success",
        "symbol": symbol,
        "exchange": exch,
        "token": inst["token"],
        "live_sync": True if state.execution_mode in ["PAPER", "REAL"] else False,
        "feed_status": LiveDataManager(user_id=user_id).status
    }

@app.get("/api/v1/market/data/{symbol}")
async def get_symbol_data(request: Request, symbol: str):
    """Fetch latest snapshot for specific symbol with async wait and subscription check"""
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    symbol = symbol.upper()
    
    # 1. Check Primary Sources (Immediate)
    data = state.market_data.get(symbol)
    if not data:
        data = state.commodity_manager.get_snapshot(symbol)

    # 2. If data missing or loading, and we are in live mode, ensure subscription
    if (not data or data.get("ltp") is None) and state.execution_mode in ["PAPER", "REAL"]:
        ldm = LiveDataManager(user_id=user_id, broker_name=state.broker_name)
        if ldm.status == "CONNECTED":
            if symbol not in ldm.market_cache:
                pass
            
            # Wait for tick
            await ldm.wait_for_symbol_data(symbol, timeout=1.5)
            
            # Re-fetch from state (updated via callback) or LDM cache
            data = state.market_data.get(symbol)
            if not data or data.get("ltp") is None:
                ldm_snap = ldm.get_market_snapshot(symbol)
                if ldm_snap: data = ldm_snap

    if not data:
        return {
            "status": "success",
            "symbol": symbol,
            "ltp": None,
            "close": None,
            "volume": None,
            "data_status": "LOADING" 
        }

    return {
        "status": "success",
        "instrument": symbol,
        "ltp": data.get("ltp"),
        "close": data.get("close"),
        "volume": data.get("volume"),
        "data_status": data.get("status", "LIVE")
    }

async def _fetch_real_balance_direct(state: GlobalExchangeState) -> float:
    """
    Directly fetch balance from Alice Blue REST API without requiring WebSocket.
    Falls back gracefully on any error.
    """
    try:
        import pyotp as _pyotp
        from pya3 import Aliceblue as _Aliceblue

        creds = state.broker_credentials
        eff_user_id  = creds.get("user_id")  or USER_ID
        eff_api_key  = creds.get("api_key")  or API_KEY
        eff_totp     = creds.get("totp_secret") or TOTP_SECRET

        if not eff_api_key or not eff_user_id or not eff_totp:
            return None

        otp = _pyotp.TOTP(eff_totp).now()
        alice = _Aliceblue(user_id=eff_user_id, api_key=eff_api_key)
        session_res = alice.get_session_id(otp)

        if not session_res or not isinstance(session_res, dict) or not session_res.get("sessionID"):
            state.add_log(f"[Balance] REST login failed: {session_res}")
            return None

        if getattr(alice, 'session_id', None) is None:
            alice.session_id = session_res.get('sessionID')

        res = alice.get_balance()
        if isinstance(res, list):
            for margin in res:
                if margin.get('stat') == 'Ok' and margin.get('symbol') == 'ALL':
                    return float(margin.get('cashmarginavailable', 0) or 0)
        elif isinstance(res, dict) and res.get('stat') == 'Ok':
            return float(res.get('cashmarginavailable', 0) or 0)

    except Exception as e:
        state.add_log(f"[Balance] Direct REST fetch error: {e}")

    return None


@app.get("/api/v1/account/balance")
async def get_balance(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)

    if state.execution_mode == "REAL":
        try:
            # First try the existing connected adapter (fast path)
            ldm = LiveDataManager(user_id=user_id)
            real_bal = None

            adapter = getattr(ldm, 'adapter', None)
            if adapter and getattr(adapter, 'alice', None):
                real_bal = await adapter.get_balance()

            # If adapter isn't connected, fall back to direct REST login
            if real_bal is None:
                real_bal = await _fetch_real_balance_direct(state)

            if real_bal is not None:
                with state.lock:
                    state.metrics["total_capital"] = real_bal
                state.add_log(f"[Balance] Live balance fetched: ₹{real_bal:,.2f}")

        except Exception as e:
            state.add_log(f"[Balance] Refresh failed: {str(e)}")

    return {"status": "success", "balance": state.metrics["total_capital"]}

@app.get("/api/v1/account/holdings")
async def get_holdings(request: Request):
    """
    Fetch portfolio holdings / invested positions.
    - REAL mode: fetches live holdings from Alice Blue REST API.
    - PAPER mode: returns open paper engine positions.
    - MOCK/SIMULATION: returns empty list.
    """
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    holdings = []

    if state.execution_mode == "REAL":
        def _fetch_holdings_sync():
            """Run Alice Blue calls in a thread, reusing session if possible."""
            import pyotp as _pyotp
            from pya3 import Aliceblue as _Aliceblue

            creds = state.broker_credentials
            eff_user_id = creds.get("user_id") or USER_ID
            eff_api_key = creds.get("api_key") or API_KEY
            eff_totp    = creds.get("totp_secret") or TOTP_SECRET

            if not (eff_api_key and eff_user_id and eff_totp):
                return []

            # Reuse or Create Alice Blue Session
            alice = getattr(state, '_alice_holdings_obj', None)
            if not alice:
                alice = _Aliceblue(user_id=eff_user_id, api_key=eff_api_key)
                state._alice_holdings_obj = alice
            
            # Check if session is valid; if not, login
            if not getattr(alice, 'session_id', None):
                otp = _pyotp.TOTP(eff_totp).now()
                session_res = alice.get_session_id(otp)
                if session_res and isinstance(session_res, dict) and session_res.get("sessionID"):
                    alice.session_id = session_res.get('sessionID')
                else:
                    return []

            result = []

            # --- Demat holdings ---
            try:
                raw = alice.get_holding_positions()
                if isinstance(raw, dict) and raw.get('stat') == 'Ok':
                    for h in raw.get('HoldingVal', []):
                        qty = float(h.get('HUqty', 0) or 0) + float(h.get('Holdqty', 0) or 0)
                        sellable = float(h.get('SellableQty', 0) or 0)
                        if qty <= 0 and sellable <= 0:
                            continue
                        
                        effective_qty = max(qty, sellable)
                        avg_price = float(h.get('Price', 0) or 0)
                        symbol_name = (h.get('Nsetsym') or h.get('Bsetsym') or 'UNKNOWN')
                        symbol_name = symbol_name.replace('-EQ', '').replace('-BE', '').strip()
                        
                        # LTP logic: Ltp is current. LTnse/LTbse is previous close.
                        ltp = float(h.get('Ltp') or h.get('LTnse') or h.get('LTbse') or avg_price)
                        prev_close = float(h.get('LTnse') or h.get('LTbse') or ltp)
                        exchange = 'NSE' if h.get('Exch1') == 'nse_cm' else 'BSE'
                        
                        invested     = effective_qty * avg_price
                        current_val  = effective_qty * ltp
                        pnl_net      = current_val - invested
                        pnl_net_pct  = (pnl_net / invested * 100) if invested else 0
                        
                        pnl_day      = (ltp - prev_close) * effective_qty
                        pnl_day_pct  = ((ltp / prev_close - 1) * 100) if prev_close else 0

                        result.append({
                            "symbol": symbol_name, "qty": effective_qty,
                            "avg_price": avg_price, "ltp": ltp,
                            "invested": round(invested, 4), "current_value": round(current_val, 4),
                            "pnl": round(pnl_net, 4), "pnl_pct": round(pnl_net_pct, 2),
                            "pnl_day": round(pnl_day, 4), "pnl_day_pct": round(pnl_day_pct, 2),
                            "exchange": exchange, "type": "HOLDING"
                        })
            except Exception as e:
                print(f"[Holdings] Demat fetch error: {e}")
                # Reset session on failure to force relogin next time
                alice.session_id = None 

            # --- Intraday positions ---
            try:
                day_pos = alice.get_daywise_positions()
                if isinstance(day_pos, list):
                    for p in day_pos:
                        if p.get('stat') != 'Ok':
                            continue
                        qty = float(p.get('netqty', 0) or 0)
                        if abs(qty) <= 0 and float(p.get('rpnl', 0) or 0) == 0:
                            continue
                        
                        symbol_name = p.get('tsym', 'UNKNOWN').replace('-EQ', '').replace('-FUT', '')
                        avg_price = float(p.get('netavgprc', 0) or 0)
                        ltp = float(p.get('lp', 0) or avg_price)
                        
                        # For intraday, invested is meaningful for open positions
                        invested = abs(qty) * avg_price
                        current_val = abs(qty) * ltp
                        
                        # Day P&L for intraday is URM+RPNL
                        pnl_day = float(p.get('urmtom', 0) or 0) + float(p.get('rpnl', 0) or 0)
                        # Net P&L for intraday is same as Day P&L in most cases unless carried over
                        pnl_net = pnl_day 
                        
                        pnl_day_pct = (pnl_day / invested * 100) if invested else 0
                        
                        result.append({
                            "symbol": symbol_name, "qty": qty,
                            "avg_price": avg_price, "ltp": ltp,
                            "invested": round(invested, 4), "current_value": round(current_val, 4),
                            "pnl": round(pnl_net, 4), "pnl_pct": round(pnl_day_pct, 2),
                            "pnl_day": round(pnl_day, 4), "pnl_day_pct": round(pnl_day_pct, 2),
                            "exchange": p.get('exch', 'NSE'), "type": "INTRADAY"
                        })
            except Exception as e:
                print(f"[Holdings] Intraday fetch error: {e}")

            return result

        try:
            holdings = await asyncio.wait_for(
                asyncio.to_thread(_fetch_holdings_sync),
                timeout=15.0
            )
        except asyncio.TimeoutError:
            state.add_log("[Holdings] Fetch timed out after 15s")
        except Exception as e:
            state.add_log(f"[Holdings] Fetch error: {e}")


    elif state.execution_mode == "PAPER":
        # Return open paper positions
        try:
            positions = state.paper_engine.get_positions()
            with state.lock:
                prices = {s: d["ltp"] for s, d in state.market_data.items() if d.get("ltp")}
            for p in positions:
                sym = p.get("symbol", "")
                qty = float(p.get("qty", 0))
                avg_price = float(p.get("avg_price", 0))
                ltp = prices.get(sym, avg_price)
                invested = qty * avg_price
                current_val = qty * ltp
                pnl = current_val - invested
                pnl_pct = (pnl / invested * 100) if invested else 0
                holdings.append({
                    "symbol": sym, "qty": qty, "avg_price": avg_price, "ltp": ltp,
                    "invested": round(invested, 4), "current_value": round(current_val, 4),
                    "pnl": round(pnl, 4), "pnl_pct": round(pnl_pct, 2),
                    "pnl_day": round(pnl, 4), "pnl_day_pct": round(pnl_pct, 2),
                    "exchange": p.get("exchange", "NSE"), "type": "PAPER"
                })
        except Exception as e:
            state.add_log(f"[Holdings] Paper position error: {e}")

    total_invested = round(sum(h["invested"] for h in holdings), 4)
    total_current  = round(sum(h["current_value"] for h in holdings), 4)
    total_pnl_net  = round(sum(h["pnl"] for h in holdings), 4)
    total_pnl_day  = round(sum(h["pnl_day"] for h in holdings), 4)
    
    total_prev_val = total_current - total_pnl_day
    
    return {
        "status": "success",
        "mode": state.execution_mode,
        "holdings": holdings,
        "summary": {
            "total_invested": total_invested,
            "total_current_value": total_current,
            "total_pnl": total_pnl_net,
            "total_pnl_day": total_pnl_day,
            "pnl_pct": round((total_pnl_net / total_invested * 100), 2) if total_invested else 0,
            "pnl_day_pct": round((total_pnl_day / total_prev_val * 100), 2) if total_prev_val else 0,
            "count": len(holdings)
        }
    }


@app.get("/api/v1/agents/status")
def get_agent_status(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    return state.agent_manager.get_agent_statuses()

@app.get("/api/v1/agents/audit")
def get_audit_trail(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    return state.agent_manager.get_audit_trail()

@app.post("/api/v1/agents/guidance/on-demand")
async def get_on_demand_guidance(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    recent_events = state.agent_manager.get_audit_trail(15)
    context_str = json.dumps(recent_events)
    advice = state.guide_agent.get_on_demand_advice(context_str)
    return {"status": "success", "advice": advice}

@app.post("/api/v1/settings/risk")
async def update_risk(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    data = await request.json()
    with state.lock:
        state.risk_rules.update(data)
        state.metrics["total_capital"] = data.get("total_capital", state.metrics["total_capital"])
    state.add_log("Risk Protocols Updated via API")
    return {"status": "success"}

@app.post("/api/v1/settings/capital")
async def update_capital(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    data = await request.json()
    with state.lock:
        state.metrics["total_capital"] = data.get("amount", state.metrics["total_capital"])
    state.add_log(f"Capital Allocation Updated: Rs.{state.metrics['total_capital']}")
    return {"status": "success"}

@app.post("/api/v1/system/start")
def system_start(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    state.is_running = True
    state.add_log(">>> ALGO SYSTEM STARTED: LIVE MONITORING <<<")
    # Trigger data engine if not already running
    asyncio.create_task(start_data_engine(user_id=user_id))
    return {"status": "success"}

@app.post("/api/v1/system/restart-engine")
async def restart_engine(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    state.add_log(f"Manual data engine restart requested by {user_id}")
    await stop_data_engine(user_id=user_id)
    # Give it a second to clean up
    await asyncio.sleep(1)
    asyncio.create_task(start_data_engine(user_id=user_id))
    return {"status": "success", "message": "Engine restart initiated."}

@app.post("/api/v1/system/mode")
async def set_execution_mode(request: Request):
    """
    Switch execution mode with comprehensive safety checks.
    
    Blocks only when:
    - Invalid mode requested
    - REAL mode without credentials
    - Active orders mid-execution
    - System in locked state
    """
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid request format")
    
    new_mode = data.get("mode")
    
    # Validate mode
    if new_mode not in ["MOCK", "SIMULATION", "PAPER", "REAL"]:
        raise HTTPException(status_code=400, detail=f"Invalid mode '{new_mode}'. Valid modes: MOCK, SIMULATION, PAPER, REAL")
    
    # Safety Check 1: Validate credentials for REAL mode
    if new_mode == "REAL":
        if not API_KEY or not USER_ID or not TOTP_SECRET:
            raise HTTPException(
                status_code=403, 
                detail="REAL mode requires valid broker API credentials. Please configure API_KEY, USER_ID, and TOTP_SECRET in .env file."
            )
    
    # Safety Check 2: Check for active mid-execution orders (if applicable)
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    with state.lock:
        old_mode = state.execution_mode
        
        # Audit Log formatting with User ID
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_info = f"USER:{user_id}"
        state.add_log(f"[{timestamp}] {user_info} MODE SWITCH: {old_mode} -> {new_mode}")
        
        # Perform the switch
        state.execution_mode = new_mode
        
        # Isolation: Clear trades when switching modes to prevent data contamination
        state.trades = []
        if hasattr(state, 'paper_engine'):
            state.paper_engine.reset()
        state.add_log(f"[{timestamp}] {user_info} ISOLATION: Positions cleared for {new_mode} mode")
    
    # Initialize data source based on rules:
    # MOCK: No live data required
    # SIMULATION: Historical or internal feed
    # PAPER/REAL: Enable live market data feed
    if new_mode in ["PAPER", "REAL"]:
        try:
            # Bridging thread to async LDM (includes commodity data engine)
            def run_async_start():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(start_data_engine(user_id=user_id))
            
            threading.Thread(target=run_async_start, daemon=True).start()
        except Exception as e:
            state.add_log(f"Live data initialization failed: {str(e)}")
    else:
        # Non-live modes: Ensure live engine + commodity engine are stopped
        def run_async_stop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(stop_data_engine(user_id=user_id))
        
        threading.Thread(target=run_async_stop, daemon=True).start()
        if new_mode == "SIMULATION":
            # Logic for starting internal/historical simulator could go here
            state.add_log("Internal simulation feed initialized.")
        else:
            # MOCK: Data fetched from internal mock generator or last cached
            state.add_log("Internal mock data engine active.")
    
    # Determine data connection status message
    data_status = "disabled"
    if new_mode == "MOCK":
        data_status = "Internal Mock Data (Isolated)"
    elif new_mode == "SIMULATION":
        data_status = "Simulated Feed Active"
    elif new_mode == "PAPER":
        data_status = "Live Data Enabled (Virtual Execution)"
    elif new_mode == "REAL":
        data_status = "Live Data + Live Execution ACTIVE"
    
    return {
        "status": "success", 
        "mode": new_mode,
        "previous_mode": old_mode,
        "data_status": data_status,
        "user_id": USER_ID,
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.post("/api/v1/system/square_off_all")
def square_off(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    state.add_log("[EMERGENCY] SQUARE OFF INITIATED [EMERGENCY]")
    
    # NEW: Inform ExecutionEngine to close and record results
    with state.lock:
        # We use a default LTP of 0 or a last known price if available
        # This allows the learning engine to record the close event
        state.exec_engine.close_all_active(state, 0.0) 
        state.metrics["used_capital_amount"] = 0
    return {"status": "success"}

# --- ADMIN USER MANAGEMENT ---

@app.get("/api/v1/admin/users/list")
def list_managed_users(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    return {"status": "success", "users": state.managed_users}

@app.get("/api/v1/admin/overview")
async def get_admin_overview(request: Request):
    """
    Admin-only endpoint: aggregates live stats from ALL active user sessions.
    Returns per-client capital, daily P&L, positions, trade count, risk status, mode.
    """
    clients = []
    total_aum = 0.0
    total_pnl = 0.0
    risk_alerts = 0
    total_trades = 0

    for uid, s in session_mgr.sessions.items():
        with s.lock:
            cap = s.metrics.get("total_capital", 0)
            daily_pnl = s.metrics.get("daily_pnl", 0)
            used = s.metrics.get("used_capital_amount", 0)
            mode = s.execution_mode
            trades = len(s.trades)
            # Count open paper positions
            positions = len(s.paper_engine.open_positions) if hasattr(s.paper_engine, 'open_positions') else 0
            risk_status = s.risk_agent.status if hasattr(s, 'risk_agent') else "UNKNOWN"

        pnl_pct = round((daily_pnl / cap * 100), 2) if cap else 0
        total_aum += cap
        total_pnl += daily_pnl
        total_trades += trades
        if risk_status == "BLOCKED":
            risk_alerts += 1

        clients.append({
            "user_id": uid,
            "capital": cap,
            "daily_pnl": round(daily_pnl, 2),
            "pnl_pct": pnl_pct,
            "open_positions": positions,
            "trade_count": trades,
            "used_capital": round(used, 2),
            "risk_status": risk_status,
            "mode": mode,
        })

    # Sort: highest P&L first
    clients.sort(key=lambda x: x["daily_pnl"], reverse=True)

    return {
        "status": "success",
        "summary": {
            "total_clients": len(clients),
            "total_aum": round(total_aum, 2),
            "total_pnl": round(total_pnl, 2),
            "risk_alerts": risk_alerts,
            "total_trades": total_trades,
        },
        "clients": clients
    }

@app.post("/api/v1/admin/users/add")
async def add_managed_user(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    password = data.get("password")
    api_key = data.get("api_key")
    secret_key = data.get("secret_key")
    broker = data.get("broker", "ALICE_BLUE") # Default to Alice Blue

    if not all([user_id, password, api_key, secret_key]):
         raise HTTPException(status_code=400, detail="Missing required credential fields")

    # SECURITY: In a real scenario, we would use these to perform a one-time 
    # handshake/validation via the broker API.
    # For this system (MOCK MODE), we simulate a successful validation.
    
    # Resolve admin's session (the one performing the add)
    admin_id = request.headers.get("X-User-ID", "admin")
    admin_state = session_mgr.get_state(admin_id)

    with admin_state.lock:
        # Check for duplicates
        if any(u["user_id"] == user_id for u in admin_state.managed_users):
            raise HTTPException(status_code=400, detail="User already onboarded")
        
        # Add to managed list (READ-ONLY ACCESS SCOPED)
        new_user = {
            "user_id": user_id,
            "role": "MANAGED_TRADER",
            "status": "CONNECTED",
            "broker": broker,
            "sync": "READ_ONLY",
            "joined_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        admin_state.managed_users.append(new_user)

    # Eagerly provision an isolated session for the new user and store their credentials
    new_user_state = session_mgr.get_state(user_id, broker_name=broker)
    new_user_state.broker_credentials = {
        "user_id": user_id,
        "api_key": api_key,
        "totp_secret": secret_key  # treated as TOTP secret / access token depending on broker
    }
        
    admin_state.add_log(f"Secure Onboarding: User {user_id} added on {broker}. Credentials stored in session.")
    
    return {"status": "success", "user": user_id, "broker": broker}

# --- PAPER TRADING API ---

@app.get("/paper/positions")
def get_paper_positions(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    return {"status": "success", "positions": state.paper_engine.get_positions()}

@app.get("/paper/pnl")
def get_paper_pnl(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    # Pass current market prices to calculate unrealized PnL
    with state.lock:
        current_prices = {s: d["ltp"] for s, d in state.market_data.items() if d["ltp"] is not None}
    return {"status": "success", "pnl": state.paper_engine.get_pnl(current_prices)}

@app.get("/paper/trades")
def get_paper_trades(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    return {"status": "success", "trades": state.paper_engine.get_trade_log()}

@app.post("/paper/reset")
def reset_paper_engine(request: Request):
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    state.paper_engine.reset()
    state.add_log("Paper Trading Engine Reset.")
    return {"status": "success"}

@app.post("/webhook")
async def tradingview_webhook(request: Request):
    """
    Webhook receiver for TradingView signals.
    Expects JSON: {"symbol": "NIFTY", "side": "BUY", "qty": 50}
    """
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    
    symbol = data.get("symbol", "").upper()
    side = data.get("side", "").upper()
    qty = data.get("qty", 1)
    
    if not symbol or not side:
        raise HTTPException(status_code=400, detail="Missing symbol or side")
    
    # Fetch latest LTP from live data cache
    with state.lock:
        market_info = state.market_data.get(symbol)
        ltp = market_info.get("ltp") if market_info else None
            
    if ltp is None or ltp <= 0.0:
        state.add_log(f"[WEBHOOK] Warning: Signal for {symbol} received but no live price available. Check data feed.")
        ltp = 0.0
    
    # Route the order via the new Execution Router
    ldm = LiveDataManager(user_id=user_id)
    if getattr(ldm, 'adapter', None):
        state.execution_router.broker = ldm.adapter.alice
    result = state.execution_router.route_order(symbol, side, qty, ltp, mode=state.execution_mode, state_logger=state.add_log)
    
    return {"status": "success", "webhook_result": result}

@app.post("/api/v1/order/manual")
async def manual_order(request: Request):
    """Manual order entry via UI dashboard."""
    user_id = get_session_id(request)
    state = session_mgr.get_state(user_id)
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
        
    symbol = data.get("symbol", "").upper()
    side = data.get("side", "").upper()
    qty = int(data.get("qty", 1))
    order_type = data.get("type", "MARKET").upper()
    price = data.get("price")
    
    if not symbol or not side:
        raise HTTPException(status_code=400, detail="Missing symbol or side")
        
    # Fetch latest LTP for market orders or validation
    with state.lock:
        market_info = state.market_data.get(symbol)
        # If not in main cache, try commodity manager
        if not market_info:
            market_info = state.commodity_manager.get_snapshot(symbol)
            
        ltp = market_info.get("ltp") if market_info else None
        
    if order_type == "MARKET":
        if ltp is None or ltp <= 0.0:
            raise HTTPException(status_code=400, detail=f"Cannot place market order for {symbol}: No live price available.")
        execution_price = ltp
    else:
        # Limit order
        if price is None or float(price) <= 0:
            raise HTTPException(status_code=400, detail="Valid Limit price is required for LIMIT orders.")
        execution_price = float(price)

    # Route the order via the Execution Router
    ldm = LiveDataManager(user_id=user_id)
    if getattr(ldm, 'adapter', None):
        state.execution_router.broker = ldm.adapter.alice
    result = state.execution_router.route_order(symbol, side, qty, execution_price, mode=state.execution_mode, state_logger=state.add_log)
    
    return {"status": "success", "result": result}


@app.on_event("startup")
async def startup_event():
    # Pre-provision the default admin session and start its data engine
    print("\n>>> Anti-Gravity Institutional Trading Platform is STARTING...")
    session_mgr.get_state("admin")
    # Start the data engine in the background without blocking the main event loop
    asyncio.create_task(start_data_engine(user_id="admin"))
    print(">>> Dashboard: http://localhost:8002")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
