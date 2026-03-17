# ===============================
# run_with_logging.py - Run app and save terminal output to file
# ===============================

import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Create logs directory if it doesn't exist
log_dir = Path("terminal_logs")
log_dir.mkdir(exist_ok=True)

# Generate filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"terminal_output_{timestamp}.txt"

print(f"📝 Terminal output will be saved to: {log_file}")
print("=" * 60)

# Run your actual script and capture output
try:
    # Run run.py and capture output in real-time while also saving to file
    with open(log_file, 'w', encoding='utf-8') as f:
        process = subprocess.Popen(
            [sys.executable, 'run.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding='utf-8'
        )
        
        # Read output line by line and print to console and file
        for line in process.stdout:
            print(line, end='')  # Print to console
            f.write(line)        # Save to file
            f.flush()            # Ensure it's written immediately
        
        process.wait()
        
    print("=" * 60)
    print(f"✅ Terminal output saved to: {log_file}")
    
except KeyboardInterrupt:
    print("\n\n⚠️ Application stopped by user")
    print(f"✅ Partial output saved to: {log_file}")
    
except Exception as e:
    print(f"❌ Error: {e}")