# ===============================
# test_login.py - Simple Login Test
# ===============================

from SmartApi import SmartConnect
import pyotp
from utils.logger import get_logger


API_KEY = "pguY4t7F"
CLIENT_ID = "AAAD452109"
PASSWORD = "4212"
TOTP_SECRET = "36ZX2GTMYYSS7PIJNWJNTME344"

def test_login():
    self.logger.debug("Testing direct login with SmartConnect...")
    
    try:
        smartApi = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        
        self.logger.debug(f"TOTP: {totp}")
        
        session = smartApi.generateSession(
            clientCode=CLIENT_ID,
            password=PASSWORD,
            totp=totp
        )
        
        if session.get("status"):
            self.logger.info("✅ Login successful!")
            self.logger.debug(f"Auth Token: {session['data']['jwtToken'][:20]}...")
            return True
        else:
            self.logger.error(f"❌ Login failed: {session}")
            return False
            
    except Exception as e:
        self.logger.error(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_login()