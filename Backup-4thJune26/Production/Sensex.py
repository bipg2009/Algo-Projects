# ---------------------------------------------------------------------
# SENSEX SECTOR-WISE WEIGHTED BREADTH ENGINE
# ---------------------------------------------------------------------

# Official BSE Sensex 30 Mapping (Sorted by Weight: Heaviest to Lightest)
SENSEX_30_MAP = {
    "FINANCIAL_SERVICES": [
        ("HDFC_BANK", 14.54),
        ("ICICI_BANK", 10.33),
        ("STATE_BANK_INDIA", 5.89),
        ("AXIS_BANK", 3.80),
        ("BAJAJ_FINANCE", 3.65),
        ("KOTAK_MAHINDRA_BANK", 2.90),
        ("BAJAJ_FINSERV", 1.20),
    ],
    "OIL_GAS_&_FUELS": [("RELIANCE_IND", 9.74)],
    "INFORMATION_TECHNOLOGY": [
        ("INFOSYS", 5.61),
        ("TCS", 4.15),
        ("HCL_TECHNOLOGIES", 1.65),
        ("TECH_MAHINDRA", 1.30),
        ("WIPRO", 0.90),
    ],
    "TELECOMMUNICATION": [("BHARTI_AIRTEL", 7.37)],
    "CONSTRUCTION_&_INFRA": [("LARSEN_&_TOUBRO", 3.67)],
    "FMCG": [("ITC", 4.20), ("HINDUSTAN_UNILEVER", 2.65)],
    "AUTOMOBILE_&_COMPONENTS": [
        ("MAHINDRA_&_MAHINDRA", 2.70),
        ("TATA_MOTORS", 2.10),
        ("MARUTI_SUZUKI", 1.45),
    ],
    "METALS_&_MINING": [("TATA_STEEL", 2.10), ("JSW_STEEL", 1.10)],
    "PHARMACEUTICALS_&_HEALTH": [
        ("SUN_PHARMA", 1.60),
        ("NTPC", 1.45),
        ("POWER_GRID", 1.35),
    ],
    "CONSUMER_DURABLES_&_CEMENT": [
        ("TITAN_COMPANY", 1.40),
        ("ULTRATECH_CEMENT", 1.18),
        ("ASIAN_PAINTS", 1.11),
    ],
}


def analyze_sensex_by_sector(stock_signals: dict[str, str]):
    """
    Prints a structured Sensex report: Sector -> Heavyweights -> Lightweights -> Total Sum Last
    """
    print(f"{'STOCK':<20} | {'SENSEX WEIGHT':<13} | {'STATUS':<10}")
    print("-" * 55)

    grand_total_bullish_weight = 0.0
    grand_total_index_weight = 0.0

    for sector, stocks in SENSEX_30_MAP.items():
        print(f"\n🏛️ SENSEX SECTOR: {sector}")

        sector_bullish_weight = 0.0
        sector_total_weight = 0.0

        # Ensures heavyweights stay strictly at the top inside their sectors
        sorted_stocks = sorted(stocks, key=lambda x: x[1], reverse=True)

        for stock_name, weight in sorted_stocks:
            signal = stock_signals.get(stock_name, "NEUTRAL")
            status_icon = "🟢" if signal == "BULLISH" else "🔴"

            # Print individual stock row
            print(f"  {status_icon} {stock_name:<16} | {weight:>5}%")

            # Mathematical accumulation
            sector_total_weight += weight
            grand_total_index_weight += weight
            if signal == "BULLISH":
                sector_bullish_weight += weight
                grand_total_bullish_weight += weight

        # --- SECTOR CALCULATIONS ---
        strength_pct = (
            (sector_bullish_weight / sector_total_weight) * 100
            if sector_total_weight > 0
            else 0
        )
        print(f"  {'═'*35}")
        print(
            f"  ∑ {sector} SUMMARY: {strength_pct:.1f}% Bullish ({sector_bullish_weight:.2f}% / {sector_total_weight:.2f}%)"
        )

    # --- FINAL SUM AT THE VERY END ---
    print("\n" + "█" * 55)
    print(f"🏁 GRAND TOTALS")
    print(f"📊 Market Coverage Tracked: {grand_total_index_weight:.2f}% of Sensex")
    print(f"🚀 TOTAL BULLISH MOMENTUM MASS: {grand_total_bullish_weight:.2f}%")

    # Calculate broad market health percentage
    market_health = (grand_total_bullish_weight / grand_total_index_weight) * 100
    print(f"📈 TRUE SENSEX HEALTH SCORE: {market_health:.2f}% Bullish")
    print("█" * 55)


# --- SIMULATION ---
# Scenario: Banks and IT are crashing, but Reliance and Telecom push a fake rally
mock_sensex_signals = {
    "HDFC_BANK": "BEARISH",
    "ICICI_BANK": "BEARISH",
    "STATE_BANK_INDIA": "BEARISH",
    "RELIANCE_IND": "BULLISH",
    "BHARTI_AIRTEL": "BULLISH",
    "INFOSYS": "BEARISH",
    "TCS": "BEARISH",
}

analyze_sensex_by_sector(mock_sensex_signals)
