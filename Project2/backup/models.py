# ===============================
# backup/models.py - Token Data Models
# ===============================

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any

@dataclass
class TokenInfo:
    """Complete token information"""
    token: str
    exchange: str = "NSE"  # NSE, BSE, etc.
    exchange_type: int = 1  # 1 for NSE, 2 for BSE
    symbol: str = ""
    name: str = ""
    expiry: Optional[str] = None
    strike: Optional[float] = None
    option_type: Optional[str] = None  # CE/PE
    lot_size: int = 1
    tick_size: float = 0.05
    asset_type: str = "EQ"  # EQ, FUT, OPT
    added_date: str = ""
    notes: str = ""
    
    def __post_init__(self):
        """Set default values after initialization"""
        if not self.added_date:
            self.added_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.symbol and self.token:
            self.symbol = self.token
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'token': self.token,
            'exchange': self.exchange,
            'exchange_type': self.exchange_type,
            'symbol': self.symbol,
            'name': self.name,
            'expiry': self.expiry,
            'strike': self.strike,
            'option_type': self.option_type,
            'lot_size': self.lot_size,
            'tick_size': self.tick_size,
            'asset_type': self.asset_type,
            'added_date': self.added_date,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TokenInfo':
        """Create from dictionary"""
        return cls(
            token=str(data.get('token', '')),
            exchange=str(data.get('exchange', 'NSE')),
            exchange_type=int(data.get('exchange_type', 1)),
            symbol=str(data.get('symbol', '')),
            name=str(data.get('name', '')),
            expiry=str(data.get('expiry')) if data.get('expiry') else None,
            strike=float(data['strike']) if data.get('strike') else None,
            option_type=str(data.get('option_type')) if data.get('option_type') else None,
            lot_size=int(data.get('lot_size', 1)),
            tick_size=float(data.get('tick_size', 0.05)),
            asset_type=str(data.get('asset_type', 'EQ')),
            added_date=str(data.get('added_date', '')),
            notes=str(data.get('notes', ''))
        )
    
    @classmethod
    def from_excel_format(cls, token_str: str, exchange_type: int = 1) -> 'TokenInfo':
        """Create from Excel format (TOKEN-EXCHANGE)"""
        if "-" in token_str:
            token, exch = token_str.split("-")
            exchange_type = int(exch)
        else:
            token = token_str
            
        return cls(
            token=token.strip(),
            exchange="NSE" if exchange_type == 1 else "BSE",
            exchange_type=exchange_type,
            added_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

@dataclass
class TokenGroup:
    """Group of tokens with metadata"""
    name: str
    description: str = ""
    tokens: List[TokenInfo] = field(default_factory=list)
    created_date: str = ""
    modified_date: str = ""
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Set default values after initialization"""
        if not self.created_date:
            self.created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.modified_date:
            self.modified_date = self.created_date
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "tokens": [t.to_dict() for t in self.tokens],
            "created_date": self.created_date,
            "modified_date": self.modified_date,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TokenGroup':
        """Create from dictionary"""
        group = cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            created_date=data.get("created_date", ""),
            modified_date=data.get("modified_date", ""),
            tags=data.get("tags", [])
        )
        
        # Convert tokens
        token_data = data.get("tokens", [])
        group.tokens = [TokenInfo.from_dict(t) for t in token_data]
        
        return group
    
    def add_token(self, token: TokenInfo):
        """Add token to group"""
        self.tokens.append(token)
        self.modified_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def remove_token(self, token: str):
        """Remove token from group"""
        self.tokens = [t for t in self.tokens if t.token != token]
        self.modified_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_token(self, token: str) -> Optional[TokenInfo]:
        """Get token by ID"""
        for t in self.tokens:
            if t.token == token:
                return t
        return None
    
    @property
    def token_count(self) -> int:
        """Get number of tokens"""
        return len(self.tokens)
    
    @property
    def token_list(self) -> List[str]:
        """Get list of token IDs"""
        return [t.token for t in self.tokens]