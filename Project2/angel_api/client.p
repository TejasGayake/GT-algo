# ===============================
# angel_api/client.py - Fixed Login
# ===============================

import requests
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import pyotp
import json

from utils.logger import get_logger
from angel_api.rate_limiter import RateLimiter
from angel_api.circuit_breaker import CircuitBreaker
from angel_api.cache_manager import CacheManager
from angel_api.exceptions import *

class AngelAPIClient:
    """
    Enhanced Angel Broking API client
    """
    
    def __init__(self, api_key: str, client_id: str, password: str, totp_secret: str):
        self.api_key = api_key
        self.client_id = client_id
        self.password = password
        self.totp_secret = totp_secret
        
        self.logger = get_logger('AngelAPIClient')
        
        # Create session
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Client-Library': 'python'
        })
        
        # Rate limiter
        self.rate_limiter = RateLimiter(max_calls=30, period=60)
        
        # Cache
        self.cache = CacheManager(ttl=300, max_size=1000)
        
        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        
        # API endpoints
        self.base_url = "https://apiconnect.angelbroking.com"
        self.endpoints = {
            'login': '/rest/auth/angelbroking/user/v1/login',
            'candle': '/rest/secure/angelbroking/historical/v1/getCandleData',
        }
        
        # Authentication
        self.auth_token = None
        self.feed_token = None
        self.refresh_token = None
        self.token_expiry = None
        
        # Metrics
        self.metrics = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'cached_calls': 0,
        }
        
        # Symbol mapping
        self.symbols = {}
        self.token_to_symbol = {}
        
        # Common symbols for fallback
        self.common_symbols = {
            "2885": "ITC",
            "3045": "RELIANCE",
            "1594": "TCS",
            "11536": "HDFC",
            "1660": "INFY",
            "17818": "HDFCBANK",
            "1394": "ICICIBANK",
            "4963": "SBIN",
            "3499": "TATAMOTORS",
            "10738": "TATASTEEL",
            "3501": "TATAPOWER",
            "3401": "SUNPHARMA",
            "14977": "BHARTIARTL",
            "2475": "KOTAKBANK",
            "11630": "WIPRO",
            "10940": "TECHM",
            "1901": "BAJFINANCE",
            "317": "BAJAJFINSV",
            "11915": "MARUTI",
            "910": "M&M",
            "1035": "ASIANPAINT",
            "881": "HINDUNILVR",
            "17963": "NESTLE",
            "467": "BRITANNIA",
            "1232": "TITAN",
            "1348": "ULTRACEMCO",
            "10789": "GRASIM",
            "1512": "JSWSTEEL",
            "11723": "NTPC",
            "11532": "ONGC",
            "247": "POWERGRID",
            "3493": "SHREECEM",
            "4373": "SBILIFE",
            "12167": "ICICIPRULI",
            "6351": "DIVISLAB",
            "12038": "DRREDDY",
            "3751": "CIPLA",
            "1245": "UPL",
            "3791": "EICHERMOT",
            "323": "BPCL",
            "1594": "HCLTECH",
        }
    
    def login(self) -> bool:
        """Login to Angel API"""
        # Check if already logged in and token valid
        if self.auth_token and self.token_expiry and datetime.now() < self.token_expiry:
            return True
        
        try:
            # Generate TOTP
            totp = pyotp.TOTP(self.totp_secret).now()
            self.logger.info(f"Logging in with TOTP: {totp}")
            
            # Prepare login payload
            payload = {
                "clientcode": self.client_id,
                "password": self.password,
                "totp": totp,
                "state": "WEB"
            }
            
            # Make login request
            response = self.session.post(
                self.base_url + self.endpoints['login'],
                json=payload,
                timeout=15
            )
            
            self.logger.info(f"Login response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    self.auth_token = data['data']['jwtToken']
                    self.feed_token = data['data']['feedToken']
                    self.refresh_token = data['data']['refreshToken']
                    self.token_expiry = datetime.now() + timedelta(hours=1)
                    
                    # Update session headers with auth token
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.auth_token}',
                        'X-API-Key': self.api_key
                    })
                    
                    self.logger.info("✅ Login successful")
                    return True
                else:
                    self.logger.error(f"❌ Login failed: {data}")
                    return False
            else:
                self.logger.error(f"❌ Login HTTP error: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"❌ Connection error during login: {e}")
            return False
        except requests.exceptions.Timeout as e:
            self.logger.error(f"❌ Timeout during login: {e}")
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Invalid JSON response: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Login error: {e}")
            return False
    
    def get_candles(self, token: str, exchange: str = "NSE", 
                    interval: str = "FIVE_MINUTE", days: int = 5,
                    force_refresh: bool = False) -> Optional[List]:
        """Fetch historical candles"""
        
        self.metrics['total_calls'] += 1
        clean_token = str(token).split('.')[0]
        
        # Check cache
        cache_key = f"candles_{clean_token}_{exchange}_{interval}_{days}"
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                self.metrics['cached_calls'] += 1
                self.logger.debug(f"Cache hit for token {clean_token}")
                return cached
        
        # Rate limiting
        if not self.rate_limiter.acquire(block=False):
            wait_time = self.rate_limiter.get_wait_time()
            self.logger.warning(f"Rate limited, waiting {wait_time:.2f}s")
            time.sleep(wait_time)
            self.rate_limiter.acquire(block=True)
        
        # Ensure logged in
        if not self.login():
            self.logger.error("Not authenticated")
            return None
        
        # Prepare request
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        
        payload = {
            "exchange": exchange,
            "symboltoken": clean_token,
            "interval": interval,
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M")
        }
        
        try:
            self.logger.info(f"Fetching candles for token {clean_token}")
            
            response = self.session.post(
                self.base_url + self.endpoints['candle'],
                json=payload,
                timeout=20
            )
            
            self.logger.debug(f"Candle response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    candles = data.get('data', [])
                    if candles:
                        self.cache.set(cache_key, candles)
                        self.metrics['successful_calls'] += 1
                        self.logger.info(f"Got {len(candles)} candles for token {clean_token}")
                        return candles
                    else:
                        self.logger.warning(f"No candle data for token {clean_token}")
                        return []
                else:
                    self.logger.error(f"API error: {data}")
                    return None
            else:
                self.logger.error(f"HTTP error: {response.status_code}")
                return None
                
        except Exception as e:
            self.metrics['failed_calls'] += 1
            self.logger.error(f"Error fetching candles: {e}")
            return None
    
    def load_symbol_master(self, url: str = None) -> bool:
        """Load symbol master"""
        if url is None:
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        
        try:
            self.logger.info("Loading symbol master...")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Build symbol mappings
                self.symbols = {}
                self.token_to_symbol = {}
                
                for item in data:
                    token = str(item["token"])
                    symbol = item["symbol"]
                    self.symbols[token] = {
                        "symbol": symbol,
                        "name": item.get("name", ""),
                        "expiry": item.get("expiry", ""),
                        "exchange": item.get("exch_seg", "NSE")
                    }
                    self.token_to_symbol[token] = symbol
                
                self.logger.info(f"Loaded {len(self.symbols)} symbols")
                return True
            else:
                self.logger.error(f"Failed to load symbols: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error loading symbols: {e}")
            return False
    
    def get_symbol(self, token: str) -> str:
        """Get symbol name for token"""
        try:
            clean_token = str(token).split('.')[0]
            
            # Check common symbols first
            if clean_token in self.common_symbols:
                return self.common_symbols[clean_token]
            
            # Check loaded symbols
            if clean_token in self.token_to_symbol:
                return self.token_to_symbol[clean_token]
            
            # Check symbols dict
            if clean_token in self.symbols:
                return self.symbols[clean_token].get('symbol', clean_token)
            
        except Exception as e:
            self.logger.error(f"Error getting symbol for {token}: {e}")
        
        return f"TKN-{clean_token}"
    
    def health_check(self) -> Dict:
        """Perform health check"""
        return {
            'status': 'healthy' if self.auth_token else 'unauthenticated',
            'timestamp': datetime.now().isoformat(),
            'authenticated': self.auth_token is not None,
            'token_expiry': self.token_expiry.isoformat() if self.token_expiry else None,
            'metrics': self.metrics.copy(),
            'cache_stats': self.cache.get_stats()
        }
    
    def close(self):
        """Close session"""
        if self.session:
            self.session.close()
        self.logger.info("Client closed")