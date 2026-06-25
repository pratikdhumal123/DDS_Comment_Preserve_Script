"""
Confluence API Configuration
Edit these values to match your environment
"""

import os

# Your Confluence instance base URL
BASE_URL = "https://scdp.cisco.com/conf"


# Authentication mode:
#   "auto"   -> try Cookie, Bearer token, then Basic auth
#   "cookie" -> use SESSION_COOKIE only
#   "bearer" -> use ACCESS_TOKEN only
#   "basic"  -> use USERNAME/PASSWORD only
# AUTH_METHOD = "basic"
AUTH_METHOD = os.getenv("CONF_AUTH_METHOD", "auto")
# Your access token (keep this secure!)
ACCESS_TOKEN = os.getenv("CONF_ACCESS_TOKEN", "")
# Basic auth credentials (used when AUTH_METHOD is "basic" or fallback in "auto")
USERNAME = os.getenv("CONF_USERNAME", "")
PASSWORD = os.getenv("CONF_PASSWORD", "")

# Optional: Browser session cookie for SSO environments where token/basic are blocked.
# Copy full Cookie header value from an authenticated Confluence browser request.
SESSION_COOKIE = os.getenv("CONF_SESSION_COOKIE", "")

# Your space key
SPACE_KEY = "MS01"

# API endpoint base
API_BASE = f"{BASE_URL}/rest/api"
