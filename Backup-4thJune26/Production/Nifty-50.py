# ---------------------------------------------------------------------
# SECTOR-WISE WEIGHTED BREADTH ENGINE
# ---------------------------------------------------------------------

# 1. Define the Sector Structure (Sorted by Weight: Heaviest to Lightest)
# Note: Weights are approximate based on 2026 data. Update monthly.
SECTOR_MAP = {
    "FINANCIAL_SERVICES": [
        ("HDFC_BANK", 10.56),
        ("ICICI_BANK", 8.32),
        ("STATE_BANK_INDIA", 3.71),
        ("AXIS_BANK", 3.42),
        ("KOTAK_BANK", 2.62),
        ("BAJAJ_FINANCE", 1.80),
    ],
    "OIL_GAS_CONSUMABLE_FUELS": [("RELIANCE", 10.19), ("ONGC", 1.50), ("BPCL", 0.80)],
    "IT": [
        ("INFOSYS", 5.90),
        ("TCS", 4.10),
        ("HCL_TECH", 1.50),
        ("TECH_MAHINDRA", 1.20),
        ("WIPRO", 1.00),
    ],
    "FMCG": [("ITC", 4.50), ("HINDUSTAN_UNILEVER", 2.60), ("NESTLE", 0.90)],
    "AUTOMOBILE": [
        ("MAHINDRA_MAHINDRA", 2.50),
        ("TATA_MOTORS", 2.30),
        ("MARUTI", 1.50),
    ],
    # Add other sectors (Pharma, Metals, Construction) similarly...
}


def analyze_market_by_sector(stock_signals: dict[str, str]):
    """
    Prints a structured report: Sector -> Heavyweights -> Lightweights -> Total
    """
    print(f"{'STOCK':<20} | {'WEIGHT':<8} | {'STATUS':<10}")
    print("-" * 50)

    grand_total_bullish_weight = 0.0

    for sector, stocks in SECTOR_MAP.items():
        print(f"\n📘 SECTOR: {sector}")

        sector_bullish_weight = 0.0
        sector_total_weight = 0.0

        # Sort stocks just in case they aren't already (Heaviest First)
        sorted_stocks = sorted(stocks, key=lambda x: x[1], reverse=True)

        for stock_name, weight in sorted_stocks:
            signal = stock_signals.get(stock_name, "NEUTRAL")
            status_icon = "🟢" if signal == "BULLISH" else "🔴"

            # Print row for this stock
            print(f"  {status_icon} {stock_name:<16} | {weight}%")

            # Accumulate math
            sector_total_weight += weight
            if signal == "BULLISH":
                sector_bullish_weight += weight
                grand_total_bullish_weight += weight

        # --- SECTOR SUMMARY ---
        strength_pct = (sector_bullish_weight / sector_total_weight) * 100
        print(f"  {'='*30}")
        print(
            f"  ∑ SECTOR SCORE: {strength_pct:.1f}% Bullish ({sector_bullish_weight:.2f} / {sector_total_weight:.2f} pts)"
        )

    print("\n" + "#" * 50)
    print(
        f"🚀 GRAND MARKET MOMENTUM: {grand_total_bullish_weight:.2f} Total Index Points"
    )


# --- TEST DRIVE ---
# Scenario: Banks are rallying (Green), but IT and Reliance are dumping (Red)
mock_signals = {
    "HDFC_BANK": "BULLISH",
    "ICICI_BANK": "BULLISH",
    "STATE_BANK_INDIA": "BULLISH",
    "RELIANCE": "BEARISH",
    "ONGC": "BEARISH",
    "INFOSYS": "BEARISH",
    "TCS": "BEARISH",
}

analyze_market_by_sector(mock_signals)
