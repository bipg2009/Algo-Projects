import os
import sys
from dotenv import load_dotenv

# Ensure project root is importable when running from /scratch
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure credentials are loaded
loaded_cred = None
for cred_file in ["cred.env", "credentials.env", "credentials.crd"]:
    cand = os.path.join(PROJECT_ROOT, cred_file)
    if os.path.exists(cand):
        load_dotenv(cand, override=True)
        loaded_cred = cred_file
        break

try:
    from broker_client import get_live_client
    tsl = get_live_client()
    if not tsl:
        cc_set = bool(os.getenv("DHAN_CLIENT_CODE"))
        tok_set = bool(os.getenv("DHAN_TOKEN_ID"))
        print("Failed to init Tradehull")
        print(f"Cred file loaded: {loaded_cred}")
        print(f"DHAN_CLIENT_CODE set: {cc_set}")
        print(f"DHAN_TOKEN_ID set: {tok_set}")
        sys.exit(1)
        
    print("Testing Dhan API connection...")
    resp = tsl.Dhan.get_fund_limits()
    print(f"Auth check (get_fund_limits) status: {resp.get('status') if isinstance(resp, dict) else type(resp)}")
    if isinstance(resp, dict) and resp.get("status") != "success":
        print(f"Remarks: {resp.get('remarks')}")
    else:
        print("Dhan auth OK.")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
