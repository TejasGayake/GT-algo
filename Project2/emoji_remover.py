# ===============================
# force_fix_unicode.py - Force remove all Unicode escapes
# ===============================

import os
import re

# Directory to scan
PROJECT_DIR = r"G:\projects\final_trading\Project2"

# Patterns to find and remove
patterns = [
    (r'\', ''),           # Remove 
    (r'\', ''),       # Remove 
    (r'\', ''),       # Remove 
    (r'\\u26a0\\ufe0f', ''),    # Remove ⚠️
    (r'\', ''),       # Remove 
    (r'\', ''),       # Remove 
    (r'\', ''),       # Remove 
    (r'\', ''),       # Remove 
]

def fix_file(filepath):
    """Fix a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        changes = 0
        
        # Remove all Unicode escapes
        for pattern, replacement in patterns:
            content, count = re.subn(pattern, replacement, content)
            changes += count
        
        # Also remove any standalone Unicode characters (just in case)
        content = re.sub(r'[\U0001F300-\U0001F9FF]', '', content)
        content = re.sub(r'[\u2700-\u27BF]', '', content)
        
        if changes > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f" Fixed: {os.path.basename(filepath)} (removed {changes} Unicode escapes)")
            return True
        else:
            return False
    except Exception as e:
        print(f" Error fixing {filepath}: {e}")
        return False

def main():
    print(" Force Remove Unicode Escapes")
    print("=" * 60)
    
    fixed_count = 0
    scanned_count = 0
    
    for root, dirs, files in os.walk(PROJECT_DIR):
        # Skip excluded directories
        if 'venv' in dirs:
            dirs.remove('venv')
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')
        if '.git' in dirs:
            dirs.remove('.git')
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                scanned_count += 1
                if fix_file(filepath):
                    fixed_count += 1
    
    print("=" * 60)
    print(f" Summary: Scanned {scanned_count} files, fixed {fixed_count} files")
    print(" Done! Now run your app.")

if __name__ == "__main__":
    main()