"""
Authentication module for Snowflake Cortex A2A Proxy.
Propagates user OAuth (Entra ID) credentials to Snowflake.
"""
import json
import jwt
from dotenv import load_dotenv

load_dotenv()


def decode_token_claims(token: str) -> dict:
    """Decode a JWT token WITHOUT verification to inspect its claims."""
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except Exception as e:
        print(f"DEBUG: Failed to decode token: {e}")
        return {}


def get_snowflake_headers(token: str) -> dict:
    """Returns Snowflake API headers using a propagated OAuth token."""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Snowflake-Authorization-Token-Type": "OAUTH"
    }
