# ===============================
# view_logs.py - View previous terminal logs
# ===============================

from pathlib import Path
from datetime import datetime

log_dir = Path("terminal_logs")

if not log_dir.exists():
    print("❌ No logs directory found")
    exit()

log_files = sorted(log_dir.glob("*.txt"), reverse=True)

if not log_files:
    print("❌ No log files found")
    exit()

print("\n📋 Available terminal logs:")
print("-" * 60)

for i, log_file in enumerate(log_files[:10], 1):  # Show last 10 logs
    # Extract timestamp from filename
    size = log_file.stat().st_size / 1024  # Size in KB
    modified = datetime.fromtimestamp(log_file.stat().st_mtime)
    print(f"{i}. {log_file.name}")
    print(f"   Size: {size:.1f} KB, Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}")

print("-" * 60)

# Ask which log to view
choice = input("\nEnter number to view log (or 0 to exit): ")
try:
    idx = int(choice) - 1
    if 0 <= idx < len(log_files):
        print(f"\n📄 Showing content of {log_files[idx].name}:")
        print("-" * 80)
        with open(log_files[idx], 'r', encoding='utf-8') as f:
            print(f.read())
        print("-" * 80)
    elif choice != '0':
        print("❌ Invalid choice")
except:
    print("❌ Invalid input")