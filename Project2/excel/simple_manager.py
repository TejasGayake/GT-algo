# ===============================
# excel/simple_manager.py - Complete Excel Manager
# ===============================

import xlwings as xw
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
import pythoncom

from utils.logger import get_logger
from data.models import TickData, IndicatorData

class SimpleExcelManager:
    """Single-threaded Excel operations with robust COM handling"""
    
    def __init__(self, file_name: str = "Live_Feed_Data.xlsx"):
        self.file_name = file_name
        self.logger = get_logger('SimpleExcelManager')
        
        # Excel objects
        self.app = None
        self.wb = None
        self.sheet_live = None
        self.sheet_inst = None
        
        # Row mapping
        self.row_map = {}  # token -> row
        self.next_row = 2
        
        # Headers for LIVE sheet
        self.live_headers = [
            "SYMBOL", "TOKEN", "TIME", "LTP", "CHANGE", "%CHANGE",
            "VOLUME", "VOL AVG", "VOL RATIO", "OPEN", "HIGH", "LOW",
            "52W HIGH", "52W LOW", "SMA20", "SMA40", "SMA200", "RSI14",
            "VWAP", "SUPPORT", "RESISTANCE", "VOLATILITY", "ALERTS"
        ]
        
        # Headers for INSTRUMENTS sheet
        self.instrument_headers = ["TOKEN", "SYMBOL", "EXCHANGE"]
        
        # Symbol master reference
        self.symbol_master = None
        self.symbol_loader = None  # ADD THIS LINE
        
        # COM state
        self.com_initialized = False
        
        # Statistics
        self.update_count = 0
        self.last_log_time = time.time()
    
    def set_symbol_master(self, symbol_master):
        """Set the symbol master for fetching symbols"""
        self.symbol_master = symbol_master
        self.logger.info("Symbol master set")
    
    def set_symbol_loader(self, symbol_loader):  # ADD THIS METHOD
        """Set the symbol loader for the Excel manager"""
        self.symbol_loader = symbol_loader
        self.logger.info("Symbol loader set for Excel manager")
    
    def _ensure_com(self):
        """Ensure COM is initialized for current thread"""
        try:
            pythoncom.CoInitialize()
            self.com_initialized = True
            return True
        except:
            return False
    
    def _ensure_excel_alive(self):
        """Check if Excel is still alive and reconnect if needed"""
        try:
            if self.app is None:
                return False
            
            # Try a simple operation to check if Excel is responsive
            self.app.books.count
            return True
        except Exception as e:
            self.logger.warning(f"Excel connection lost: {e}")
            return self._reconnect_excel()
    
    def _reconnect_excel(self):
        """Reconnect to Excel"""
        try:
            self.logger.info("Attempting to reconnect to Excel...")
            
            # Try to get existing Excel instance or create new
            try:
                self.app = xw.App(visible=True)
            except:
                self.app = xw.App(visible=True)
            
            self.app.display_alerts = False
            self.app.screen_updating = True
            
            # Open workbook
            file_path = Path(self.file_name)
            if file_path.exists():
                self.wb = self.app.books.open(str(file_path))
                self.logger.info(f"Reopened file: {self.file_name}")
            else:
                self.wb = self.app.books.add()
                self.wb.save(str(file_path))
                self.logger.info(f"Created new file: {self.file_name}")
            
            # Get sheets
            if "LIVE" in [s.name for s in self.wb.sheets]:
                self.sheet_live = self.wb.sheets["LIVE"]
            else:
                self.sheet_live = self.wb.sheets[0]
                self.sheet_live.name = "LIVE"
            
            if "Instruments" in [s.name for s in self.wb.sheets]:
                self.sheet_inst = self.wb.sheets["Instruments"]
            else:
                self.sheet_inst = self.wb.sheets.add("Instruments")
                self._format_instrument_headers()
            
            self.logger.info("✅ Reconnected to Excel")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reconnect to Excel: {e}")
            return False
    
    def initialize(self) -> bool:
        """Initialize Excel connection"""
        try:
            self._ensure_com()
            
            # Start Excel
            self.app = xw.App(visible=True)
            self.app.display_alerts = False
            self.app.screen_updating = True
            
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
            
            self.logger.info("✅ Excel manager initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Excel initialization failed: {e}")
            return False
    
    def _setup_sheets(self):
        """Setup Excel sheets with formatting"""
        try:
            # LIVE sheet
            if "LIVE" in [s.name for s in self.wb.sheets]:
                self.sheet_live = self.wb.sheets["LIVE"]
                self.logger.info("Using existing LIVE sheet")
            else:
                self.sheet_live = self.wb.sheets[0]
                self.sheet_live.name = "LIVE"
                self.logger.info("Created LIVE sheet")
            
            # INSTRUMENTS sheet
            try:
                self.sheet_inst = self.wb.sheets["Instruments"]
                self.logger.info("Using existing Instruments sheet")
            except:
                self.sheet_inst = self.wb.sheets.add("Instruments")
                self.logger.info("Created Instruments sheet")
            
            # Format headers
            self._format_live_headers()
            self._format_instrument_headers()
            self._add_instructions()
            
        except Exception as e:
            self.logger.error(f"Error setting up sheets: {e}")
            raise
    
    def _format_live_headers(self):
        """Format LIVE sheet header row"""
        try:
            last_col = chr(64 + len(self.live_headers))
            
            # Write headers
            self.sheet_live.range("A1").value = [self.live_headers]
            
            # Format header row
            header_range = self.sheet_live.range(f"A1:{last_col}1")
            header_range.font.bold = True
            header_range.color = (0, 100, 200)  # Blue
            header_range.font.color = (255, 255, 255)  # White
            
            # Set column widths
            self.sheet_live.range("A:A").column_width = 12  # SYMBOL
            self.sheet_live.range("B:B").column_width = 10  # TOKEN
            self.sheet_live.range("C:C").column_width = 10  # TIME
            self.sheet_live.range("W:W").column_width = 20  # ALERTS
            
            self.logger.info("LIVE sheet headers formatted")
            
        except Exception as e:
            self.logger.error(f"Error formatting LIVE headers: {e}")
    
    def _format_instrument_headers(self):
        """Format INSTRUMENTS sheet header row"""
        try:
            # Clear existing
            self.sheet_inst.range("A1:C1").clear_contents()
            
            # Write headers
            self.sheet_inst.range("A1").value = [self.instrument_headers]
            
            # Format header row
            header_range = self.sheet_inst.range("A1:C1")
            header_range.font.bold = True
            header_range.color = (0, 100, 200)  # Blue
            header_range.font.color = (255, 255, 255)  # White
            
            # Set column widths
            self.sheet_inst.range("A:A").column_width = 15  # TOKEN
            self.sheet_inst.range("B:B").column_width = 20  # SYMBOL
            self.sheet_inst.range("C:C").column_width = 15  # EXCHANGE
            
            self.logger.info("Instruments sheet headers formatted")
            
        except Exception as e:
            self.logger.error(f"Error formatting Instruments headers: {e}")
    
    def _prepare_row_data(self, tick, indicators, alerts):
        """Prepare a single row of data for Excel"""
        vol_ratio = 0
        if indicators and indicators.volume_avg and indicators.volume_avg > 0:
            vol_ratio = tick.volume / indicators.volume_avg
        
        return [
            tick.symbol,
            tick.token,
            tick.timestamp.strftime("%H:%M:%S"),
            tick.ltp,
            tick.change,
            tick.change_percent,
            tick.volume,
            round(indicators.volume_avg) if indicators and indicators.volume_avg else "",
            round(vol_ratio, 2) if vol_ratio else "",
            tick.open,
            tick.high,
            tick.low,
            tick.week_52_high, 
            tick.week_52_low,   
            round(indicators.sma20, 2) if indicators and indicators.sma20 else "",
            round(indicators.sma40, 2) if indicators and indicators.sma40 else "",
            round(indicators.sma200, 2) if indicators and indicators.sma200 else "",
            round(indicators.rsi14, 2) if indicators and indicators.rsi14 else "",
            round(indicators.vwap, 2) if indicators and indicators.vwap else "",
            round(indicators.support, 2) if indicators and indicators.support else "",
            round(indicators.resistance, 2) if indicators and indicators.resistance else "",
            round(indicators.volatility * 100, 2) if indicators and indicators.volatility else "",
            ", ".join(alerts) if alerts else ""
        ]

    def fast_update_all_rows(self, all_tokens_data):
        """
        Update ALL rows in ONE operation - SUPER FAST!
        """
        try:
            # Turn off Excel's brain
            self.app.screen_updating = False
            self.app.calculation = 'manual'
    
            if not all_tokens_data:
                return
    
            # Prepare data for ALL rows at once
            rows_data = []
            rows_range = []
            min_row = 999999
            max_row = 0
    
            # Keep track of tokens we're updating in this batch
            tokens_in_batch = set()
            
            for token, (tick, indicators, alerts) in all_tokens_data.items():
                # Create row if it doesn't exist
                if token not in self.row_map:
                    self.row_map[token] = self.next_row
                    self.next_row += 1
                    self.logger.debug(f"Created row {self.row_map[token]} for {tick.symbol}")
    
                row = self.row_map[token]
                min_row = min(min_row, row)
                max_row = max(max_row, row)
                rows_range.append(row)
                tokens_in_batch.add(token)
    
                # Prepare row data
                row_data = self._prepare_row_data(tick, indicators, alerts)
                rows_data.append((row, row_data))
    
            if not rows_data:
                return
    
            # Create a complete 2D array for the entire range
            height = max_row - min_row + 1
            width = len(self.live_headers)
    
            # IMPORTANT: First, read the CURRENT Excel data for this range
            # This preserves data for rows NOT in this batch
            current_data = self.sheet_live.range(
                f"A{min_row}:{chr(64+width)}{max_row}"
            ).value
    
            # If current_data is None or wrong shape, create empty array
            if not current_data or len(current_data) != height:
                current_data = [[''] * width for _ in range(height)]
    
            # Update ONLY the rows we have new data for
            for (row, data), orig_row in zip(rows_data, rows_range):
                current_data[orig_row - min_row] = data
    
            # Write everything back in ONE operation
            range_str = f"A{min_row}:{chr(64+width)}{max_row}"
            self.sheet_live.range(range_str).value = current_data
    
            self.logger.info(f"⚡ Fast update: {len(rows_data)} rows in one batch")
    
        except Exception as e:
            self.logger.error(f"Fast update error: {e}")
        finally:
            self.app.screen_updating = True
            self.app.calculation = 'automatic'
    
    
    def _add_instructions(self):
        """Add instructions to the sheet"""
        try:
            self.sheet_inst.range("E1").value = "INSTRUCTIONS:"
            self.sheet_inst.range("E1").font.bold = True
            self.sheet_inst.range("E1").font.color = (0, 100, 200)
            
            instructions = [
                ["1. Enter TOKEN numbers in column A (e.g., 3045)"],
                ["2. SYMBOL column (B) will be auto-filled automatically"],
                ["3. EXCHANGE column (C) will be auto-filled as 'NSE'"],
                ["4. Multiple tokens: Enter one token per row"],
                ["5. Save the file after adding tokens"]
            ]
            
            for i, instruction in enumerate(instructions, start=2):
                self.sheet_inst.range(f"E{i}").value = instruction
            
        except Exception as e:
            self.logger.error(f"Error adding instructions: {e}")
    
    def get_symbol_for_token(self, token: str) -> str:
        """Get symbol name for token from symbol master"""
        try:
            if self.symbol_loader and self.symbol_loader.loaded:
                symbol = self.symbol_loader.get_symbol(token)
                self.logger.debug(f"ExcelManager.get_symbol_for_token: {token} → {symbol}")
                return symbol
        except Exception as e:
            self.logger.error(f"Error getting symbol for {token}: {e}")

        return f"TKN-{token}"

    def read_instruments(self) -> List[Tuple[str, int]]:
        """Read tokens from Instruments sheet - IGNORE existing symbol column"""
        try:
            # Ensure COM is initialized
            self._ensure_com()

            # Ensure Excel is alive
            if not self._ensure_excel_alive():
                self.logger.warning("Excel not alive, skipping read")
                return []

            if self.sheet_inst is None:
                self.logger.error("Instruments sheet not initialized")
                return []

            # Find last row with data in column A
            try:
                last_row = self.sheet_inst.range(
                    "A" + str(self.sheet_inst.cells.last_cell.row)
                ).end('up').row
            except Exception as e:
                self.logger.error(f"Error finding last row: {e}")
                return []

            if last_row < 2:
                return []

            # Read token values from column A ONLY
            try:
                token_values = self.sheet_inst.range(f"A2:A{last_row}").value
            except Exception as e:
                self.logger.error(f"Error reading values: {e}")
                return []

            instruments = []

            if isinstance(token_values, list):
                for i, token in enumerate(token_values, start=2):
                    if token and str(token).strip():
                        # Clean the token (remove .0 if it's a float)
                        raw_token = str(token).strip()
                        clean_token = raw_token.split('.')[0]

                        # Get symbol name from loader (NOT from Excel)
                        symbol = self.get_symbol_for_token(clean_token)

                        # OPTIONAL: Update Excel with correct symbol (but don't rely on it)
                        try:
                            # Only write if we have a valid symbol and it's not TKN-
                            if symbol and not symbol.startswith("TKN-"):
                                self.sheet_inst.range(f"B{i}").value = symbol
                            else:
                                # Clear incorrect symbol if it exists
                                current = self.sheet_inst.range(f"B{i}").value
                                if current and current.startswith("TKN-"):
                                    self.sheet_inst.range(f"B{i}").clear_contents()
                        except:
                            pass
                        
                        # Auto-fill exchange column (C) as "NSE"
                        try:
                            self.sheet_inst.range(f"C{i}").value = "NSE"
                        except:
                            pass
                        
                        # Add to instruments list (ONLY the token, exchange is always 1 for NSE)
                        instruments.append((clean_token, 1))

            elif token_values:
                # Single token
                raw_token = str(token_values).strip()
                clean_token = raw_token.split('.')[0]

                # Get symbol name from loader
                symbol = self.get_symbol_for_token(clean_token)

                # OPTIONAL: Update Excel with correct symbol
                try:
                    if symbol and not symbol.startswith("TKN-"):
                        self.sheet_inst.range("B2").value = symbol
                    else:
                        current = self.sheet_inst.range("B2").value
                        if current and current.startswith("TKN-"):
                            self.sheet_inst.range("B2").clear_contents()
                except:
                    pass
                
                # Auto-fill exchange column (C) as "NSE"
                try:
                    self.sheet_inst.range("C2").value = "NSE"
                except:
                    pass
                
                instruments.append((clean_token, 1))

            # Fixed version:
            if instruments:
                token_list = [t[0] for t in instruments]
                self.logger.debug(f"Read {len(instruments)} tokens: {token_list}")
            
                # Log first few symbols for verification
                sample_tokens = token_list[:5]
                sample_symbols = [self.get_symbol_for_token(t) for t in sample_tokens]
                self.logger.info(f"Sample symbols (from loader): {dict(zip(sample_tokens, sample_symbols))}")
            
            return instruments

        except Exception as e:
            self.logger.error(f"Error reading instruments: {e}")
            return []
    
    def update_row(self, tick: TickData, indicators: IndicatorData, alerts: List[str]):
        """Update a single row in LIVE sheet"""
        try:
            # Ensure COM is initialized
            self._ensure_com()
            
            # Ensure Excel is alive
            if not self._ensure_excel_alive():
                return
            
            token = tick.token
            symbol = tick.symbol  # This should now be the actual symbol name
            
            # Get or create row
            if token not in self.row_map:
                self.row_map[token] = self.next_row
                self.next_row += 1
                self.logger.info(f"New row {self.row_map[token]} for {symbol} ({token})")
            
            row = self.row_map[token]
            
            # Calculate volume ratio
            vol_ratio = 0
            if indicators and hasattr(indicators, 'volume_avg') and indicators.volume_avg and indicators.volume_avg > 0:
                vol_ratio = tick.volume / indicators.volume_avg

            # Prepare data with proper error handling
            row_data = [
                tick.symbol,
                tick.token,
                tick.timestamp.strftime("%H:%M:%S"),
                tick.ltp,
                tick.change,
                tick.change_percent,
                tick.volume,
                round(indicators.volume_avg, 0) if indicators and indicators.volume_avg and indicators.volume_avg > 0 else "",
                round(vol_ratio, 2) if vol_ratio and vol_ratio > 0 else "",
                tick.open,
                tick.high,
                tick.low,
                tick.week_52_high if hasattr(tick, 'week_52_high') and tick.week_52_high else "",
                tick.week_52_low if hasattr(tick, 'week_52_low') and tick.week_52_low else "",
                round(indicators.sma20, 2) if indicators and indicators.sma20 and indicators.sma20 > 0 else "",
                round(indicators.sma40, 2) if indicators and indicators.sma40 and indicators.sma40 > 0 else "",
                round(indicators.sma200, 2) if indicators and indicators.sma200 and indicators.sma200 > 0 else "",
                round(indicators.rsi14, 2) if indicators and indicators.rsi14 and indicators.rsi14 > 0 else "",
                round(indicators.vwap, 2) if indicators and indicators.vwap and indicators.vwap > 0 else "",
                round(indicators.support, 2) if indicators and indicators.support and indicators.support > 0 else "",
                round(indicators.resistance, 2) if indicators and indicators.resistance and indicators.resistance > 0 else "",
                round(indicators.volatility * 100, 2) if indicators and indicators.volatility and indicators.volatility > 0 else "",
                ", ".join(alerts) if alerts else ""
            ]
            
            # Write to Excel
            self.sheet_live.range(f"A{row}").value = [row_data]
            
            # Color coding for change
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
            
            # Update statistics
            self.update_count += 1
            if time.time() - self.last_log_time > 60:  # Log every minute
                self.logger.info(f"Excel updates: {self.update_count} rows updated")
                self.last_log_time = time.time()
            
        except Exception as e:
            self.logger.error(f"Error updating row for {token}: {e}")
    
    def batch_update_all(self, all_data):
        """Update ALL rows in ONE operation"""
        self.app.screen_updating = False
        self.app.calculation = 'manual'

        # Prepare 2D array for all rows
        rows = []
        for token, data in all_data.items():
            if token in self.row_map:
                rows.append((self.row_map[token], self._prepare_row_data(*data)))

        if not rows:
            return

        # Find range
        min_row = min(r[0] for r in rows)
        max_row = max(r[0] for r in rows)

        # Create full matrix
        full_data = [[''] * len(self.live_headers) 
                     for _ in range(max_row - min_row + 1)]

        for row, row_data in rows:
            full_data[row - min_row] = row_data

        # Write everything at once
        self.sheet_live.range(f"A{min_row}:W{max_row}").value = full_data

        self.app.screen_updating = True
        self.app.calculation = 'automatic'
    
    def cleanup_removed(self, active_tokens: Set[str]):
        """Clean up rows for removed tokens"""
        try:
            removed = set(self.row_map.keys()) - active_tokens
            for token in removed:
                if token in self.row_map:
                    row = self.row_map[token]
                    last_col = chr(64 + len(self.live_headers))
                    self.sheet_live.range(f"A{row}:{last_col}{row}").clear_contents()
                    del self.row_map[token]
                    self.logger.info(f"Cleaned up token {token} from row {row}")
        except Exception as e:
            self.logger.error(f"Error cleaning up: {e}")
    
    def close(self):
        """Close Excel"""
        try:
            if self.wb:
                self.wb.save()
                self.logger.info("Workbook saved")
                self.wb.close()
                self.logger.info("Workbook closed")
            if self.app:
                self.app.quit()
                self.logger.info("Excel application closed")
        except Exception as e:
            self.logger.error(f"Error closing Excel: {e}")