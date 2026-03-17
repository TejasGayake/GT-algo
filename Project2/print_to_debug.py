# ===============================
# convert_prints_to_logging.py
# ===============================
# Run this script to automatically convert all print() statements
# to logger.debug() in your Python files
# 
# Usage: python convert_prints_to_logging.py
# ===============================

import os
import re
import sys
from pathlib import Path

# Configuration
PROJECT_DIR = r"G:\projects\final_trading\Project2"  # Change this to your project path
FILE_EXTENSIONS = ['.py']
EXCLUDE_DIRS = ['venv', 'env', '__pycache__', '.git', 'logs', 'token_backups']
EXCLUDE_FILES = ['convert_prints_to_logging.py']  # Don't convert this script itself

# Patterns to match
PRINT_PATTERNS = [
    # Match self.logger.debug("something") or self.logger.debug(f"something")
    r'print\s*\(\s*(f?["\'].*?["\'])\s*\)',
    
    # Match self.logger.debug(variable)
    r'print\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)',
    
    # Match self.logger.error("something", variable)
    r'print\s*\(\s*(f?["\'].*?["\']\s*,\s*[^)]+)\s*\)',
    
    # Match our specific debug prints with emojis
    r'print\s*\(\s*f?["\']🔍.*?["\']\s*\)',
    r'print\s*\(\s*f?["\']🎯.*?["\']\s*\)',
    r'print\s*\(\s*f?["\']📊.*?["\']\s*\)',
    r'print\s*\(\s*f?["\']📈.*?["\']\s*\)',
]

# Replacement templates
def get_replacement(match):
    """Determine the appropriate logger method based on content"""
    text = match.group(0)
    
    # Check if it's an error message
    if 'error' in text.lower() or '❌' in text or 'failed' in text.lower():
        return f"self.logger.error({match.group(1)})" if len(match.groups()) > 0 else "self.logger.error('Error')"
    
    # Check if it's a warning
    elif 'warning' in text.lower() or '⚠️' in text:
        return f"self.logger.warning({match.group(1)})" if len(match.groups()) > 0 else "self.logger.warning('Warning')"
    
    # Check if it's info (like status updates)
    elif any(x in text.lower() for x in ['✅', '🚀', 'found', 'loaded', 'starting', 'initializing']):
        return f"self.logger.info({match.group(1)})" if len(match.groups()) > 0 else "self.logger.info('Info')"
    
    # Default to debug for most prints
    else:
        # For prints with emojis, convert to debug
        if any(emoji in text for emoji in ['🔍', '🎯', '📊', '📈']):
            return f"self.logger.debug({match.group(1)})" if len(match.groups()) > 0 else "self.logger.debug('Debug')"
        
        # Regular prints become debug
        return f"self.logger.debug({match.group(1)})" if len(match.groups()) > 0 else "self.logger.debug('Debug')"

def process_file(filepath):
    """Process a single Python file, converting prints to logging"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = 0
        
        # First, check if file already has logger
        has_logger = 'self.logger' in content or 'logger =' in content or 'get_logger' in content
        
        # Convert each print statement
        for pattern in PRINT_PATTERNS:
            def replacement(match):
                nonlocal changes_made
                changes_made += 1
                return get_replacement(match)
            
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # Also handle standalone prints without parentheses? (rare)
        content = re.sub(r'^print\s+(.+)$', r'self.logger.debug(\1)', content, flags=re.MULTILINE)
        
        # If changes were made and file doesn't have logger, add import
        if changes_made > 0 and not has_logger:
            # Add logger import at top if needed
            if 'from utils.logger import get_logger' not in content:
                # Find a good place to add import (after other imports)
                lines = content.split('\n')
                import_index = 0
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        import_index = i + 1
                
                # Insert logger import
                if import_index < len(lines):
                    lines.insert(import_index, 'from utils.logger import get_logger')
                    lines.insert(import_index + 1, '')
                else:
                    lines.append('from utils.logger import get_logger')
                    lines.append('')
                
                content = '\n'.join(lines)
        
        # Write back if changes were made
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.info(f"✅ Converted {changes_made} prints in {filepath}")
            return True
        else:
            self.logger.debug(f"⏭️  No changes needed in {filepath}")
            return False
            
    except Exception as e:
        self.logger.error(f"❌ Error processing {filepath}: {e}")
        return False

def main():
    """Main function to process all Python files"""
    project_path = Path(PROJECT_DIR)
    
    if not project_path.exists():
        self.logger.error(f"❌ Project directory not found: {PROJECT_DIR}")
        self.logger.debug("Please update PROJECT_DIR in the script.")
        return
    
    self.logger.debug(f"🔍 Scanning directory: {project_path}")
    self.logger.debug("=" * 60)
    
    total_files = 0
    converted_files = 0
    total_prints = 0
    
    # Walk through all files
    for root, dirs, files in os.walk(project_path):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            if any(file.endswith(ext) for ext in FILE_EXTENSIONS):
                if file in EXCLUDE_FILES:
                    continue
                    
                filepath = Path(root) / file
                total_files += 1
                
                # Count prints before conversion (rough estimate)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print_count = len(re.findall(r'print\s*\(', content))
                    if print_count > 0:
                        total_prints += print_count
                
                if process_file(filepath):
                    converted_files += 1
    
    self.logger.debug("=" * 60)
    self.logger.debug('Debug')
    self.logger.debug(f"   Total Python files scanned: {total_files}")
    self.logger.debug(f"   Files with conversions: {converted_files}")
    self.logger.debug(f"   Total print statements converted: {total_prints}")
    self.logger.info("=" * 60)
    print("\n✅ Done! Your terminal will now be much cleaner.")
    self.logger.debug("   All debug messages will go to logs/live_feed.log")

if __name__ == "__main__":
    main()