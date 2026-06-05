import os
import sys
from dotenv import load_dotenv

# Ensure credentials are loaded
for cred_file in ["credentials.env", "cred.env", "credentials.crd"]:
    if os.path.exists(cred_file):
        load_dotenv(cred_file, override=True)
        break

try:
    from broker_client import get_live_client
    tsl = get_live_client()
    if not tsl:
        print("Failed to init Tradehull")
        sys.exit(1)
        
    print("Testing Dhan API connection...")
    bal = tsl.get_balance()
    print(f"Balance: {bal}")
except Exception as e:
    print(f"Error: {e}")
