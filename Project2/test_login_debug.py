# ===============================
# test_login_debug.py - Debug Login Issues
# ===============================

import requests
import pyotp
import json
from utils.logger import get_logger


API_KEY = "pguY4t7F"
CLIENT_ID = "AAAD452109"
PASSWORD = "4212"
TOTP_SECRET = "36ZX2GTMYYSS7PIJNWJNTME344"

def test_login_debug():
    self.logger.debug("=" * 50)
    self.logger.debug("DEBUGGING ANGEL API LOGIN")
    self.logger.debug("=" * 50)
    
    # Generate TOTP
    totp = pyotp.TOTP(TOTP_SECRET).now()
    print(f"TOTP: {totp}")
    
    # Prepare login payload
    url = "https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/login"
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Client-Library': 'python',
        'X-API-Key': API_KEY
    }
    
    payload = {
        "clientcode": CLIENT_ID,
        "password": PASSWORD,
        "totp": totp,
        "state": "WEB"
    }
    
    self.logger.debug(f"\nURL: {url}")
    self.logger.debug(f"Headers: {headers}")
    self.logger.debug(f"Payload: {payload}")
    
    # Make request
    try:
        self.logger.debug("\nSending request...")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        self.logger.debug(f"Response Status Code: {response.status_code}")
        self.logger.debug(f"Response Headers: {dict(response.headers)}")
        self.logger.debug(f"Raw Response Text: {response.text[:500]}")  # First 500 chars
        
        if response.status_code == 200:
            try:
                data = response.json()
                self.logger.info("\n✅ JSON parsed successfully!")
                self.logger.debug(f"Response JSON: {json.dumps(data, indent=2)[:500]}")
                
                if data.get('status'):
                    self.logger.info("\n✅ Login successful!")
                    self.logger.debug(f"Auth Token: {data['data']['jwtToken'][:50]}...")
                    self.logger.debug(f"Feed Token: {data['data']['feedToken']}")
                    return True
                else:
                    self.logger.error(f"\n❌ Login failed: {data}")
                    return False
            except json.JSONDecodeError as e:
                self.logger.error(f"\n❌ JSON Decode Error: {e}")
                return False
        else:
            self.logger.error(f"\n❌ HTTP Error: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        self.logger.error(f"\n❌ Connection Error: {e}")
        return False
    except requests.exceptions.Timeout as e:
        self.logger.error(f"\n❌ Timeout Error: {e}")
        return False
    except Exception as e:
        self.logger.error(f"\n❌ Unexpected Error: {e}")
        return False

if __name__ == "__main__":
    test_login_debug()