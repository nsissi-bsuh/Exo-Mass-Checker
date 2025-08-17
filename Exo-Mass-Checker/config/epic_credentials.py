"""
Epic Games Developer API Configuration

🚨 SECURITY WARNING: This file contains sensitive API credentials
🔒 NEVER commit this file to version control with real credentials
📋 REQUIRED: Register your application at https://dev.epicgames.com/portal

PROPER SETUP INSTRUCTIONS:
1. Go to https://dev.epicgames.com/portal
2. Create a new application
3. Get your Client ID and Client Secret
4. Replace the placeholder values below
5. Add this file to .gitignore
"""

import os
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 🔧 PRODUCTION CREDENTIALS (Official Epic Games Developer Portal)
EPIC_CLIENT_CREDENTIALS = {
    "client_id": os.getenv("EPIC_CLIENT_ID", "YOUR_EPIC_CLIENT_ID_HERE"),
    "client_secret": os.getenv("EPIC_CLIENT_SECRET", "YOUR_EPIC_CLIENT_SECRET_HERE"),
    "deployment_id": os.getenv("EPIC_DEPLOYMENT_ID", "BDG"),
    "user_agent": "EpicGamesBot/1.0.0 (Official Epic Games Developer API)"
}

# 🚫 NO FALLBACK CREDENTIALS - Only use Epic Developer Portal credentials

# 🌐 EPIC GAMES API ENDPOINTS
EPIC_ENDPOINTS = {
    "oauth_token": "https://api.epicgames.dev/epic/oauth/v2/token",
    "token_info": "https://api.epicgames.dev/epic/oauth/v2/tokenInfo",
    "token_revoke": "https://api.epicgames.dev/epic/oauth/v2/revoke",
    "accounts": "https://api.epicgames.dev/epic/id/v2/accounts",
    "jwks": "https://api.epicgames.dev/epic/oauth/v2/.well-known/jwks.json"
}

# 🎮 FORTNITE SPECIFIC ENDPOINTS (Legacy - may change)
FORTNITE_ENDPOINTS = {
    "profile": "https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/profile/{}/client/QueryProfile",
    "stats": "https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/stats/accountId/{}/bulk/window/alltime"
}

# 🔐 OAUTH SCOPES
REQUIRED_SCOPES = "basic_profile friends_list presence"

# ⚙️ API SETTINGS
API_SETTINGS = {
    "request_timeout": 30,
    "max_retries": 3,
    "rate_limit_delay": 1.0,
    "user_agent_fallback": "EpicGamesLauncher/10.15.3-14907503+++Portal+Release-Live"
}

def get_primary_credentials() -> Dict[str, str]:
    """Get primary Epic Games credentials (from environment only)"""
    return EPIC_CLIENT_CREDENTIALS

def get_all_credentials() -> List[Dict[str, str]]:
    """Get only the credentials from .env file (no fallbacks)"""
    return [EPIC_CLIENT_CREDENTIALS]

def is_production_ready() -> bool:
    """Check if production Epic Games credentials are configured"""
    return (EPIC_CLIENT_CREDENTIALS["client_id"] != "YOUR_EPIC_CLIENT_ID_HERE" and
            EPIC_CLIENT_CREDENTIALS["client_secret"] != "YOUR_EPIC_CLIENT_SECRET_HERE")