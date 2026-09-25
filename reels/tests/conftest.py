import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["HF_API_KEY_ID"] = "test-key-id"
os.environ["HF_API_KEY_SECRET"] = "test-key-secret"
os.environ["TELEGRAM_API_ID"] = "12345"
os.environ["TELEGRAM_API_HASH"] = "test-api-hash"
os.environ["APPROVAL_CHAT_ID"] = "-1001234567890"
