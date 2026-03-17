# ===============================
# indicators/calculator.py - Fixed with better error handling
# ===============================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import threading
import time

from utils.logger import get_logger
from data.models import IndicatorData

class IndicatorCalculator:
    """Indicator calculations with caching"""
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.logger = get_logger('IndicatorCalculator')
        
        # Cache
        self.cache = {}  # token -> (IndicatorData, timestamp)
        self.cache_duration = 300  # 5 minutes
        self.cache_lock = threading.RLock()
        
        # Track API calls
        self.api_calls = 0
        self.failed_calls = 0
        
        # Default values for when API fails
        self.default_indicators = {
            'sma20': 0, 'sma40': 0, 'sma200': 0, 'rsi14': 50,
             'vwap': 0, 'prev_high': 0, 'prev_low': 0,
             'volume_avg': 0, 'volatility': 0, 'support': 0, 'resistance': 0
         }

    def calculate_indicators(self, token: str, force: bool = False) -> Optional[IndicatorData]:
        """Calculate indicators for a token"""
        current_time = datetime.now()
        clean_token = str(token).split('.')[0]

        # Check cache
        if not force:
            with self.cache_lock:
                if clean_token in self.cache:
                    data, timestamp = self.cache[clean_token]
                    if (current_time - timestamp).seconds < self.cache_duration:
                        self.logger.debug(f"Cache hit for {clean_token}")
                        return data

        try:
            self.logger.info(f"📊 Fetching indicators for token {clean_token}")

            # Fetch candles from API
            candles = self.api_client.get_candles(clean_token, days=5)
            self.api_calls += 1

            if not candles:
                self.logger.warning(f"⚠️ No candle data for {clean_token}")
                self.failed_calls += 1
                return self._create_default_indicators(clean_token, current_time)

            if len(candles) < 20:
                self.logger.warning(f"⚠️ Insufficient candles for {clean_token}: got {len(candles)}, need at least 20")
                self.failed_calls += 1
                # Still try to calculate with what we have
                if len(candles) > 0:
                    result = self._calculate_from_candles(clean_token, candles, current_time)
                    self.logger.info(f"✅ Calculated indicators for {clean_token} with limited data ({len(candles)} candles)")
                else:
                    result = self._create_default_indicators(clean_token, current_time)
            else:
                # Calculate indicators from candles
                result = self._calculate_from_candles(clean_token, candles, current_time)
                self.logger.info(f"✅ Successfully calculated indicators for {clean_token} with {len(candles)} candles")

            # Log the calculated values for debugging
            if result:
                self.logger.info(f"📊 {clean_token} indicators - Volume Avg: {result.volume_avg}, SMA20: {result.sma20:.2f}, RSI14: {result.rsi14:.1f}")

            # Update cache
            with self.cache_lock:
                self.cache[clean_token] = (result, current_time)

            return result

        except Exception as e:
            self.logger.error(f"❌ Error calculating indicators for {clean_token}: {e}")
            import traceback
            traceback.print_exc()
            self.failed_calls += 1
            return self._create_default_indicators(clean_token, current_time)

    def _calculate_from_candles(self, token: str, candles: List, current_time: datetime) -> IndicatorData:
        """Calculate indicators from candle data"""
        try:
            self.logger.info(f"🔧 Calculating indicators from {len(candles)} candles for {token}")

            # Convert to DataFrame
            df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])

            # Convert to numeric
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col])

            self.logger.info(f"📊 DataFrame shape: {df.shape}")

            # Calculate all indicators
            indicators = {}

            # Moving averages
            indicators['sma20'] = self._safe_series(df['close'].rolling(20).mean())
            indicators['sma40'] = self._safe_series(df['close'].rolling(40).mean())
            indicators['sma200'] = self._safe_series(df['close'].rolling(200).mean())

            # RSI (14 periods)
            indicators['rsi14'] = self._calculate_rsi(df['close'])

            # VWAP
            indicators['vwap'] = self._calculate_vwap(df)

            # Previous day high/low
            indicators['prev_high'] = float(df['high'].iloc[-2]) if len(df) > 1 else float(df['high'].iloc[-1])
            indicators['prev_low'] = float(df['low'].iloc[-2]) if len(df) > 1 else float(df['low'].iloc[-1])

            # Average volume (20 days)
            volume_series = df['volume'].tail(20)
            indicators['volume_avg'] = float(volume_series.mean()) if len(volume_series) > 0 else 0

            # Volatility (20 days annualized)
            returns = df['close'].pct_change().dropna()
            indicators['volatility'] = float(returns.std() * np.sqrt(252)) if len(returns) > 5 else 0

            # Support and resistance
            indicators['support'] = float(df['low'].tail(20).min())
            indicators['resistance'] = float(df['high'].tail(20).max())

            # Log individual calculations for debugging
            self.logger.info(f"📈 {token} calculation results:")
            self.logger.info(f"   - SMA20: {indicators['sma20']:.2f}")
            self.logger.info(f"   - SMA40: {indicators['sma40']:.2f}")
            self.logger.info(f"   - SMA200: {indicators['sma200']:.2f}")
            self.logger.info(f"   - RSI14: {indicators['rsi14']:.1f}")
            self.logger.info(f"   - VWAP: {indicators['vwap']:.2f}")
            self.logger.info(f"   - Volume Avg: {indicators['volume_avg']:.0f}")
            self.logger.info(f"   - Support: {indicators['support']:.2f}")
            self.logger.info(f"   - Resistance: {indicators['resistance']:.2f}")

            # Create result
            return IndicatorData(
                token=token,
                timestamp=current_time,
                sma20=indicators.get('sma20', 0),
                sma40=indicators.get('sma40', 0),
                sma200=indicators.get('sma200', 0),
                rsi14=indicators.get('rsi14', 50),
                vwap=indicators.get('vwap', 0),
                prev_high=indicators.get('prev_high', 0),
                prev_low=indicators.get('prev_low', 0),
                volume_avg=indicators.get('volume_avg', 0),
                volatility=indicators.get('volatility', 0),
                support=indicators.get('support', 0),
                resistance=indicators.get('resistance', 0)
            )

        except Exception as e:
            self.logger.error(f"❌ Error in _calculate_from_candles for {token}: {e}")
            import traceback
            traceback.print_exc()
            return self._create_default_indicators(token, current_time)

    def _create_default_indicators(self, token: str, current_time: datetime) -> IndicatorData:
        """Create default indicators when calculation fails"""
        self.logger.warning(f"⚠️ Using default indicators for {token}")
        return IndicatorData(
            token=token,
            timestamp=current_time,
            sma20=0,
            sma40=0,
            sma200=0,
            rsi14=50,
            vwap=0,
            prev_high=0,
            prev_low=0,
            volume_avg=0,
            volatility=0,
            support=0,
            resistance=0
        )    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI"""
        try:
            delta = prices.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            
            avg_gain = gain.rolling(period).mean()
            avg_loss = loss.rolling(period).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
        except:
            return 50
    
    def _calculate_vwap(self, df: pd.DataFrame) -> float:
        """Calculate VWAP"""
        try:
            tp = (df['high'] + df['low'] + df['close']) / 3
            vwap = (tp * df['volume']).cumsum() / df['volume'].cumsum()
            return float(vwap.iloc[-1]) if not pd.isna(vwap.iloc[-1]) else 0
        except:
            return 0
    
    def _safe_series(self, series: pd.Series) -> float:
        """Safely get last value from series"""
        try:
            if len(series) > 0 and not pd.isna(series.iloc[-1]):
                return float(series.iloc[-1])
            return 0
        except:
            return 0
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        with self.cache_lock:
            return {
                'size': len(self.cache),
                'api_calls': self.api_calls,
                'failed_calls': self.failed_calls
            }