# test_indicators.py - Updated
from config.credentials import API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET
from angel_api.client import AngelAPIClient
from indicators.calculator import IndicatorCalculator
from utils.logger import get_logger


client = AngelAPIClient(API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET)
if client.login():
    self.logger.info("✅ Login successful")
    calc = IndicatorCalculator(client)
    indicators = calc.calculate_indicators("2885", force=True)
    if indicators:
        self.logger.debug(f"RSI: {indicators.rsi14}")
else:
    self.logger.error("❌ Login failed")