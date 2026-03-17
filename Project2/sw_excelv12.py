# ===============================
# sw_excelv12.py - Main Application with All Fixes
# ===============================

import threading
import time
from datetime import datetime
from typing import List, Set

from utils.logger import get_logger
from utils.helpers import get_market_status
from config.settings import config
from config.credentials import API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET

from angel_api.client import AngelAPIClient
from excel.simple_manager import SimpleExcelManager
from indicators.calculator import IndicatorCalculator
from indicators.alerts import AlertSystem
from data.processor import TickProcessor
from backup.manager import TokenBackupManager
from backup.integration import TokenBackupIntegration
from angel_api.websocket_wrapper import start_stream, subscribe
from utils.symbol_loader import SymbolLoader

class LiveFeedApp:
    """Main application controller"""
    
    def __init__(self):
        self.logger = get_logger('LiveFeedApp')
        
        # Load symbols from CSV
        self.symbol_loader = SymbolLoader("symbol_mapping.csv")
        self.symbol_loader.load()
        self.logger.info(f"Loaded {len(self.symbol_loader.token_to_symbol)} symbols from CSV")

        # Initialize components
        self.api_client = AngelAPIClient(
            api_key=API_KEY,
            client_id=CLIENT_ID,
            password=PASSWORD,
            totp_secret=TOTP_SECRET
        )
        
        self.excel_mgr = SimpleExcelManager(file_name=config.EXCEL_FILE)
        self.excel_mgr.set_symbol_master(self.api_client)
        
        self.alert_system = AlertSystem(thresholds=config.ALERT_THRESHOLDS)
        self.indicator_calc = IndicatorCalculator(self.api_client)
        self.backup_mgr = TokenBackupManager()
        self.backup_integration = TokenBackupIntegration(self.excel_mgr, self.backup_mgr)
        
        # Processor with symbol loader
        self.processor = TickProcessor(
            self.indicator_calc, 
            self.alert_system,
            self.api_client,
            self.symbol_loader
        )
        
        # State
        self.running = False
        self.active_tokens = set()
        
        # Timers for batch updates
        self._last_batch = 0      # Timer for Excel batch updates
        self._last_check = 0      # Timer for checking new tokens
        
    def start(self):
        """Start the application"""
        self.logger.info("=" * 60)
        self.logger.info("Starting Live Feed Application v12")
        self.logger.info("=" * 60)
        
        # Load symbols
        self.logger.info("Loading symbol master...")
        self.api_client.load_symbol_master()
        
        # Initialize Excel
        self.logger.info("Initializing Excel...")
        if not self.excel_mgr.initialize():
            self.logger.error("Failed to initialize Excel")
            return
        
        # Read initial tokens
        instruments = self.excel_mgr.read_instruments()
        self.active_tokens = {token for token, _ in instruments}
        self.logger.info(f"Found {len(self.active_tokens)} tokens: {self.active_tokens}")
        
        # Start processor
        self.logger.info("Starting tick processor...")
        self.processor.start()
        self.processor.update_subscriptions(self.active_tokens)
        
        # Ensure symbol loader is set
        self.processor.symbol_loader = self.symbol_loader
        self.excel_mgr.symbol_loader = self.symbol_loader
        
        # Start WebSocket
        self.logger.info("Starting WebSocket connection...")
        self.ws_thread = threading.Thread(
            target=start_stream,
            args=(self.processor.add_tick,),
            daemon=True
        )
        self.ws_thread.start()
        
        # Wait for WebSocket to connect
        self.logger.info("Waiting for WebSocket to connect...")
        time.sleep(5)
        
        # Subscribe to tokens with retry
        if self.active_tokens:
            self.logger.info(f"Subscribing to {len(self.active_tokens)} tokens")
            self._subscribe_with_retry(list(self.active_tokens))
        
        # Start backup scheduler
        self.logger.info("Starting backup scheduler...")
        self.backup_integration.start_auto_backup()
        
        self.running = True
        self.logger.info("System ready!")
        self.logger.info("Add tokens to Instruments sheet (column A)")
        
        # MAIN LOOP
        try:
            while self.running:
                self._main_loop_iteration()
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            self.logger.error(f"Unexpected error in main loop: {e}")
            self.stop()
    
    def _subscribe_with_retry(self, tokens: List[str], max_attempts: int = 3):
        """Subscribe to tokens with retry logic"""
        for attempt in range(max_attempts):
            try:
                self.logger.info(f"Subscription attempt {attempt + 1}/{max_attempts}")
                result = subscribe([{"exchangeType": 1, "tokens": tokens}])
                if result:
                    self.logger.info(f"Successfully subscribed on attempt {attempt + 1}")
                    return True
                else:
                    self.logger.warning(f"Subscription returned False on attempt {attempt + 1}")
            except Exception as e:
                self.logger.warning(f"Subscription attempt {attempt + 1} failed: {e}")
            
            if attempt < max_attempts - 1:
                wait_time = (attempt + 1) * 2
                self.logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
        
        self.logger.error("Failed to subscribe after all attempts")
        return False
    
    def _main_loop_iteration(self):
        """Super fast main loop with batch Excel updates"""
        now = time.time()
    
        # Get pending updates
        updates = self.processor.get_excel_updates()
    
        # Group by token (keep latest only)
        latest = {}
        for tick, ind, alerts in updates:
            latest[tick.token] = (tick, ind, alerts)
    
        # Only update if we have data and enough time has passed
        if latest and now - self._last_batch > 0.5:  # 500ms minimum between batches
            self.excel_mgr.fast_update_all_rows(latest)
            self._last_batch = now
    
        # Check for new tokens every 2 seconds
        if now - self._last_check > 2:
            self._check_excel_changes()
            self._last_check = now
                
    def _check_excel_changes(self):
        """Check for changes in Instruments sheet"""
        try:
            instruments = self.excel_mgr.read_instruments()
            new_tokens = {token for token, _ in instruments}
            
            if new_tokens != self.active_tokens:
                added = new_tokens - self.active_tokens
                removed = self.active_tokens - new_tokens
                
                if added:
                    self.logger.info(f"New tokens detected: {added}")
                    self._subscribe_with_retry(list(added))
                
                if removed:
                    self.logger.info(f"Tokens removed: {removed}")
                    self.excel_mgr.cleanup_removed(new_tokens)
                
                self.active_tokens = new_tokens
                self.processor.update_subscriptions(self.active_tokens)
                
        except Exception as e:
            self.logger.error(f"Error checking Excel changes: {e}")
    
    def stop(self):
        """Stop the application"""
        self.logger.info("Stopping application...")
        self.running = False
        
        # Stop components
        if hasattr(self, 'processor'):
            self.logger.info("Stopping tick processor...")
            self.processor.stop()
        
        if hasattr(self, 'backup_integration'):
            self.logger.info("Stopping backup scheduler...")
            self.backup_integration.stop_auto_backup()
        
        # Create final backup
        if self.active_tokens:
            self.logger.info("Creating final backup...")
            self.backup_integration.backup_current_tokens("session_end")
        
        # Close Excel
        if hasattr(self, 'excel_mgr'):
            self.logger.info("Closing Excel...")
            self.excel_mgr.close()
        
        if hasattr(self, 'api_client'):
            self.logger.info("Closing API client...")
            self.api_client.close()
        
        self.logger.info("Application stopped. Goodbye!")

# ===============================
# ENTRY POINT
# ===============================

if __name__ == "__main__":
    app = LiveFeedApp()
    
    try:
        app.start()
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt, stopping...")
        app.stop()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        app.stop()