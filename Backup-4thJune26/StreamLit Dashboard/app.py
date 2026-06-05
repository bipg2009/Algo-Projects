import streamlit as st
import json
import os
import time

st.set_page_config(page_title="Scanner Dashboard", layout="wide", initial_sidebar_state="collapsed")

# Inject custom CSS for aesthetic neon glowing elements
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #333;
        margin-bottom: 10px;
    }
    .metric-title {
        color: #888;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        color: #FFF;
    }
    .value-green { color: #00FF00; text-shadow: 0 0 10px rgba(0,255,0,0.5); }
    .value-red { color: #FF3333; text-shadow: 0 0 10px rgba(255,51,51,0.5); }
    .value-neutral { color: #00FFFF; text-shadow: 0 0 10px rgba(0,255,255,0.5); }
    .panel-header {
        font-size: 22px;
        color: #FFF;
        margin-top: 20px;
        margin-bottom: 15px;
        border-bottom: 2px solid #444;
        padding-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

STATE_FILE = os.path.join(os.path.dirname(__file__), "live_dashboard_state.json")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            return None
    return None

def metric_card(title, value, color_class="value-neutral"):
    return f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value {color_class}">{value}</div>
    </div>
    """

# Auto-refresh logic placeholder container
placeholder = st.empty()

while True:
    state = load_state()
    
    with placeholder.container():
        st.title("⚡ Live Option Scanner Dashboard")
        
        if not state:
            st.warning("Waiting for scanner to emit live data... Ensure the scanner is running.")
            time.sleep(1)
            continue
            
        st.caption(f"Last Updated: {state.get('timestamp')} | Analyzing: {state.get('symbol')}")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        # PANEL 1: MARKET STRUCTURE
        with col1:
            st.markdown('<div class="panel-header">📈 Market Structure Panel</div>', unsafe_allow_html=True)
            
            trend = state.get("trend_direction", "UNKNOWN")
            t_color = "value-green" if trend == "UP" else "value-red"
            
            ltp = state.get('nifty_ltp', 0)
            vwap = state.get('vwap', 0)
            vwap_color = "value-green" if ltp >= vwap else "value-red"
            
            adx = state.get('adx', 0)
            adx_color = "value-green" if adx > 20 else "value-red"
            
            st.markdown(metric_card("Trend Direction", trend, t_color), unsafe_allow_html=True)
            
            c1_1, c1_2 = st.columns(2)
            c1_1.markdown(metric_card("Index LTP", f"{ltp:.2f}", vwap_color), unsafe_allow_html=True)
            c1_2.markdown(metric_card("VWAP", f"{vwap:.2f}", "value-neutral"), unsafe_allow_html=True)
            
            c1_3, c1_4 = st.columns(2)
            c1_3.markdown(metric_card("EMA 20", f"{state.get('ema20',0):.2f}", "value-neutral"), unsafe_allow_html=True)
            c1_4.markdown(metric_card("ADX", f"{adx:.2f}", adx_color), unsafe_allow_html=True)

        # PANEL 2: OPTION CHAIN
        with col2:
            st.markdown('<div class="panel-header">🔗 Option Chain Panel</div>', unsafe_allow_html=True)
            
            pcr = state.get("pcr", 1.0)
            pcr_color = "value-green" if pcr > 1.0 else "value-red"
            
            oi_pct = state.get("oi_change_pct", 0)
            oi_color = "value-green" if oi_pct < -2 else ("value-red" if oi_pct > 5 else "value-neutral")
            
            prem_pct = state.get("premium_change_pct", 0)
            prem_color = "value-green" if prem_pct > 0 else "value-red"
            
            st.markdown(metric_card("Live PCR", f"{pcr:.2f}", pcr_color), unsafe_allow_html=True)
            
            c2_1, c2_2 = st.columns(2)
            c2_1.markdown(metric_card("Target OI Change", f"{oi_pct:.2f}%", oi_color), unsafe_allow_html=True)
            c2_2.markdown(metric_card("Target Premium Chg", f"{prem_pct:.2f}%", prem_color), unsafe_allow_html=True)
            
            st.markdown(metric_card("ATM IV", f"{state.get('atm_iv', 0):.2f}", "value-neutral"), unsafe_allow_html=True)

        # PANEL 3: DECISION ENGINE
        with col3:
            st.markdown('<div class="panel-header">🎯 Decision Panel</div>', unsafe_allow_html=True)
            
            bull_score = state.get("bull_score", 0)
            if bull_score >= 110:
                score_color = "value-green"
                verdict = "STRONG BUY"
            elif bull_score >= 95:
                score_color = "value-green"
                verdict = "BUY"
            elif bull_score >= 80:
                score_color = "value-neutral"
                verdict = "WATCHLIST"
            else:
                score_color = "value-red"
                verdict = "IGNORE"
                
            st.markdown(metric_card("Bull Score", f"{bull_score}/165", score_color), unsafe_allow_html=True)
            st.markdown(metric_card("System Verdict", verdict, score_color), unsafe_allow_html=True)
            
            st.markdown("### Score Breakdown")
            bd = state.get("score_breakdown", {})
            for key, val in bd.items():
                val_str = f"+{val}" if val > 0 else str(val)
                st.markdown(f"**{key.upper()}:** `{val_str}`")

    time.sleep(1) # Refresh interval
