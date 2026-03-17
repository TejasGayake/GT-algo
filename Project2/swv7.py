# ===============================
# swv7.py - Fixed WebSocket Connection
# ===============================

from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from datetime import datetime, timedelta
import threading
import time
import pyotp
import pandas as pd
import logging

# ===============================
# CREDENTIALS
# ===============================
API_KEY = "pguY4t7F"
CLIENT_ID = "AAAD452109"
PASSWORD = "4212"
TOTP_SECRET = "36ZX2GTMYYSS7PIJNWJNTME344"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("swv7")

smartApi = None
sws = None
auth_token = None
feed_token = None
refresh_token = None
connected = False
reconnect_thread = None

# ===============================
# LOGIN FUNCTION
# ===============================
def login():
    """Login to Angel Broking API"""
    global smartApi, auth_token, feed_token, refresh_token
    
    try:
        smartApi = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        
        logger.info(f"Logging in with TOTP: {totp}")
        
        session = smartApi.generateSession(
            clientCode=CLIENT_ID,
            password=PASSWORD,
            totp=totp
        )
        
        if session.get("status"):
            auth_token = session["data"]["jwtToken"]
            refresh_token = session["data"]["refreshToken"]
            feed_token = smartApi.getfeedToken()
            logger.info("✅ Login successful")
            return True
        else:
            logger.error(f"❌ Login failed: {session}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        return False

# ===============================
# HISTORICAL DATA
# ===============================
def get_candles(token, days=5):
    """Fetch historical candles"""
    global smartApi
    
    if not smartApi:
        if not login():
            return None
    
    to_dt = datetime.now()
    from_dt = to_dt - timedelta(days=days)
    
    params = {
        "exchange": "NSE",
        "symboltoken": str(token).split('.')[0],
        "interval": "FIVE_MINUTE",
        "fromdate": from_dt.strftime("%Y-%m-%d %H:%M"),
        "todate": to_dt.strftime("%Y-%m-%d %H:%M")
    }
    
    try:
        logger.info(f"Fetching candles for token {token}")
        res = smartApi.getCandleData(params)
        
        if res and res.get("status"):
            logger.info(f"Got {len(res.get('data', []))} candles for token {token}")
            return res.get("data", [])
        else:
            logger.error(f"API returned error: {res}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching candles: {e}")
        return None

# ===============================
# WEBSOCKET STREAM
# ===============================
def start_stream(callback):
    """Start WebSocket stream with callback"""
    global sws, auth_token, feed_token, connected
    
    logger.info("Starting WebSocket stream...")
    
    # Login if needed
    if not auth_token or not feed_token:
        if not login():
            logger.error("❌ Login failed, cannot start WebSocket")
            return
    
    def on_open(ws):
        global connected
        connected = True
        logger.info("🟢 WebSocket connected")
    
    def on_data(ws, message):
        # Pass tick data to callback
        try:
            callback(message)
        except Exception as e:
            logger.error(f"Error in tick callback: {e}")
    
    def on_error(ws, error):
        global connected
        connected = False
        logger.error(f"🔴 WebSocket error: {error}")
    
    def on_close(ws):
        global connected
        connected = False
        logger.info("🔴 WebSocket closed")
        # Attempt to reconnect
        time.sleep(5)
        logger.info("Attempting to reconnect...")
        start_stream(callback)
    
    # Create WebSocket
    sws = SmartWebSocketV2(
        auth_token=auth_token,
        api_key=API_KEY,
        client_code=CLIENT_ID,
        feed_token=feed_token
    )
    
    # Set handlers
    sws.on_open = on_open
    sws.on_data = on_data
    sws.on_error = on_error
    sws.on_close = on_close
    
    # Connect
    try:
        sws.connect()
        logger.info("WebSocket connection initiated")
        
        # Wait for connection
        for i in range(10):
            if connected:
                break
            time.sleep(1)
        
    except Exception as e:
        logger.error(f"❌ WebSocket connection failed: {e}")
        connected = False
    
    # Keep thread alive
    while True:
        if not connected:
            logger.warning("WebSocket not connected, waiting...")
        time.sleep(1)

# ===============================
# SUBSCRIBE FUNCTION
# ===============================
def subscribe(token_list):
    """Subscribe to tokens"""
    global sws, connected
    
    if not sws:
        logger.error("❌ WebSocket not created")
        return False
    
    if not connected:
        logger.error("❌ WebSocket not connected")
        return False
    
    if not token_list:
        return False
    
    try:
        # Clean tokens (remove decimals)
        cleaned_list = []
        for item in token_list:
            tokens = [str(t).split('.')[0] for t in item.get('tokens', [])]
            cleaned_list.append({
                "exchangeType": item.get('exchangeType', 1),
                "tokens": tokens
            })
        
        logger.info(f"Subscribing to: {cleaned_list}")
        
        # Check if socket is still connected
        try:
            sws.subscribe(
                correlation_id="excel-feed",
                mode=3,
                token_list=cleaned_list
            )
            logger.info("✅ Subscription successful")
            return True
        except Exception as e:
            logger.error(f"❌ Subscription failed: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Subscription error: {e}")
        return False

# ===============================
# UNSUBSCRIBE FUNCTION
# ===============================
def unsubscribe(token_list):
    """Unsubscribe from tokens"""
    global sws
    
    if not sws or not connected:
        return False
    
    try:
        sws.unsubscribe(
            correlation_id="excel-feed",
            mode=3,
            token_list=token_list
        )
        logger.info("✅ Unsubscription successful")
        return True
    except Exception as e:
        logger.error(f"❌ Unsubscription failed: {e}")
        return False

# ===============================
# GET QUOTE
# ===============================
def get_quote(token):
    """Get current quote for a token"""
    global smartApi
    
    if not smartApi:
        if not login():
            return None
    
    try:
        clean_token = str(token).split('.')[0]
        response = smartApi.ltpData("NSE", clean_token, "")
        return response
    except Exception as e:
        logger.error(f"Error getting quote: {e}")
        return None

# ===============================
# TEST FUNCTION
# ===============================
def test_token(token="3045"):
    """Test if a token works"""
    logger.info(f"Testing token {token}...")
    
    if login():
        logger.info("✅ Login successful")
    else:
        logger.error("❌ Login failed")
        return
    
    candles = get_candles(token)
    if candles:
        logger.info(f"✅ Got {len(candles)} candles")
    else:
        logger.error("❌ Failed to get candles")
    
    quote = get_quote(token)
    if quote:
        logger.info(f"✅ Quote: {quote}")
    else:
        logger.error("❌ Failed to get quote")

if __name__ == "__main__":
    logger.info("Testing Angel Broking API...")
    test_token("3045")
