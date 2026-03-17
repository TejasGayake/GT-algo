# ===============================
# run.py - Entry point with path fix
# ===============================

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now import and run the main app
from sw_excelv12 import LiveFeedApp
from utils.logger import get_logger


if __name__ == "__main__":
    app = LiveFeedApp()
    try:
        app.start()
    except KeyboardInterrupt:
        app.stop()
    except Exception as e:
        self.logger.error(f"Fatal error: {e}")
        app.stop()