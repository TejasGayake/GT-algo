# ===============================
# excel/manager.py - Excel Manager with Complete COM Handling
# ===============================

import xlwings as xw
import threading
import queue
import time
import pythoncom
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple

from utils.logger import get_logger
from utils.helpers import format_token
from data.models import TickData, IndicatorData

class ExcelManager:
    """Centralized Excel operations with thread safety and COM initialization"""
    
    def __init__(self, file_name: str = "Live_Feed_Data.xlsx"):
        self.file_name = file_name
        self.logger = get_logger('ExcelManager')
        
        # Excel objects
        self.app = None
        self.wb = None
        self.sheet_live = None
        self.sheet_inst = None
        
        # Row mapping
        self.row_map = {}  # token -> row
        self.next_row = 2
        self.lock = threading.RLock()
        
        # Update queue
        self.update_queue = queue.Queue(maxsize=10000)
        self.running = False
        self.update_thread = None
        
        # COM initialization tracking
        self.main_com_initialized = False
        self.worker_com_initialized = False
        
        # Headers
        self.headers = [
            "SYMBOL", "TOKEN", "TIME", "LTP", "CHANGE", "%CHANGE",
            "VOLUME", "VOL AVG", "VOL RATIO", "OPEN", "HIGH", "LOW",
            "52W HIGH", "52W LOW", "SMA20", "SMA40", "SMA200", "RSI14",
            "VWAP", "SUPPORT", "RESISTANCE", "VOLATILITY", "ALERTS"
        ]
    
    def initialize(self) -> bool:
        """Initialize Excel connection"""
        try:
            # Initialize COM for main thread
            self._ensure_com_initialized()
            
            self.app = xw.App(visible=True)
            self.app.display_alerts = False
            self.app.screen_updating = False  # Faster updates
            
            # Open or create workbook
            file_path = Path(self.file_name)
            if file_path.exists():
                self.wb = self.app.books.open(str(file_path))
                self.logger.info(f"Opened existing file: {self.file_name}")
            else:
                self.wb = self.app.books.add()
                self.wb.save(str(file_path))
                self.logger.info(f"Created new file: {self.file_name}")
            
            # Setup sheets
            self._setup_sheets()
            
            # Start update thread
            self.running = True
            self.update_thread = threading.Thread(target=self._update_worker, daemon=True)
            self.update_thread.start()
            
            self.logger.info("✅ Excel manager initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Excel initialization failed: {e}")
            return False
    
    def _ensure_com_initialized(self):
        """Ensure COM is initialized for the current thread"""
        try:
            # Check if COM is already initialized
            pythoncom.CoInitialize()
            self.logger.debug(f"COM initialized for thread {threading.current_thread().name}")
            return True
        except Exception as e:
            # COM might already be initialized
            self.logger.debug(f"COM initialization skipped: {e}")
            return False
    
    def _setup_sheets(self):
        """Setup Excel sheets with formatting"""
        try:
            # LIVE sheet
            if "LIVE" in [s.name for s in self.wb.sheets]:
                self.sheet_live = self.wb.sheets["LIVE"]
            else:
                # Rename first sheet to LIVE
                self.sheet_live = self.wb.sheets[0]
                self.sheet_live.name = "LIVE"
            
            # Instruments sheet
            try:
                self.sheet_inst = self.wb.sheets["Instruments"]
            except:
                self.sheet_inst = self.wb.sheets.add("Instruments")
                self.sheet_inst.range("A1").value = "ExchangeType"
                self.sheet_inst.range("B1").value = "Token"
                self.sheet_inst.range("A2").value = 1  # Default NSE
            
            # Format headers
            self._format_headers()
            
        except Exception as e:
            self.logger.error(f"Error setting up sheets: {e}")
            raise
    
    def _format_headers(self):
        """Format header row"""
        try:
            last_col = chr(64 + len(self.headers))
            
            # Clear existing content in row 1
            self.sheet_live.range(f"A1:{last_col}1").clear_contents()
            
            # Write headers
            self.sheet_live.range("A1").value = [self.headers]
            
            # Format header row
            header_range = self.sheet_live.range(f"A1:{last_col}1")
            header_range.font.bold = True
            header_range.color = (0, 100, 200)  # Blue
            header_range.font.color = (255, 255, 255)  # White
            
            # Set column widths
            for i, col in enumerate(range(ord('A'), ord(last_col) + 1)):
                col_letter = chr(col)
                try:
                    if col_letter in ['A', 'B']:  # Symbol, Token
                        self.sheet_live.range(f"{col_letter}:{col_letter}").column_width = 12
                    elif col_letter == 'C':  # Time
                        self.sheet_live.range(f"{col_letter}:{col_letter}").column_width = 10
                    elif col_letter in ['D', 'E', 'F', 'G', 'H', 'I']:  # Price columns
                        self.sheet_live.range(f"{col_letter}:{col_letter}").column_width = 10
                    elif col_letter == 'W':  # Alerts column
                        self.sheet_live.range(f"{col_letter}:{col_letter}").column_width = 20
                    else:
                        self.sheet_live.range(f"{col_letter}:{col_letter}").column_width = 10
                except:
                    # Skip if column width setting fails
                    pass
            
        except Exception as e:
            self.logger.error(f"Error formatting headers: {e}")
    
    def read_instruments(self) -> List[Tuple[str, int]]:
        """Read instruments from Excel"""
        try:
            # Ensure COM is initialized for this thread
            self._ensure_com_initialized()
            
            # Check if sheet is available
            if self.sheet_inst is None:
                self.logger.error("Instruments sheet not initialized")
                return []
            
            # Find last row with data
            try:
                last_row = self.sheet_inst.range(
                    "B" + str(self.sheet_inst.cells.last_cell.row)
                ).end('up').row
            except Exception as e:
                self.logger.error(f"Error finding last row: {e}")
                return []
            
            if last_row < 2:
                return []
            
            # Read values
            try:
                values = self.sheet_inst.range(f"B2:B{last_row}").value
            except Exception as e:
                self.logger.error(f"Error reading values: {e}")
                return []
            
            instruments = []
            if isinstance(values, list):
                for cell in values:
                    if cell and str(cell).strip():
                        try:
                            token, exch = str(cell).strip().split("-")
                            instruments.append((token.strip(), int(exch)))
                        except:
                            # Default to NSE if no exchange
                            instruments.append((str(cell).strip(), 1))
            elif values:
                try:
                    token, exch = str(values).strip().split("-")
                    instruments.append((token.strip(), int(exch)))
                except:
                    instruments.append((str(values).strip(), 1))
            
            if instruments:
                self.logger.debug(f"Read {len(instruments)} instruments")
            
            return instruments
            
        except Exception as e:
            self.logger.error(f"Error reading instruments: {e}")
            return []
    
    def update_row(self, tick: TickData, indicators: IndicatorData, alerts: List[str]):
        """Queue row update"""
        try:
            self.update_queue.put((tick, indicators, alerts), timeout=1)
        except queue.Full:
            self.logger.warning("Update queue full, dropping update")
    
    def _update_worker(self):
        """Background thread for Excel updates"""
        thread_name = threading.current_thread().name
        self.logger.info(f"Update worker thread started: {thread_name}")
        
        # Initialize COM for this thread
        try:
            pythoncom.CoInitialize()
            self.worker_com_initialized = True
            self.logger.info(f"COM initialized for update worker: {thread_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize COM for worker: {e}")
        
        batch = []
        last_flush = time.time()
        
        while self.running:
            try:
                # Collect updates
                try:
                    item = self.update_queue.get(timeout=0.1)
                    batch.append(item)
                except queue.Empty:
                    pass
                
                # Flush batch
                if len(batch) >= 50 or (batch and time.time() - last_flush > 1.0):
                    if batch:
                        self._flush_batch(batch)
                        batch = []
                        last_flush = time.time()
                
                time.sleep(0.01)
                
            except Exception as e:
                self.logger.error(f"Update worker error: {e}")
                time.sleep(1)
        
        # Uninitialize COM when done
        if self.worker_com_initialized:
            try:
                pythoncom.CoUninitialize()
                self.logger.info("COM uninitialized for worker")
            except:
                pass
    
    def _flush_batch(self, batch: List[Tuple]):
        """Write batch updates to Excel"""
        if not batch:
            return
        
        try:
            with self.lock:
                # Turn off screen updating for batch
                self.app.screen_updating = False
                
                for tick, indicators, alerts in batch:
                    token = tick.token
                    
                    # Get or create row
                    if token not in self.row_map:
                        self.row_map[token] = self.next_row
                        self.next_row += 1
                    
                    row = self.row_map[token]
                    
                    # Calculate volume ratio
                    vol_ratio = (tick.volume / indicators.volume_avg 
                               if indicators and indicators.volume_avg > 0 else 0)
                    
                    # Prepare data
                    row_data = [
                        tick.symbol,
                        token,
                        tick.timestamp.strftime("%H:%M:%S"),
                        tick.ltp,
                        tick.change,
                        tick.change_percent,
                        tick.volume,
                        round(indicators.volume_avg) if indicators else 0,
                        round(vol_ratio, 2),
                        tick.open,
                        tick.high,
                        tick.low,
                        "",  # 52W high
                        "",  # 52W low
                        indicators.sma20 if indicators else "",
                        indicators.sma40 if indicators else "",
                        indicators.sma200 if indicators else "",
                        indicators.rsi14 if indicators else "",
                        indicators.vwap if indicators else "",
                        indicators.support if indicators else "",
                        indicators.resistance if indicators else "",
                        round(indicators.volatility * 100, 2) if indicators else "",
                        ", ".join(alerts) if alerts else ""
                    ]
                    
                    # Write to Excel
                    self.sheet_live.range(f"A{row}").value = [row_data]
                    
                    # Color coding
                    if tick.change > 0:
                        self.sheet_live.range(f"E{row}:F{row}").color = (200, 255, 200)  # Green
                    elif tick.change < 0:
                        self.sheet_live.range(f"E{row}:F{row}").color = (255, 200, 200)  # Red
                    
                    # RSI coloring
                    if indicators and indicators.rsi14:
                        if indicators.rsi14 > 70:
                            self.sheet_live.range(f"R{row}").color = (255, 200, 200)  # Overbought
                        elif indicators.rsi14 < 30:
                            self.sheet_live.range(f"R{row}").color = (200, 255, 200)  # Oversold
                
                # Turn screen updating back on
                self.app.screen_updating = True
                
        except Exception as e:
            self.logger.error(f"Batch flush error: {e}")
    
    def cleanup_removed(self, active_tokens: Set[str]):
        """Clean up rows for removed tokens"""
        with self.lock:
            removed = set(self.row_map.keys()) - active_tokens
            for token in removed:
                if token in self.row_map:
                    row = self.row_map[token]
                    # Clear row
                    self.sheet_live.range(f"A{row}:{chr(64+len(self.headers))}{row}").clear_contents()
                    del self.row_map[token]
                    self.logger.debug(f"Cleaned up token {token}")
    
    def write_tokens_to_excel(self, tokens: List[str]):
        """Write tokens to Instruments sheet"""
        try:
            # Ensure COM is initialized
            self._ensure_com_initialized()
            
            if self.sheet_inst is None:
                self.logger.error("Instruments sheet not initialized")
                return
            
            # Clear existing
            try:
                last_row = self.sheet_inst.range("B" + str(self.sheet_inst.cells.last_cell.row)).end('up').row
                if last_row >= 2:
                    self.sheet_inst.range(f"B2:B{last_row}").clear_contents()
            except Exception as e:
                self.logger.error(f"Error clearing existing tokens: {e}")
            
            # Write new tokens
            if tokens:
                # Convert to column format
                token_column = [[t] for t in tokens]
                self.sheet_inst.range("B2").value = token_column
            
            self.logger.info(f"Wrote {len(tokens)} tokens to Excel")
            
        except Exception as e:
            self.logger.error(f"Error writing tokens: {e}")
    
    def close(self):
        """Close Excel"""
        self.logger.info("Closing Excel...")
        self.running = False
        
        if self.update_thread:
            self.update_thread.join(timeout=5)
        
        try:
            if self.wb:
                self.wb.save()
                self.wb.close()
            if self.app:
                self.app.quit()
            
            self.logger.info("Excel closed")
        except Exception as e:
            self.logger.error(f"Error closing Excel: {e}")