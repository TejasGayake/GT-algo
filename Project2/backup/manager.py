# ===============================
# backup/manager.py - Token Backup Manager
# ===============================

import csv
import json
import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
import pandas as pd
import threading
from dataclasses import dataclass, asdict, field

# Absolute imports
from utils.logger import get_logger
from utils.helpers import sanitize_filename
from backup.models import TokenInfo, TokenGroup

class TokenBackupManager:
    """Manages token backups and restoration"""
    
    def __init__(self, backup_dir: str = "token_backups"):
        """
        Initialize backup manager
        
        Args:
            backup_dir: Directory to store backups
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.csv_dir = self.backup_dir / "csv"
        self.json_dir = self.backup_dir / "json"
        self.groups_dir = self.backup_dir / "groups"
        self.history_dir = self.backup_dir / "history"
        
        for dir_path in [self.csv_dir, self.json_dir, self.groups_dir, self.history_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Setup logging
        self.logger = get_logger('TokenBackup')
        
        # Current session tracking
        self.current_tokens: List[TokenInfo] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Lock for thread safety
        self.lock = threading.RLock()
    
    # ===============================
    # CSV BACKUP METHODS
    # ===============================
    
    def save_to_csv(self, tokens: List[TokenInfo], filename: Optional[str] = None) -> str:
        """
        Save tokens to CSV file
        
        Args:
            tokens: List of TokenInfo objects
            filename: Optional custom filename
            
        Returns:
            Path to saved file
        """
        if not filename:
            filename = f"tokens_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = self.csv_dir / filename
        
        # Convert to list of dicts
        data = [t.to_dict() for t in tokens]
        
        # Write to CSV
        if data:
            df = pd.DataFrame(data)
            df.to_csv(filepath, index=False)
        else:
            # Empty file with headers
            pd.DataFrame(columns=[
                'token', 'exchange', 'exchange_type', 'symbol', 'name',
                'expiry', 'strike', 'option_type', 'lot_size', 'tick_size',
                'asset_type', 'added_date', 'notes'
            ]).to_csv(filepath, index=False)
        
        self.logger.info(f"Saved {len(tokens)} tokens to {filepath}")
        
        # Save to history
        self._save_to_history(tokens, "csv", filename)
        
        return str(filepath)
    
    def load_from_csv(self, filepath: str) -> List[TokenInfo]:
        """
        Load tokens from CSV file
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            List of TokenInfo objects
        """
        try:
            df = pd.read_csv(filepath)
            tokens = []
            
            for _, row in df.iterrows():
                token_data = row.to_dict()
                # Handle NaN values
                for key, value in token_data.items():
                    if pd.isna(value):
                        token_data[key] = "" if key in ['symbol', 'name', 'expiry', 'notes'] else 0
                
                tokens.append(TokenInfo.from_dict(token_data))
            
            self.logger.info(f"Loaded {len(tokens)} tokens from {filepath}")
            return tokens
            
        except Exception as e:
            self.logger.error(f"Error loading CSV: {e}")
            return []
    
    # ===============================
    # JSON BACKUP METHODS
    # ===============================
    
    def save_to_json(self, tokens: List[TokenInfo], filename: Optional[str] = None, 
                     pretty: bool = True) -> str:
        """
        Save tokens to JSON file
        
        Args:
            tokens: List of TokenInfo objects
            filename: Optional custom filename
            pretty: Pretty print JSON
            
        Returns:
            Path to saved file
        """
        if not filename:
            filename = f"tokens_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.json_dir / filename
        
        data = [t.to_dict() for t in tokens]
        
        with open(filepath, 'w') as f:
            if pretty:
                json.dump(data, f, indent=2, default=str)
            else:
                json.dump(data, f, default=str)
        
        self.logger.info(f"Saved {len(tokens)} tokens to {filepath}")
        
        # Save to history
        self._save_to_history(tokens, "json", filename)
        
        return str(filepath)
    
    def load_from_json(self, filepath: str) -> List[TokenInfo]:
        """
        Load tokens from JSON file
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            List of TokenInfo objects
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            tokens = [TokenInfo.from_dict(item) for item in data]
            self.logger.info(f"Loaded {len(tokens)} tokens from {filepath}")
            return tokens
            
        except Exception as e:
            self.logger.error(f"Error loading JSON: {e}")
            return []
    
    # ===============================
    # TOKEN GROUP METHODS
    # ===============================
    
    def save_group(self, group: TokenGroup) -> str:
        """
        Save token group
        
        Args:
            group: TokenGroup object
            
        Returns:
            Path to saved file
        """
        # Update timestamps
        if not group.created_date:
            group.created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        group.modified_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Sanitize filename
        filename = sanitize_filename(f"{group.name}.json")
        filepath = self.groups_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(group.to_dict(), f, indent=2, default=str)
        
        self.logger.info(f"Saved group '{group.name}' with {len(group.tokens)} tokens")
        return str(filepath)
    
    def load_group(self, name: str) -> Optional[TokenGroup]:
        """
        Load token group by name
        
        Args:
            name: Group name
            
        Returns:
            TokenGroup object or None
        """
        filename = sanitize_filename(f"{name}.json")
        filepath = self.groups_dir / filename
        
        if not filepath.exists():
            self.logger.warning(f"Group '{name}' not found")
            return None
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            return TokenGroup.from_dict(data)
            
        except Exception as e:
            self.logger.error(f"Error loading group '{name}': {e}")
            return None
    
    def list_groups(self) -> List[Dict]:
        """List all available token groups"""
        groups = []
        
        for filepath in self.groups_dir.glob("*.json"):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                groups.append({
                    "name": data.get("name", filepath.stem),
                    "description": data.get("description", ""),
                    "token_count": len(data.get("tokens", [])),
                    "created": data.get("created_date", ""),
                    "modified": data.get("modified_date", ""),
                    "tags": data.get("tags", []),
                    "file": filepath.name
                })
            except Exception as e:
                self.logger.error(f"Error reading group {filepath}: {e}")
                continue
        
        return groups
    
    def delete_group(self, name: str) -> bool:
        """Delete a token group"""
        filename = sanitize_filename(f"{name}.json")
        filepath = self.groups_dir / filename
        
        if filepath.exists():
            filepath.unlink()
            self.logger.info(f"Deleted group '{name}'")
            return True
        
        return False
    
    # ===============================
    # EXCEL FORMAT METHODS
    # ===============================
    
    def tokens_to_excel_format(self, tokens: List[TokenInfo]) -> List[str]:
        """
        Convert tokens to Excel format (TOKEN-EXCHANGE)
        
        Args:
            tokens: List of TokenInfo objects
            
        Returns:
            List of formatted strings
        """
        return [f"{t.token}-{t.exchange_type}" for t in tokens]
    
    def excel_format_to_tokens(self, excel_tokens: List[str]) -> List[TokenInfo]:
        """
        Convert Excel format to TokenInfo objects
        
        Args:
            excel_tokens: List of strings like "TOKEN-EXCHANGE"
            
        Returns:
            List of TokenInfo objects
        """
        tokens = []
        for token_str in excel_tokens:
            if token_str and str(token_str).strip():
                try:
                    if "-" in str(token_str):
                        token, exch = str(token_str).strip().split("-")
                        tokens.append(TokenInfo(
                            token=token.strip(),
                            exchange="NSE" if int(exch) == 1 else "BSE",
                            exchange_type=int(exch),
                            added_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ))
                    else:
                        # Handle tokens without exchange
                        tokens.append(TokenInfo(
                            token=str(token_str).strip(),
                            exchange="NSE",
                            exchange_type=1,
                            added_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ))
                except Exception as e:
                    self.logger.error(f"Error parsing token {token_str}: {e}")
                    continue
        
        return tokens
    
    # ===============================
    # AUTO-BACKUP METHODS
    # ===============================
    
    def auto_backup(self, tokens: List[TokenInfo], prefix: str = "auto") -> Dict[str, str]:
        """
        Create automatic backup in multiple formats
        
        Args:
            tokens: List of tokens to backup
            prefix: Prefix for backup files
            
        Returns:
            Dictionary with paths to backup files
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{prefix}_{timestamp}"
        
        backups = {}
        
        # Save in multiple formats
        backups['csv'] = self.save_to_csv(tokens, f"{base_name}.csv")
        backups['json'] = self.save_to_json(tokens, f"{base_name}.json")
        
        # Create daily backup if not exists
        daily_name = f"daily_{datetime.now().strftime('%Y%m%d')}"
        daily_csv = self.csv_dir / f"{daily_name}.csv"
        
        if not daily_csv.exists():
            self.save_to_csv(tokens, f"{daily_name}.csv")
            backups['daily'] = str(daily_csv)
        
        # Update current session
        with self.lock:
            self.current_tokens = tokens.copy()
        
        return backups
    
    def _save_to_history(self, tokens: List[TokenInfo], format_type: str, filename: str):
        """Save backup to history"""
        history_file = self.history_dir / "backup_history.json"
        
        history = []
        if history_file.exists():
            with open(history_file, 'r') as f:
                try:
                    history = json.load(f)
                except:
                    history = []
        
        # Add entry
        history.append({
            "timestamp": datetime.now().isoformat(),
            "format": format_type,
            "filename": filename,
            "token_count": len(tokens),
            "session_id": self.session_id,
            "tokens": [t.token for t in tokens]
        })
        
        # Keep last 100 entries
        history = history[-100:]
        
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def get_backup_history(self, limit: int = 50) -> List[Dict]:
        """Get backup history"""
        history_file = self.history_dir / "backup_history.json"
        
        if not history_file.exists():
            return []
        
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
            return history[-limit:]
        except:
            return []
    
    # ===============================
    # RESTORATION METHODS
    # ===============================
    
    def restore_latest(self, format_type: str = "csv") -> Optional[List[TokenInfo]]:
        """
        Restore from latest backup
        
        Args:
            format_type: 'csv' or 'json'
            
        Returns:
            List of tokens or None
        """
        # Get latest backup file
        dir_path = self.csv_dir if format_type == "csv" else self.json_dir
        files = list(dir_path.glob(f"*.{format_type}"))
        
        if not files:
            self.logger.warning(f"No {format_type} backups found")
            return None
        
        # Sort by modification time
        latest = max(files, key=lambda f: f.stat().st_mtime)
        
        if format_type == "csv":
            return self.load_from_csv(str(latest))
        else:
            return self.load_from_json(str(latest))
    
    def restore_by_date(self, date: str, format_type: str = "csv") -> Optional[List[TokenInfo]]:
        """
        Restore backup from specific date
        
        Args:
            date: Date string in YYYYMMDD format
            format_type: 'csv' or 'json'
            
        Returns:
            List of tokens or None
        """
        pattern = f"*{date}*.{format_type}"
        
        if format_type == "csv":
            files = list(self.csv_dir.glob(pattern))
        else:
            files = list(self.json_dir.glob(pattern))
        
        if not files:
            self.logger.warning(f"No backup found for date {date}")
            return None
        
        # Use the most recent match
        latest = max(files, key=lambda f: f.stat().st_mtime)
        
        if format_type == "csv":
            return self.load_from_csv(str(latest))
        else:
            return self.load_from_json(str(latest))
    
    # ===============================
    # UTILITY METHODS
    # ===============================
    
    def get_backup_summary(self) -> Dict:
        """Get summary of all backups"""
        summary = {
            "csv_backups": len(list(self.csv_dir.glob("*.csv"))),
            "json_backups": len(list(self.json_dir.glob("*.json"))),
            "groups": len(list(self.groups_dir.glob("*.json"))),
            "total_tokens_backed_up": 0,
            "latest_backup": None,
            "disk_usage_mb": 0,
            "groups_list": self.list_groups(),
            "history_count": len(self.get_backup_history())
        }
        
        # Calculate total tokens
        for filepath in self.csv_dir.glob("*.csv"):
            try:
                df = pd.read_csv(filepath)
                summary["total_tokens_backed_up"] += len(df)
            except:
                pass
        
        # Calculate disk usage
        total_size = 0
        for dir_path in [self.csv_dir, self.json_dir, self.groups_dir, self.history_dir]:
            for filepath in dir_path.glob("*"):
                total_size += filepath.stat().st_size
        summary["disk_usage_mb"] = round(total_size / (1024 * 1024), 2)
        
        # Find latest backup
        all_backups = list(self.csv_dir.glob("*.csv")) + list(self.json_dir.glob("*.json"))
        if all_backups:
            latest = max(all_backups, key=lambda f: f.stat().st_mtime)
            summary["latest_backup"] = {
                "file": latest.name,
                "time": datetime.fromtimestamp(latest.stat().st_mtime).isoformat()
            }
        
        return summary
    
    def cleanup_old_backups(self, days: int = 30) -> int:
        """
        Delete backups older than specified days
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of files deleted
        """
        cutoff = time.time() - (days * 24 * 3600)
        deleted_count = 0
        
        for dir_path in [self.csv_dir, self.json_dir]:
            for filepath in dir_path.glob("*"):
                if filepath.stat().st_mtime < cutoff:
                    filepath.unlink()
                    deleted_count += 1
                    self.logger.debug(f"Deleted old backup: {filepath.name}")
        
        self.logger.info(f"Cleaned up {deleted_count} old backups")
        return deleted_count