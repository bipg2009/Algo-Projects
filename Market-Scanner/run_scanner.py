from scanner_engine import get_breakout_stocks, get_value_stocks
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

def print_section_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}".upper())
    print("=" * 60)

def display_results(results_list, columns):
    if not results_list:
        print("  No stocks found matching the criteria today.\n")
        return
        
    df = pd.DataFrame(results_list)
    df = df[columns]
    print(df.to_string(index=False))
    print("\n")

def main():
    categories = ["Large Cap", "Mid Cap", "Small Cap", "FinCap"]
    
    print("\n" + "#" * 60)
    print("      STOCK FINDER: MARKET SCANNER REPORT")
    print("      (52-Week Breakout & Deep Value)")
    print("#" * 60 + "\n")
    
    for category in categories:
        print(f"Fetching data for {category} via Dhan API...")
        
        print_section_header(f"{category} - Momentum Leaders (52W High Breakouts)")
        try:
            breakout_results = get_breakout_stocks(category)
            display_results(breakout_results, ["Rank", "Symbol", "CMP", "52W_High", "Volume_Surge"])
        except Exception as e:
            print(f"Error fetching {category} breakout data: {e}")
            
        print_section_header(f"{category} - Deep Value Candidates (Near 52W Low)")
        try:
            value_results = get_value_stocks(category)
            display_results(value_results, ["Rank", "Symbol", "CMP", "52W_Low", "Distance"])
        except Exception as e:
            print(f"Error fetching {category} value data: {e}")

    print("\n" + "=" * 60)
    print("  SCAN COMPLETE")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
