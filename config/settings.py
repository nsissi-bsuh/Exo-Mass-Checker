"""
Bot Configuration Settings
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Bot credentials
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0') or '0')

# File paths
TEMP_DIR = 'temp'
DATA_DIR = 'data'

# Bot settings
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
SUPPORTED_FILE_TYPES = ['.txt']
MAX_CONCURRENT_CHECKS = 10
REQUEST_TIMEOUT = 30