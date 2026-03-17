# ===============================
# backup/integration.py - Excel Integration
# ===============================

import threading
import time
from datetime import datetime
from typing import Optional, List, Dict

# Absolute imports
from utils.logger import get_logger
from backup.manager import TokenBackupManager
from backup.models import TokenGroup, TokenInfo
from backup.scheduler import ScheduledBackup

class TokenBackupIntegration:
    """Integration class for Excel and backup system"""
    
    def __init__(self, excel_manager, backup_manager: TokenBackupManager = None):
        """
        Initialize with Excel manager
        
        Args:
            excel_manager: ExcelManager instance from main app
            backup_manager: Optional backup manager instance
        """
        self.excel_mgr = excel_manager
        self.backup_mgr = backup_manager or TokenBackupManager()
        self.logger = get_logger('BackupIntegration')
        
        # Scheduled backup
        self.scheduled_backup = ScheduledBackup(self.backup_mgr)
        
        # Auto-save settings
        self.auto_save_enabled = True
        self.last_auto_save = None
        
    def backup_current_tokens(self, group_name: str = "live_session") -> Dict:
        """
        Backup currently active tokens from Excel
        
        Args:
            group_name: Name for the backup group
            
        Returns:
            Backup information dictionary
        """
        try:
            # Read current tokens from Excel
            instruments = self.excel_mgr.read_instruments()
            
            if not instruments:
                self.logger.info("No tokens to backup")
                return {"status": "no_tokens", "count": 0}
            
            # Convert to TokenInfo objects
            excel_tokens = [f"{t}-{e}" for t, e in instruments]
            tokens = self.backup_mgr.excel_format_to_tokens(excel_tokens)
            
            # Create group
            group = TokenGroup(
                name=group_name,
                description=f"Live session backup {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                tokens=tokens,
                tags=["live", "active"]
            )
            
            # Save group
            group_path = self.backup_mgr.save_group(group)
            
            # Auto backup
            backups = self.backup_mgr.auto_backup(tokens, prefix=group_name)
            
            self.logger.info(f"✅ Backed up {len(tokens)} tokens to {group_name}")
            
            return {
                "status": "success",
                "group": group_path,
                "backups": backups,
                "token_count": len(tokens),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Backup failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def restore_to_excel(self, source: str, source_type: str = "group") -> int:
        """
        Restore tokens to Excel
        
        Args:
            source: Group name or file path
            source_type: 'group', 'csv', or 'json'
            
        Returns:
            Number of tokens restored
        """
        try:
            tokens = []
            
            # Load tokens from source
            if source_type == "group":
                group = self.backup_mgr.load_group(source)
                if group:
                    tokens = group.tokens
                    self.logger.info(f"Loaded group '{source}' with {len(tokens)} tokens")
            elif source_type == "csv":
                tokens = self.backup_mgr.load_from_csv(source)
                self.logger.info(f"Loaded {len(tokens)} tokens from CSV")
            elif source_type == "json":
                tokens = self.backup_mgr.load_from_json(source)
                self.logger.info(f"Loaded {len(tokens)} tokens from JSON")
            
            if not tokens:
                self.logger.warning(f"No tokens found in {source}")
                return 0
            
            # Convert to Excel format
            excel_tokens = self.backup_mgr.tokens_to_excel_format(tokens)
            
            # Write to Excel Instruments sheet
            self.excel_mgr.write_tokens_to_excel(excel_tokens)
            
            self.logger.info(f"✅ Restored {len(tokens)} tokens to Excel")
            return len(tokens)
            
        except Exception as e:
            self.logger.error(f"❌ Restore failed: {e}")
            return 0
    
    def start_auto_backup(self):
        """Start automatic backup during market hours"""
        if self.auto_save_enabled:
            self.scheduled_backup.start()
            self.logger.info("Auto-backup started")
    
    def stop_auto_backup(self):
        """Stop automatic backup"""
        self.scheduled_backup.stop()
        self.logger.info("Auto-backup stopped")
    
    def auto_save_current(self):
        """Auto-save current tokens (called periodically)"""
        if not self.auto_save_enabled:
            return
        
        # Don't save too frequently
        if self.last_auto_save and (datetime.now() - self.last_auto_save).seconds < 300:
            return
        
        try:
            instruments = self.excel_mgr.read_instruments()
            if instruments:
                excel_tokens = [f"{t}-{e}" for t, e in instruments]
                tokens = self.backup_mgr.excel_format_to_tokens(excel_tokens)
                
                # Update current tokens in backup manager
                self.backup_mgr.current_tokens = tokens
                self.last_auto_save = datetime.now()
                
                self.logger.debug(f"Auto-save updated {len(tokens)} tokens")
                
        except Exception as e:
            self.logger.error(f"Auto-save error: {e}")
    
    def list_saved_groups(self) -> List[Dict]:
        """List all saved token groups"""
        return self.backup_mgr.list_groups()
    
    def get_backup_history(self, limit: int = 20) -> List[Dict]:
        """Get backup history"""
        return self.backup_mgr.get_backup_history(limit)
    
    def get_backup_summary(self) -> Dict:
        """Get backup system summary"""
        summary = self.backup_mgr.get_backup_summary()
        summary['auto_backup'] = {
            'enabled': self.auto_save_enabled,
            'running': self.scheduled_backup.running,
            'last_auto_save': self.last_auto_save.isoformat() if self.last_auto_save else None
        }
        return summary
    
    def create_group_from_excel(self, group_name: str, description: str = "") -> bool:
        """Create a named group from current Excel tokens"""
        try:
            instruments = self.excel_mgr.read_instruments()
            if not instruments:
                return False
            
            excel_tokens = [f"{t}-{e}" for t, e in instruments]
            tokens = self.backup_mgr.excel_format_to_tokens(excel_tokens)
            
            group = TokenGroup(
                name=group_name,
                description=description,
                tokens=tokens,
                tags=["user_created"]
            )
            
            self.backup_mgr.save_group(group)
            self.logger.info(f"Created group '{group_name}' with {len(tokens)} tokens")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating group: {e}")
            return False
    
    def delete_group(self, group_name: str) -> bool:
        """Delete a saved group"""
        return self.backup_mgr.delete_group(group_name)