import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit.components.v1 as components
import os
from datetime import datetime, date, time, timezone, timedelta

# Auto-refresh helper (every 5 minutes for TV loop stability)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=300000, key="data_loop_refresh")
except Exception:
    pass

# --- 1. PAGE CONFIGURATION & CLEAN LIGHT THEME CSS ---
st.set_page_config(
    page_title="Innovation Lab – HVAC Monitoring",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* 1. Base App & Canvas: Crisp Clean Light Theme */
    .stApp, [data-testid="stAppViewContainer"], .main {
        background-color: #f8fafc !important;
        color: #0f172a !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    .main .block-container {
        padding-top: 1.0rem;
        padding-bottom: 5rem;
        max-width: 98%;
    }
    
    /* 2. Search Toolbar */
    .filter-toolbar {
        background-color: #ffffff !important;
        border: 1.5px solid #e2e8f0 !important;
        border-radius: 14px;
        padding: 10px 20px;
        margin-bottom: 18px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
    }
    
    /* 3. Metric Cards */
    .metric-card-box {
        background-color: #ffffff !important;
        border: 1.5px solid #e2e8f0 !important;
        border-radius: 18px;
        padding: 16px 16px;
        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.03);
        height: 100%;
        min-height: 175px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-sizing: border-box;
    }
    
    .card-top-title {
        font-size: 16.5px;
        font-weight: 800;
        color: #1e293b !important;
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 0;
        padding: 0;
    }

    .graph-section-title {
        font-size: 17px;
        font-weight: 800;
        color: #1e293b !important;
        margin-top: 8px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .metric-main-val {
        font-size: clamp(28px, 2.5vw, 40px);
        font-weight: 900;
        color: #0f172a !important;
        line-height: 1.05;
        margin: 4px 0 2px 0;
    }
    
    .metric-label-muted {
        font-size: 12px;
        font-weight: 800;
        color: #64748b !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .metric-sub-unit {
        font-size: 11.5px;
        font-weight: 700;
        color: #64748b !important;
    }

    /* Distinct Compartment Boxes for Temperature Display */
    .temp-compartment {
        flex: 1;
        background-color: #ffffff;
        border: 1.5px solid #e2e8f0;
        border-radius: 12px;
        padding: 10px 4px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
    }
    .temp-divider {
        width: 1.5px;
        background-color: #e2e8f0;
        height: 52px;
        margin: 0 4px;
        align-self: center;
    }

    /* 4. Thermal Comfort Badge */
    .comfort-card-box {
        background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
        border-radius: 18px;
        padding: 14px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        height: 100%;
        min-height: 175px;
        box-shadow: 0 4px 18px rgba(22, 163, 74, 0.35);
        animation: comfortPulse 3s infinite ease-in-out;
        box-sizing: border-box;
    }
    @keyframes comfortPulse {
        0%, 100% { box-shadow: 0 0 12px rgba(22, 163, 74, 0.25); }
        50% { box-shadow: 0 0 26px rgba(22, 163, 74, 0.55); }
    }
    
    /* 5. Radial Saving Ring Gauge */
    .gauge-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        height: 100%;
    }
    .circular-gauge {
        position: relative;
        width: 120px;
        height: 120px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .circular-gauge-inner {
        position: absolute;
        width: 92px;
        height: 92px;
        background: #ffffff !important;
        border-radius: 50%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.06);
    }
    
    .circle-dot {
        height: 14px;
        width: 14px;
        border-radius: 50%;
        display: inline-block;
        animation: blinkLive 2s infinite ease-in-out;
    }
    @keyframes blinkLive {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.15); }
    }
    .circle-green { background-color: #16a34a; box-shadow: 0 0 10px rgba(22, 163, 74, 0.8); }
    .circle-gray { background-color: #94a3b8; }
</style>
""", unsafe_allow_html=True)

# --- 2. AUTOMATIC SMOOTH TV SCROLL LOOP ---
components.html("""
<script>
    function startTVScroll() {
        const parentDoc = window.parent.document;
        const scrollContainer = parentDoc.querySelector('[data-testid="stAppViewContainer"]') || 
                                parentDoc.querySelector('.main') || 
                                parentDoc.documentElement;

        if (!scrollContainer) {
            setTimeout(startTVScroll, 500);
            return;
        }

        let scrollSpeed = 1;
        let intervalMs = 30;
        let isPaused = false;

        setInterval(() => {
            if (isPaused) return;

            const maxScroll = scrollContainer.scrollHeight - scrollContainer.clientHeight;
            if (maxScroll <= 10) return;

            if (scrollContainer.scrollTop >= maxScroll - 4) {
                isPaused = true;
                setTimeout(() => {
                    scrollContainer.scrollTo({ top: 0, behavior: 'smooth' });
                    setTimeout(() => {
                        isPaused = false;
                    }, 3500);
                }, 3000);
            } else {
                scrollContainer.scrollTop += scrollSpeed;
            }
        }, intervalMs);
    }

    if (window.parent.document.readyState === 'complete') {
        startTVScroll();
    } else {
        window.parent.addEventListener('load', startTVScroll);
    }
</script>
""", height=0, width=0)

# --- 3. DATA LOADING & CSV DATE PARSING ---
@st.cache_data(ttl=60)
def load_data():
    try:
        df_hvac = pd.read_csv('hvac_comparison.csv')
    except Exception as e:
        st.error(f"Could not read hvac_comparison.csv: {e}")
        st.stop()

    df_hvac['timestamp'] = pd.to_datetime(df_hvac['timestamp'])

    forecast_filename = 'occupancy_forecast_2.csv' if os.path.exists('occupancy_forecast_2.csv') else 'occupancy_forecast.csv'
    if os.path.exists(forecast_filename):
        try:
            with open(forecast_filename, 'r') as f:
                first_line = f.readline()
            sep = ';' if ';' in first_line else ','
            df_fc = pd.read_csv(forecast_filename, sep=sep)
            
            if 'timestamp' in df_fc.columns:
                df_fc['timestamp'] = pd.to_datetime(df_fc['timestamp'], format='%d/%m/%Y %H:%M', errors='coerce')
                df_fc['timestamp'] = df_fc['timestamp'].fillna(pd.to_datetime(df_fc['timestamp'], errors='coerce'))
                cols_to_use = [c for c in ['timestamp', 'occupancystatus', 'deviceid'] if c in df_fc.columns]
                df_hvac = pd.merge(df_hvac, df_fc[cols_to_use], on='timestamp', how='left')
        except Exception:
            pass

    df = df_hvac.set_index('timestamp').sort_index()
    return df

df_full = load_data()
all_dates = df_full.index.normalize().unique().date

# Filter out weekend days (Saturday=5, Sunday=6) -> Keep only Monday to Friday
business_dates = [d for d in all_dates if d.weekday() < 5]

# Select default benchmark date based on business dates (prioritize Monday, Sep 29, 2025)
sep29_candidates = [d for d in business_dates if d.year == 2025 and d.month == 9 and d.day == 29]
csv_default_date = sep29_candidates[0] if sep29_candidates else business_dates[-1]

# Real-time Melbourne Clock
try:
    import pytz
    melbourne_tz = pytz.timezone('Australia/Melbourne')
    now_melbourne = datetime.now(melbourne_tz)
except Exception:
    melbourne_tz = timezone(timedelta(hours=11))
    now_melbourne = datetime.now(melbourne_tz)

real_live_time = now_melbourne.time()

# --- 4. TOP HEADER BAR ---
if 'active_date' not in st.session_state:
    st.session_state.active_date = csv_default_date

col_head_left, col_head_mid, col_head_right = st.columns([2.5, 1.3, 1.0])

with col_head_left:
    st.markdown("""
        <div style="line-height: 1.2;">
            <div style="font-size: 38px; font-weight: 900; color: #0f172a; letter-spacing: -0.5px;">Innovation Lab – HVAC Monitoring</div>
            <div style="font-size: 19px; font-weight: 700; color: #64748b; margin-top: 3px;">Occupancy Prediction Based Control</div>
        </div>
    """, unsafe_allow_html=True)

with col_head_mid:
    header_date_str = st.session_state.active_date.strftime('%a, %d %b %Y')
    st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 24px; margin-top: 6px;">
            <div style="text-align: right; line-height: 1.2;">
                <div style="font-size: 15px; color: #64748b; font-weight: 800;">📅 {header_date_str}</div>
                <div style="font-size: 28px; font-weight: 900; color: #0f172a;">{now_melbourne.strftime('%H:%M:%S')}</div>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <span class="circle-dot circle-green"></span>
                <div style="line-height: 1.1;">
                    <div style="font-size: 17px; font-weight: 900; color: #0f172a;">System Online</div>
                    <div style="font-size: 12.5px; color: #64748b; font-weight: 600;">All sensors connected</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_head_right:
    st.selectbox("Select Zone:", ["Zone: Innovation Lab", "Zone: Meeting Room", "Zone: Open Workspace"], label_visibility="collapsed")

# --- 5. SEARCHABLE DATE & TIME CONTROL TOOLBAR ---
st.markdown("<div class='filter-toolbar'>", unsafe_allow_html=True)
c_mode, c_date, c_time, c_track = st.columns([1.0, 1.3, 1.7, 1.2])

with c_mode:
    is_live_mode = st.toggle("🔴 Real-Time Clock Sync", value=True, help="Toggle OFF to search and jump to any historical business day.")

if is_live_mode:
    active_date = csv_default_date
    st.session_state.active_date = active_date
    if real_live_time < time(8, 0):
        active_time = time(8, 0)
    elif real_live_time > time(18, 0):
        active_time = time(18, 0)
    else:
        active_time = real_live_time
        
    with c_date:
        st.markdown(f"<div style='font-size: 16px; font-weight: 800; padding-top: 6px; color: #334155;'>📅 Active Date: <b>{active_date.strftime('%a, %d %b %Y')}</b></div>", unsafe_allow_html=True)
    with c_time:
        tz_abbr = now_melbourne.strftime('%Z') or "AEDT"
        st.markdown(f"<div style='font-size: 16px; font-weight: 800; padding-top: 6px; color: #2563eb;'>⏱️ Real-Time: <b>{active_time.strftime('%H:%M:%S')} ({tz_abbr})</b></div>", unsafe_allow_html=True)
else:
    with c_date:
        date_options = [d.strftime('%a, %d %b %Y') for d in business_dates]
        default_str = csv_default_date.strftime('%a, %d %b %Y')
        default_idx = date_options.index(default_str) if default_str in date_options else len(date_options)-1
        sel_date_str = st.selectbox("🔍 Search Date (Mon–Fri):", options=date_options, index=default_idx)
        active_date = datetime.strptime(sel_date_str, '%a, %d %b %Y').date()
        st.session_state.active_date = active_date

    df_day_candidates = df_full[df_full.index.date == active_date]
    day_times = [
        t.strftime('%H:%M') 
        for t in df_day_candidates.index.time 
        if time(8, 0) <= t <= time(18, 0)
    ]

    with c_time:
        if len(day_times) > 0:
            default_slider_val = "12:00" if "12:00" in day_times else day_times[len(day_times)//2]
            sel_time_str = st.select_slider(
                "🔍 Select Time (08:00 AM - 06:00 PM):", 
                options=day_times, 
                value=default_slider_val
            )
            h, m = map(int, sel_time_str.split(':'))
            active_time = time(h, m)
        else:
            active_time = time(12, 0)

with c_track:
    energy_view_mode = st.radio(
        "Energy Tracking Scope:",
        options=["Daily (08:00-18:00)", "Monthly Cumulative (Mon-Fri)"],
        horizontal=True,
        index=0
    )

st.markdown("</div>", unsafe_allow_html=True)

# Locked working timeframe: 08:00 AM to 06:00 PM (18:00)
t_start = datetime.combine(active_date, time(8, 0))
t_end = datetime.combine(active_date, time(18, 0))

# Filter dataset to selected date and active time
df_day = df_full[df_full.index.date == active_date].copy()
df_live = df_day[df_day.index.time <= active_time]
if df_live.empty:
    df_live = df_day.iloc[:1]

# Current Telemetry Values
cur_occ = int(df_live['occupancy_now'].iloc[-1])
pred_occ = int(df_live['occupancy_forecast_15min'].iloc[-1])
zone_temp = df_live['predictive_room_temperature_C'].iloc[-1]
outdoor_temp = df_live['outdoor_temperature_C'].iloc[-1]
setpoint_temp = 24.0
cur_power = df_live['predictive_hvac_power_kW'].iloc[-1]

# --- DAILY ENERGY CALCULATIONS (FROM 08:00 AM) ---
df_day['pred_kwh_interval'] = df_day['predictive_hvac_power_kW'] * (5.0 / 60.0)
df_day['sched_kwh_interval'] = df_day['scheduled_hvac_power_kW'] * (5.0 / 60.0)

day_work_mask = (df_day.index >= t_start)
df_day['pred_energy_cum_day'] = 0.0
df_day['sched_energy_cum_day'] = 0.0
df_day.loc[day_work_mask, 'pred_energy_cum_day'] = df_day.loc[day_work_mask, 'pred_kwh_interval'].cumsum()
df_day.loc[day_work_mask, 'sched_energy_cum_day'] = df_day.loc[day_work_mask, 'sched_kwh_interval'].cumsum()

df_live = df_day[df_day.index.time <= active_time]
if df_live.empty:
    df_live = df_day.iloc[:1]

df_live_since_8am = df_live[df_live.index >= t_start]
if not df_live_since_8am.empty:
    pred_energy_today = df_live_since_8am['pred_energy_cum_day'].iloc[-1]
    sched_energy_today = df_live_since_8am['sched_energy_cum_day'].iloc[-1]
else:
    pred_energy_today = 0.0
    sched_energy_today = 0.0

daily_energy_saved = max(0.0, sched_energy_today - pred_energy_today)
daily_pct_saved = (daily_energy_saved / sched_energy_today * 100) if sched_energy_today > 0 else 0.0

# --- MONTHLY CUMULATIVE ENERGY (WEEKDAYS ONLY: 8 AM - 6 PM) ---
active_month = active_date.month
active_year = active_date.year
month_name = datetime(active_year, active_month, 1).strftime('%B %Y')

df_month_raw = df_full[(df_full.index.year == active_year) & (df_full.index.month == active_month)].copy()
mask_business_hours = (
    (df_month_raw.index.dayofweek < 5) & 
    (df_month_raw.index.time >= time(8, 0)) & 
    (df_month_raw.index.time <= time(18, 0))
)
df_month_hours = df_month_raw[mask_business_hours].copy()

df_month_hours['step_pred_kwh'] = df_month_hours['predictive_hvac_power_kW'] * (5.0 / 60.0)
df_month_hours['step_sched_kwh'] = df_month_hours['scheduled_hvac_power_kW'] * (5.0 / 60.0)

daily_summary = df_month_hours.groupby(df_month_hours.index.date).agg({
    'step_pred_kwh': 'sum',
    'step_sched_kwh': 'sum'
}).rename(columns={'step_pred_kwh': 'pred_kwh', 'step_sched_kwh': 'sched_kwh'})

daily_summary['pred_kwh_cum'] = daily_summary['pred_kwh'].cumsum()
daily_summary['sched_kwh_cum'] = daily_summary['sched_kwh'].cumsum()
daily_summary['saved_kwh_cum'] = (daily_summary['sched_kwh_cum'] - daily_summary['pred_kwh_cum']).clip(lower=0.0)

if active_date in daily_summary.index:
    month_cum_pred = daily_summary.loc[active_date, 'pred_kwh_cum']
    month_cum_sched = daily_summary.loc[active_date, 'sched_kwh_cum']
    month_cum_saved = daily_summary.loc[active_date, 'saved_kwh_cum']
else:
    month_cum_pred = daily_summary['pred_kwh_cum'].iloc[-1] if not daily_summary.empty else 0.0
    month_cum_sched = daily_summary['sched_kwh_cum'].iloc[-1] if not daily_summary.empty else 0.0
    month_cum_saved = (month_cum_sched - month_cum_pred) if month_cum_sched > month_cum_pred else 0.0

month_pct_saved = (month_cum_saved / month_cum_sched * 100) if month_cum_sched > 0 else 0.0

if energy_view_mode == "Monthly Cumulative (Mon-Fri)":
    card_title = f"📊 Monthly Cumulative Energy ({month_name})"
    disp_pred = month_cum_pred
    disp_sched = month_cum_sched
    disp_saved = month_cum_saved
    disp_pct = month_pct_saved
else:
    card_title = "📊 Daily Energy Usage (Since 08:00 AM)"
    disp_pred = pred_energy_today
    disp_sched = sched_energy_today
    disp_saved = daily_energy_saved
    disp_pct = daily_pct_saved

gauge_pct = min(100.0, max(0.0, disp_pct))
gauge_deg = int((gauge_pct / 100.0) * 360)

# Colors and chart styling for crisp light theme
CHART_BG = "#ffffff"
GRID_COLOR = "#f1f5f9"
TEXT_COLOR = "#334155"
CHART_HEIGHT = 250

day_window_data = df_day[(df_day.index >= t_start) & (df_day.index <= t_end)]
max_occ_day = max(day_window_data['occupancy_now'].max(), day_window_data['occupancy_forecast_15min'].max())
y_upper = max(8, int(max_occ_day) + 2) if pd.notna(max_occ_day) else 8

# ==============================================================================
# --- TOP SUMMARY ROW: 5 CLEAN LIGHT CARDS (INCL. CURRENT POWER) ---
# ==============================================================================
kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns([0.95, 1.35, 0.85, 0.95, 1.65])

# 1. Occupancy Card
if pred_occ > cur_occ:
    trend_symbol = "↑"
    trend_color = "#dc2626"
elif pred_occ < cur_occ:
    trend_symbol = "↓"
    trend_color = "#16a34a"
else:
    trend_symbol = "="
    trend_color = "#2563eb"

with kpi_col1:
    st.markdown(f"""
    <div class="metric-card-box">
        <div class="card-top-title">👥 Occupancy</div>
        <div style="display: flex; justify-content: space-around; align-items: center; text-align: center; margin: auto 0;">
            <div>
                <div class="metric-label-muted">Current</div>
                <div class="metric-main-val">{cur_occ}</div>
                <div class="metric-sub-unit">people</div>
            </div>
            <div style="border-left: 1.5px solid #e2e8f0; height: 60px;"></div>
            <div>
                <div class="metric-label-muted">15 min ahead</div>
                <div class="metric-main-val">
                    {pred_occ} 
                    <span style="font-size: 26px; font-weight: 900; color: {trend_color}; vertical-align: middle;">
                        {trend_symbol}
                    </span>
                </div>
                <div class="metric-sub-unit">people</div>
            </div>
        </div>
        <div style="height: 2px;"></div>
    </div>
    """, unsafe_allow_html=True)

# 2. Temperature Card with Clear Distinct Compartments & Visible Boundaries
with kpi_col2:
    st.markdown(f"""
    <div class="metric-card-box">
        <div class="card-top-title">🌡️ Temperature (°C)</div>
        <div style="display: flex; justify-content: space-between; align-items: center; gap: 6px; margin: auto 0;">
            <div class="temp-compartment">
                <div class="metric-label-muted" style="font-size: 11px;">Zone</div>
                <div class="metric-main-val" style="color: #0284c7; font-size: 30px;">{zone_temp:.1f}</div>
                <div class="metric-sub-unit" style="font-size: 10.5px;">°C Actual</div>
            </div>
            <div class="temp-divider"></div>
            <div class="temp-compartment">
                <div class="metric-label-muted" style="font-size: 11px;">Setpoint</div>
                <div class="metric-main-val" style="color: #16a34a; font-size: 30px;">{setpoint_temp:.1f}</div>
                <div class="metric-sub-unit" style="font-size: 10.5px;">°C Target</div>
            </div>
            <div class="temp-divider"></div>
            <div class="temp-compartment">
                <div class="metric-label-muted" style="font-size: 11px;">Outdoor</div>
                <div class="metric-main-val" style="color: #ea580c; font-size: 30px;">{outdoor_temp:.1f}</div>
                <div class="metric-sub-unit" style="font-size: 10.5px;">°C Ambient</div>
            </div>
        </div>
        <div style="height: 2px;"></div>
    </div>
    """, unsafe_allow_html=True)

# 3. Thermal Comfort Hero Card
with kpi_col3:
    is_comfort = (22.8 <= zone_temp <= 25.8)
    comfort_label = "COMFORTABLE" if is_comfort else "DEVIATION"
    comfort_icon = "😊" if is_comfort else "⚠️"
    bg_comfort = "linear-gradient(135deg, #16a34a 0%, #15803d 100%)" if is_comfort else "linear-gradient(135deg, #d97706 0%, #b45309 100%)"
    st.markdown(f"""
    <div class="comfort-card-box" style="background: {bg_comfort};">
        <div style="font-size: 42px; line-height: 1.1; margin-bottom: 6px;">
            {comfort_icon}
        </div>
        <div>
            <div style="font-size: 11px; font-weight: 800; color: rgba(255,255,255,0.85); text-transform: uppercase; letter-spacing: 0.5px;">
                Thermal Comfort
            </div>
            <div style="font-size: 17px; font-weight: 900; letter-spacing: 0.5px; line-height: 1.2; color: #ffffff;">
                {comfort_label}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 4. Current Power Card (Instant Demand kW)
with kpi_col4:
    st.markdown(f"""
    <div class="metric-card-box">
        <div class="card-top-title">⚡ Current Power</div>
        <div style="text-align: center; margin: auto 0; background-color: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 12px; padding: 12px 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
            <div class="metric-label-muted" style="font-size: 11px;">Instant Demand</div>
            <div class="metric-main-val" style="color: #0284c7; font-size: 34px; margin: 2px 0;">
                {cur_power:.2f}
            </div>
            <div class="metric-sub-unit" style="font-size: 11px; font-weight: 700;">kW active load</div>
        </div>
        <div style="height: 2px;"></div>
    </div>
    """, unsafe_allow_html=True)

# 5. Daily Energy Usage Card (Expanded & Spacious)
with kpi_col5:
    st.markdown(f"""
    <div class="metric-card-box">
        <div class="card-top-title">{card_title}</div>
        <div class="gauge-container" style="padding: 0 2px; margin: auto 0;">
            <div style="display: flex; align-items: center; justify-content: space-around; flex: 1; text-align: center; gap: 10px;">
                <div style="background-color: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 12px; padding: 8px 10px; flex: 1; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                    <div class="metric-label-muted" style="font-size: 10.5px;">Predictive</div>
                    <div style="font-size: 26px; font-weight: 900; color: #2563eb; line-height: 1.05; margin-top: 2px;">
                        {disp_pred:.2f}
                    </div>
                    <div class="metric-sub-unit" style="font-size: 10.5px; font-weight: 700;">kWh</div>
                </div>
                <div style="border-left: 1.5px solid #e2e8f0; height: 50px;"></div>
                <div style="background-color: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 12px; padding: 8px 10px; flex: 1; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                    <div class="metric-label-muted" style="font-size: 10.5px;">Baseline</div>
                    <div style="font-size: 26px; font-weight: 900; color: #d97706; line-height: 1.05; margin-top: 2px;">
                        {disp_sched:.2f}
                    </div>
                    <div class="metric-sub-unit" style="font-size: 10.5px; font-weight: 700;">kWh</div>
                </div>
            </div>
            <!-- Radial Savings Ring Gauge -->
            <div class="circular-gauge" style="background: conic-gradient(#16a34a 0deg {gauge_deg}deg, #e2e8f0 {gauge_deg}deg 360deg);">
                <div class="circular-gauge-inner">
                    <div style="font-size: 9.5px; font-weight: 900; color: #16a34a; text-transform: uppercase; letter-spacing: 0.8px;">SAVING</div>
                    <div style="font-size: 24px; font-weight: 900; color: #0f172a; line-height: 1.05;">{disp_pct:.1f}%</div>
                    <div style="font-size: 10.5px; font-weight: 700; color: #64748b; margin-top: 1px;">-{disp_saved:.2f} kWh</div>
                </div>
            </div>
        </div>
        <div style="height: 2px;"></div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

# ==============================================================================
# --- 4 FULL-WIDTH STACKED GRAPHS ---
# ==============================================================================

# --- GRAPH 1: OCCUPANCY TRACKING & 15 MIN FORECAST ---
st.markdown("<div class='graph-section-title'>👥 Occupancy Tracking & 15 Min Forecast</div>", unsafe_allow_html=True)
fig_occ = go.Figure()
fig_occ.add_trace(go.Scatter(
    x=df_live.index, y=df_live['occupancy_forecast_15min'],
    mode='lines', name='15 Min Forecast',
    line=dict(color='#f97316', width=2.8, dash='dash')
))
fig_occ.add_trace(go.Scatter(
    x=df_live.index, y=df_live['occupancy_now'],
    mode='lines', name='Actual Occupancy',
    line=dict(color='#0284c7', width=3.2)
))
fig_occ.add_vline(x=datetime.combine(active_date, active_time), line_width=2, line_color="#ef4444")

fig_occ.update_layout(
    height=CHART_HEIGHT,
    margin=dict(l=25, r=25, t=10, b=20),
    xaxis_title="", yaxis_title="People",
    plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
    font=dict(color=TEXT_COLOR, size=12),
    xaxis=dict(showgrid=True, gridcolor=GRID_COLOR, tickfont=dict(size=11, color=TEXT_COLOR), range=[t_start, t_end]),
    yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, tickfont=dict(size=11, color=TEXT_COLOR), range=[0, y_upper], dtick=1),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=11, color=TEXT_COLOR),
        bgcolor="rgba(255, 255, 255, 0.9)",
        bordercolor="#e2e8f0",
        borderwidth=1
    )
)
st.plotly_chart(fig_occ, use_container_width=True)

st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

# --- GRAPH 2: TEMPERATURE TREND (°C) ---
st.markdown("<div class='graph-section-title'>🌡️ Temperature Trend (°C)</div>", unsafe_allow_html=True)
fig_temp = go.Figure()

# Comfort band shading (22.8 - 25.8 °C)
fig_temp.add_hrect(
    y0=22.8, y1=25.8, line_width=0, fillcolor="#22c55e", opacity=0.18,
    annotation_text="Comfort (22.8 - 25.8°C)", annotation_position="top right", annotation_font_size=11, annotation_font_color="#166534"
)
# Setpoint (24.0 °C)
fig_temp.add_hline(
    y=24.0, line_dash="dash", line_color="#10b981", line_width=2, 
    annotation_text="Setpoint (24°C)", annotation_position="top left", annotation_font_size=11, annotation_font_color="#047857"
)
# Zone Temperature
fig_temp.add_trace(go.Scatter(
    x=df_live.index, y=df_live['predictive_room_temperature_C'],
    mode='lines', name='Zone Temp',
    line=dict(color='#0284c7', width=3.2)
))
# Outdoor Temperature
fig_temp.add_trace(go.Scatter(
    x=df_live.index, y=df_live['outdoor_temperature_C'],
    mode='lines', name='Outdoor Temp',
    line=dict(color='#ea580c', width=2.4, dash='dot')
))
fig_temp.add_vline(x=datetime.combine(active_date, active_time), line_width=2, line_color="#ef4444")

fig_temp.update_layout(
    height=CHART_HEIGHT,
    margin=dict(l=25, r=25, t=10, b=20),
    xaxis_title="", yaxis_title="Temperature (°C)",
    plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
    font=dict(color=TEXT_COLOR, size=12),
    xaxis=dict(showgrid=True, gridcolor=GRID_COLOR, tickfont=dict(size=11, color=TEXT_COLOR), range=[t_start, t_end]),
    yaxis=dict(
        showgrid=True, 
        gridcolor=GRID_COLOR, 
        tickfont=dict(size=11, color=TEXT_COLOR),
        range=[22.0, 34.0],
        dtick=2.0
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=11, color=TEXT_COLOR),
        bgcolor="rgba(255, 255, 255, 0.9)",
        bordercolor="#e2e8f0",
        borderwidth=1
    )
)
st.plotly_chart(fig_temp, use_container_width=True)

st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

# --- GRAPH 3: POWER DEMAND PROFILE (KW) ---
st.markdown("<div class='graph-section-title'>⚡ Power Demand Profile (kW)</div>", unsafe_allow_html=True)
fig_pwr = go.Figure()

df_live_plot = df_live[df_live.index >= t_start]

# Baseline Power (kW)
fig_pwr.add_trace(go.Scatter(
    x=df_live_plot.index, y=df_live_plot['scheduled_hvac_power_kW'],
    mode='lines', name='Baseline Power (kW)',
    line=dict(color='#fdba74', width=2.2, dash='dot')
))
# Predictive HVAC Power (kW)
fig_pwr.add_trace(go.Scatter(
    x=df_live_plot.index, y=df_live_plot['predictive_hvac_power_kW'],
    mode='lines', name='Predictive Power (kW)',
    line=dict(color='#0284c7', width=2.8),
    fill='tozeroy', fillcolor='rgba(2, 132, 199, 0.12)'
))
fig_pwr.add_vline(x=datetime.combine(active_date, active_time), line_width=2, line_color="#ef4444")

fig_pwr.update_layout(
    height=CHART_HEIGHT,
    margin=dict(l=25, r=25, t=10, b=20),
    xaxis_title="", yaxis_title="Power Demand (kW)",
    plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
    font=dict(color=TEXT_COLOR, size=12),
    xaxis=dict(showgrid=True, gridcolor=GRID_COLOR, tickfont=dict(size=11, color=TEXT_COLOR), range=[t_start, t_end]),
    yaxis=dict(
        showgrid=True, 
        gridcolor=GRID_COLOR, 
        tickfont=dict(size=11, color=TEXT_COLOR),
        range=[0.0, 2.0],
        dtick=0.5
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=11, color=TEXT_COLOR),
        bgcolor="rgba(255, 255, 255, 0.9)",
        bordercolor="#e2e8f0",
        borderwidth=1
    )
)
st.plotly_chart(fig_pwr, use_container_width=True)

st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

# --- GRAPH 4: DAILY ENERGY CUMULATIVE (KWH) ---
if energy_view_mode == "Monthly Cumulative (Mon-Fri)":
    st.markdown(f"<div class='graph-section-title'>📊 Monthly Cumulative Energy Progression ({month_name})</div>", unsafe_allow_html=True)
    fig_energy = go.Figure()

    dates_list = [d.strftime('%a %d %b') for d in daily_summary.index]

    # Scheduled Baseline Cumulative (Business Days Only)
    fig_energy.add_trace(go.Scatter(
        x=dates_list, y=daily_summary['sched_kwh_cum'],
        mode='lines+markers', name='Baseline Cumulative',
        line=dict(color='#ea580c', width=3, dash='dash'),
        marker=dict(size=4)
    ))
    
    # Predictive HVAC Cumulative (Business Days Only)
    fig_energy.add_trace(go.Scatter(
        x=dates_list, y=daily_summary['pred_kwh_cum'],
        mode='lines+markers', name='Predictive Cumulative',
        line=dict(color='#0284c7', width=3.2),
        fill='tozeroy', fillcolor='rgba(2, 132, 199, 0.12)',
        marker=dict(size=4)
    ))

    active_label = active_date.strftime('%a %d %b')
    if active_label in dates_list:
        fig_energy.add_vline(x=active_label, line_width=2, line_color="#ef4444")

    y_max = daily_summary['sched_kwh_cum'].max() * 1.1 if not daily_summary.empty else 10.0

    fig_energy.update_layout(
        height=CHART_HEIGHT,
        margin=dict(l=25, r=25, t=10, b=20),
        xaxis_title="Business Day (08:00 AM - 06:00 PM)", 
        yaxis_title="Cumulative Energy (kWh)",
        plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
        font=dict(color=TEXT_COLOR, size=12),
        xaxis=dict(showgrid=True, gridcolor=GRID_COLOR, tickfont=dict(size=11, color=TEXT_COLOR)),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, tickfont=dict(size=11, color=TEXT_COLOR), range=[0.0, y_max], zeroline=False),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color=TEXT_COLOR),
            bgcolor="rgba(255, 255, 255, 0.9)",
            bordercolor="#e2e8f0",
            borderwidth=1
        )
    )
    st.plotly_chart(fig_energy, use_container_width=True)
else:
    st.markdown("<div class='graph-section-title'>📊 Daily Energy: Cumulative (kWh)</div>", unsafe_allow_html=True)
    fig_energy = go.Figure()
    
    # Cumulative Energy Consumed Since 08:00 AM (Single Y-Axis, kWh)
    fig_energy.add_trace(go.Scatter(
        x=df_live_plot.index, y=df_live_plot['sched_energy_cum_day'],
        mode='lines', name='Baseline Cumulative',
        line=dict(color='#ea580c', width=3, dash='dash')
    ))
    fig_energy.add_trace(go.Scatter(
        x=df_live_plot.index, y=df_live_plot['pred_energy_cum_day'],
        mode='lines', name='Predictive Cumulative',
        line=dict(color='#0284c7', width=3.5),
        fill='tozeroy', fillcolor='rgba(2, 132, 199, 0.10)'
    ))
    
    fig_energy.add_vline(x=datetime.combine(active_date, active_time), line_width=2, line_color="#ef4444")
    
    max_cum_e = day_window_data['sched_energy_cum_day'].max() if not day_window_data.empty else 5.0
    y_energy_cum_upper = max(2.0, round(float(max_cum_e) + 0.6, 1))

    fig_energy.update_layout(
        height=CHART_HEIGHT,
        margin=dict(l=25, r=25, t=10, b=20),
        xaxis_title="", 
        plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
        font=dict(color=TEXT_COLOR, size=12),
        xaxis=dict(showgrid=True, gridcolor=GRID_COLOR, tickfont=dict(size=11, color=TEXT_COLOR), range=[t_start, t_end]),
        yaxis=dict(
            title="Cumulative Energy (kWh)",
            showgrid=True, 
            gridcolor=GRID_COLOR, 
            tickfont=dict(size=11, color=TEXT_COLOR),
            range=[0.0, y_energy_cum_upper],
            zeroline=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color=TEXT_COLOR),
            bgcolor="rgba(255, 255, 255, 0.9)",
            bordercolor="#e2e8f0",
            borderwidth=1
        )
    )
    st.plotly_chart(fig_energy, use_container_width=True)

# Bottom spacing to keep the auto-scroll loop smooth on all TV resolutions
st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)
