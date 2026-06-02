"""
broker_client.py — Shared broker client factory.

Single source of truth for creating a Dhan Tradehull client.
All modules that need a live broker connection must import from here
instead of creating their own get_live_client() functions.
"""
import os
import SafetyLogger


def get_live_client():
    """Creates and returns a Tradehull broker client using env credentials.

    Returns None if credentials are missing or connection fails.
    Never raises — always fails safely.
    """
    from dotenv import load_dotenv
    # Prefer project-standard `cred.env` over older files.
    for cred_file in ["cred.env", "credentials.env", "credentials.crd"]:
        if os.path.exists(cred_file):
            load_dotenv(cred_file, override=True)
            break
            
    client_code: str = os.getenv("DHAN_CLIENT_CODE", "")
    token_id: str = os.getenv("DHAN_TOKEN_ID", "")
    if not client_code or not token_id:
        return None
    try:
        from Dhan_Tradehull import Tradehull
        tsl = Tradehull(client_code, token_id)

        # Validate token early: Tradehull() can "init" even when token is expired.
        resp = tsl.Dhan.get_fund_limits()
        if not isinstance(resp, dict) or resp.get("status") != "success":
            SafetyLogger.log_warning(
                "broker_client",
                f"Dhan auth check failed (get_fund_limits): {resp}",
            )
            return None

        return tsl
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "broker_client", "get_live_client", e,
            {"client_code_set": bool(client_code)}
        )
        return None
