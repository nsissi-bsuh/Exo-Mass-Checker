"""
Epic Games Developer API Configuration (env-only)
- Reads EPIC_CLIENT_ID, EPIC_CLIENT_SECRET, EPIC_DEPLOYMENT_ID from environment
- No hardcoded placeholders or fallbacks
"""

import os
from typing import Dict, List
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

def _required(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise ValueError(f"Missing required environment variable: {name}")
    return val

# Credentials strictly from environment
EPIC_CLIENT_CREDENTIALS = {
    "client_id": _required("EPIC_CLIENT_ID"),
    "client_secret": _required("EPIC_CLIENT_SECRET"),
    "deployment_id": _required("EPIC_DEPLOYMENT_ID"),
    "user_agent": os.getenv("EPIC_USER_AGENT", "EpicGamesBot/1.0.0 (Official Epic Games Developer API)")
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

# Fortnite endpoints
FORTNITE_ENDPOINTS = {
    "profile": "https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/profile/{}/client/QueryProfile",
    "stats": "https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/stats/accountId/{}/bulk/window/alltime"
}

# 🔐 OAUTH SCOPES
REQUIRED_SCOPES = "basic_profile friends_list presence"


def get_primary_credentials() -> Dict[str, str]:
    """Get primary Epic Games credentials (from environment only)"""
    return EPIC_CLIENT_CREDENTIALS

def get_all_credentials() -> List[Dict[str, str]]:
    """Get only the credentials from .env file (no fallbacks)"""
    return [EPIC_CLIENT_CREDENTIALS]

def is_production_ready() -> bool:
    """True when all required env vars are present (no placeholders)."""
    try:
        return all(bool(EPIC_CLIENT_CREDENTIALS.get(k)) for k in ("client_id", "client_secret", "deployment_id"))
    except Exception:
        return False


def validate_client_credentials(timeout: int = 15) -> dict:
    """Perform a small OAuth request to sanity-check client credentials.
    Returns a dict like {ok: bool, status_code: int, error?: str}."""
    try:
        auth = (EPIC_CLIENT_CREDENTIALS["client_id"], EPIC_CLIENT_CREDENTIALS["client_secret"])
        headers = {"User-Agent": EPIC_CLIENT_CREDENTIALS["user_agent"]}
        data = {"grant_type": "client_credentials", "deployment_id": EPIC_CLIENT_CREDENTIALS["deployment_id"]}
        resp = requests.post(EPIC_ENDPOINTS["oauth_token"], auth=auth, headers=headers, data=data, timeout=timeout)
        if resp.status_code == 200:
            return {"ok": True, "status_code": 200}
        err = None
        try:
            j = resp.json()
            err = j.get("errorCode") or j.get("error") or resp.text[:200]
        except Exception:
            err = resp.text[:200]
        if isinstance(err, str) and "invalid_client" in err.lower():
            return {"ok": False, "status_code": resp.status_code, "error": "invalid_client (check client id/secret)"}
        return {"ok": True, "status_code": resp.status_code, "error": str(err)}
    except requests.RequestException as e:
        return {"ok": False, "status_code": -1, "error": str(e)}
