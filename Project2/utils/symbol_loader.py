# ===============================
# utils/symbol_loader.py - For CSV File
# ===============================

import pandas as pd
from pathlib import Path
from typing import Dict, Optional

from utils.logger import get_logger

class SymbolLoader:
    """Load symbol mappings from CSV file"""
    
    def __init__(self, csv_path: str = "symbol_mapping.csv"):
        self.csv_path = Path(csv_path)
        self.logger = get_logger('SymbolLoader')
        self.token_to_symbol: Dict[str, str] = {}
        self.loaded = False
    
    def load(self) -> bool:
        """Load symbols from CSV file"""
        try:
            if not self.csv_path.exists():
                self.logger.error(f"Symbol file not found: {self.csv_path}")
                return False
            
            # Read CSV file
            df = pd.read_csv(self.csv_path)
            
            # Check required columns
            if 'TOKEN' not in df.columns or 'SYMBOL' not in df.columns:
                self.logger.error("CSV must have 'TOKEN' and 'SYMBOL' columns")
                return False
            
            # Clean the data
            df['TOKEN'] = df['TOKEN'].astype(str).str.strip()
            df['SYMBOL'] = df['SYMBOL'].astype(str).str.strip()
            
            # Create lookup dictionary
            self.token_to_symbol = dict(zip(df['TOKEN'], df['SYMBOL']))
            
            self.logger.info(f"✅ Loaded {len(self.token_to_symbol)} symbol mappings from CSV")
            self.logger.debug(f"First 5 mappings: {list(self.token_to_symbol.items())[:5]}")
            
            self.loaded = True
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading symbols: {e}")
            return False
    # ========================================
    ''' def get_symbol(self, token: str) -> str:
        """Get symbol for token"""
        clean_token = str(token).split('.')[0]
        return self.token_to_symbol.get(clean_token, f"TKN-{clean_token}") '''
     
    def get_symbol(self, token: str) -> str:
        """Get symbol for token"""
        clean_token = str(token).split('.')[0]
        symbol = self.token_to_symbol.get(clean_token)

        # Debug print
        if symbol:
            self.logger.debug(f"CSV lookup: {token} → {symbol}")
        else:
            self.logger.info(f"🔍 CSV lookup: {clean_token} → NOT FOUND")

        return symbol if symbol else f"TKN-{clean_token}" 
    # ========================================
    
    def get_all_tokens(self) -> list:
        """Get list of all tokens"""
        return list(self.token_to_symbol.keys())
    
    def add_token(self, token: str, symbol: str):
        """Add a new token to the mapping"""
        clean_token = str(token).split('.')[0]
        self.token_to_symbol[clean_token] = symbol
        self.logger.info(f"✅ Added token {clean_token} -> {symbol}")
    
    def save(self, csv_path: Optional[str] = None):
        """Save mappings back to CSV"""
        save_path = csv_path or self.csv_path
        try:
            import pandas as pd
            data = [{"TOKEN": t, "SYMBOL": s} for t, s in self.token_to_symbol.items()]
            df = pd.DataFrame(data)
            df.to_csv(save_path, index=False)
            self.logger.info(f"✅ Saved {len(data)} mappings to {save_path}")
        except Exception as e:
            self.logger.error(f"Error saving CSV: {e}")
