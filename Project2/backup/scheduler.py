# ===============================
# backup/scheduler.py - Scheduled Backup
# ===============================

import threading
import time
from datetime import datetime, time as dtime
from typing import List, Callable, Optional

# Absolute imports
from utils.logger import get_logger
from backup.manager import TokenBackupManager
from backup.models import TokenInfo

class ScheduledBackup:
    """Handles automated scheduled backups"""
    
    def __init__(self, backup_manager: TokenBackupManager):
        """
        Initialize scheduled backup
        
        Args:
            backup_manager: TokenBackupManager instance
        """
        self.manager = backup_manager
        self.logger = get_logger('ScheduledBackup')
        
        # Threading
        self.schedule_thread = None
        self.running = False
        self.lock = threading.RLock()
        
        # Schedule configuration
        self.market_hours = [
            (dtime(9, 15), dtime(12, 0)),   # Morning session
            (dtime(12, 0), dtime(15, 30))   # Afternoon session
        ]
        
        self.backup_times = [
            dtime(9, 30),   # 9:30 AM - Market open
            dtime(12, 0),   # 12:00 PM - Mid-day
            dtime(15, 15),  # 3:15 PM - Before close
            dtime(15, 45)   # 3:45 PM - Market close + 15 min
        ]
        
        self.last_backup = None
        self.backup_count = 0
    
    def start(self):
        """Start scheduled backup thread"""
        with self.lock:
            if self.running:
                return
            
            self.running = True
            self.schedule_thread = threading.Thread(target=self._run_schedule, daemon=True)
            self.schedule_thread.start()
            self.logger.info("Scheduled backup started")
    
    def stop(self):
        """Stop scheduled backup"""
        with self.lock:
            self.running = False
            if self.schedule_thread:
                self.schedule_thread.join(timeout=5)
            self.logger.info("Scheduled backup stopped")
    
    def _run_schedule(self):
        """Main schedule loop"""
        self.logger.info("Backup scheduler running")
        
        while self.running:
            try:
                now = datetime.now()
                current_time = now.time()
                
                # Check if it's time to backup
                for backup_time in self.backup_times:
                    if self._time_match(current_time, backup_time):
                        self._execute_backup(f"scheduled_{backup_time.strftime('%H%M')}")
                        break
                
                # Check for market close backup
                if self._is_market_closed(current_time) and self._should_create_eod_backup():
                    self._execute_backup("market_close")
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Schedule error: {e}")
                time.sleep(60)
    
    def _time_match(self, current: dtime, target: dtime, tolerance: int = 60) -> bool:
        """
        Check if current time matches target time within tolerance
        
        Args:
            current: Current time
            target: Target time
            tolerance: Tolerance in seconds
            
        Returns:
            True if times match
        """
        if not self.manager.current_tokens:
            return False
            
        # Convert to seconds since midnight
        current_seconds = current.hour * 3600 + current.minute * 60 + current.second
        target_seconds = target.hour * 3600 + target.minute * 60
        
        return abs(current_seconds - target_seconds) < tolerance
    
    def _is_market_hours(self, current_time: dtime) -> bool:
        """Check if within market hours"""
        for start, end in self.market_hours:
            if start <= current_time <= end:
                return True
        return False
    
    def _is_market_closed(self, current_time: dtime) -> bool:
        """Check if market is closed"""
        return not self._is_market_hours(current_time)
    
    def _should_create_eod_backup(self) -> bool:
        """Check if End of Day backup should be created"""
        if not self.last_backup:
            return True
        
        # Check if last backup was today
        last_date = self.last_backup.date()
        today = datetime.now().date()
        
        return last_date < today
    
    def _execute_backup(self, prefix: str):
        """Execute backup"""
        try:
            if not self.manager.current_tokens:
                self.logger.debug("No tokens to backup")
                return
            
            self.logger.info(f"Executing scheduled backup: {prefix}")
            
            # Create backup
            result = self.manager.auto_backup(
                self.manager.current_tokens,
                prefix=prefix
            )
            
            self.last_backup = datetime.now()
            self.backup_count += 1
            
            self.logger.info(f"✅ Scheduled backup complete: {result}")
            
        except Exception as e:
            self.logger.error(f"❌ Scheduled backup failed: {e}")
    
    def set_backup_times(self, times: List[dtime]):
        """Set custom backup times"""
        with self.lock:
            self.backup_times = times
            self.logger.info(f"Backup times updated: {[t.strftime('%H:%M') for t in times]}")
    
    def add_backup_time(self, backup_time: dtime):
        """Add a backup time"""
        with self.lock:
            if backup_time not in self.backup_times:
                self.backup_times.append(backup_time)
                self.backup_times.sort()
                self.logger.info(f"Added backup time: {backup_time.strftime('%H:%M')}")
    
    def remove_backup_time(self, backup_time: dtime):
        """Remove a backup time"""
        with self.lock:
            if backup_time in self.backup_times:
                self.backup_times.remove(backup_time)
                self.logger.info(f"Removed backup time: {backup_time.strftime('%H:%M')}")
    
    def get_status(self) -> dict:
        """Get scheduler status"""
        with self.lock:
            return {
                'running': self.running,
                'backup_times': [t.strftime('%H:%M') for t in self.backup_times],
                'last_backup': self.last_backup.isoformat() if self.last_backup else None,
                'backup_count': self.backup_count,
                'current_tokens': len(self.manager.current_tokens) if self.manager.current_tokens else 0
            }