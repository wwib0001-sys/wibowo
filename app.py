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

# --- 1. PAGE CONFIGURATION & BIG SCREEN CSS ---
st.set_page_config(
    page_title="Innovation Lab – HVAC Monitoring",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* Clean, high-contrast light background */
    .stApp {
        background-color: #f8fafc !important;
        color: #0f172a !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 6rem;
        max-width: 98%;
    }
    
    /* Search Toolbar */
    .filter-toolbar {
        background-color: #ffffff;
        border: 1.5px solid #cbd5e1;
        border-radius: 14px;
        padding: 12px 20px;
        margin-bottom: 22px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }
    
    /* Aligned Square Metric Cards */
    .metric-card-box {
        background-color: #ffffff;
        border: 1.5px solid #cbd5e1;
        border-radius: 18px;
        padding: 20px 22px;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.05);
        height: 205px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-sizing: border-box;
    }
    
    .card-top-title {
        font-size: 20px;
        font-weight: 800;
        color: #1e293b;
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 0;
        padding: 0;
    }
    
    .metric-main-val {
        font-size: 50px;
        font-weight: 900;
        color: #0f172a;
        line-height: 1.0;
        margin: 4px 0 2px 0;
    }
    
    .metric-label-muted {
        font-size: 15px;
        font-weight: 800;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .metric-sub-unit {
        font-size: 14px;
        font-weight: 700;
        color: #64748b;
    }

    /* Green Comfort Hero Badge */
    .comfort-card-box {
        background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
        color: #ffffff;
        border-radius: 18px;
        padding: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 18px;
        height: 205px;
        box-shadow: 0 6px 24px rgba(22, 163, 74, 0.4);
        animation: comfortPulse 3s infinite ease-in-out;
        box-sizing: border-box;
    }
    @keyframes comfortPulse {
        0%, 100% { box-shadow: 0 0 16px rgba(22, 163, 74, 0.3); }
        50% { box-shadow: 0 0 30px rgba(22, 163, 74, 0.65); }
    }
    
    /* Radial Circular Ring Gauge Styling */
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
        width: 94px;
        height: 94px;
        background: #ffffff;
        border-radius: 50%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.06);
    }
    
    /* Device Status Table */
    .status-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 18px;
    }
    .status-table th {
        background-color: #e2e8f0;
        color: #334155;
        font-weight: 800;
        padding: 13px 20px;
        text-align: left;
    }
    .status-table td {
        padding: 11px 20px;
        border-bottom: 1px solid #f1f5f9;
        color: #0f172a;
        font-weight: 700;
    }
    .badge-on {
        color: #16a34a;
        font-weight: 900;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    .badge-off {
        color: #94a3b8;
        font-weight: 800;
        display: inline-flex;
        align-items: center;
        gap: 8px;
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

# --- 3. DATA LOADING ---
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
available_dates = df_full.index.normalize().unique().date

sep29_dates = [d for d in available_dates if d.month == 9 and d.day == 29]
default_date = sep29_dates[0] if sep29_dates else available_dates[-1]

# Real-time Melbourne Clock
try:
    import pytz
    melbourne_tz = pytz.timezone('Australia/Melbourne')
    now_melbourne = datetime.now(melbourne_tz)
except Exception:
    melbourne_tz = timezone(timedelta(hours=10))
    now_melbourne = datetime.now(melbourne_tz)

real_live_time = now_melbourne.time()

# --- 4. TOP HEADER BAR ---
col_head_left, col_head_mid, col_head_right = st.columns([2.5, 1.3, 1.0])

with col_head_left:
    st.markdown("""
        <div style="line-height: 1.2;">
            <div style="font-size: 38px; font-weight: 900; color: #0f172a; letter-spacing: -0.5px;">Innovation Lab – HVAC Monitoring</div>
            <div style="font-size: 20px; font-weight: 700; color: #64748b; margin-top: 3px;">Occupancy Prediction Based Control</div>
        </div>
    """, unsafe_allow_html=True)

with col_head_mid:
    st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 24px; margin-top: 6px;">
            <div style="text-align: right; line-height: 1.2;">
                <div style="font-size: 16px; color: #64748b; font-weight: 800;">📅 {default_date.strftime('%a, %d %b %Y')}</div>
                <div style="font-size: 28px; font-weight: 900; color: #0f172a;">{real_live_time.strftime('%H:%M:%S')}</div>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <span class="circle-dot circle-green"></span>
                <div style="line-height: 1.1;">
                    <div style="font-size: 18px; font-weight: 900; color: #0f172a;">System Online</div>
                    <div style="font-size: 13px; color: #64748b; font-weight: 600;">All sensors connected</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_head_right:
    st.selectbox("Select Zone:", ["Zone: Innovation Lab", "Zone: Meeting Room", "Zone: Open Workspace"], label_visibility="collapsed")

# --- 5. SEARCHABLE DATE & TIME CONTROL TOOLBAR ---
st.markdown("<div class='filter-toolbar'>", unsafe_allow_html=True)
c_mode, c_date, c_time = st.columns([1.1, 1.4, 2.0])

with c_mode:
    is_live_mode = st.toggle("🔴 Real-Time Clock Sync", value=True, help="Toggle OFF to search and jump to any historical date/time.")

if is_live_mode:
    selected_date = default_date
    active_time = real_live_time
    with c_date:
        st.markdown(f"<div style='font-size: 17px; font-weight: 800; padding-top: 6px; color: #334155;'>📅 Active Date: <b>{selected_date.strftime('%Y-%m-%d')}</b></div>", unsafe_allow_html=True)
    with c_time:
        st.markdown(f"<div style='font-size: 17px; font-weight: 800; padding-top: 6px; color: #2563eb;'>⏱️ Real-Time Tracking: <b>{active_time.strftime('%H:%M:%S')} (AEST)</b></div>", unsafe_allow_html=True)
else:
    with c_date:
        date_options = [d.strftime('%Y-%m-%d') for d in available_dates]
        default_idx = date_options.index(default_date.strftime('%Y-%m-%d')) if default_date.strftime('%Y-%m-%d') in date_options else len(date_options)-1
        sel_date_str = st.selectbox("🔍 Search Date:", options=date_options, index=default_idx)
        selected_date = datetime.strptime(sel_date_str, '%Y-%m-%d').date()

    df_day_candidates = df_full[df_full.index.date == selected_date]
    day_times = [t.strftime('%H:%M') for t in df_day_candidates.index.time]

    with c_time:
        if len(day_times) > 0:
            sel_time_str = st.select_slider("🔍 Scrub / Select Time:", options=day_times, value=day_times[len(day_times)//2])
            h, m = map(int, sel_time_str.split(':'))
            active_time = time(h, m)
        else:
            active_time = time(12, 0)

st.markdown("</div>", unsafe_allow_html=True)

# Locked working timeframe: 08:00 AM to 06:00 PM (18:00)
t_start = datetime.combine(selected_date, time(8, 0))
t_end = datetime.combine(selected_date, time(18, 0))

# Filter dataset to selected date and active time
df_day = df_full[df_full.index.date == selected_date].copy()
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
is_cooling = cur_power > 0.05
hvac_on = cur_power > 0.0

# --- CUMULATIVE ENERGY RECALCULATION (RESET AT 08:00 AM) ---
df_day['pred_energy_step'] = df_day['predictive_hvac_power_kW'] * (5.0 / 60.0)
df_day['sched_energy_step'] = df_day['scheduled_hvac_power_kW'] * (5.0 / 60.0)

day_work_mask = (df_day.index >= t_start)
df_day['pred_energy_cum_day'] = 0.0
df_day['sched_energy_cum_day'] = 0.0
df_day.loc[day_work_mask, 'pred_energy_cum_day'] = df_day.loc[day_work_mask, 'pred_energy_step'].cumsum()
df_day.loc[day_work_mask, 'sched_energy_cum_day'] = df_day.loc[day_work_mask, 'sched_energy_step'].cumsum()

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

energy_saved = max(0.0, sched_energy_today - pred_energy_today)
pct_saved = (energy_saved / sched_energy_today * 100) if sched_energy_today > 0 else 0.0

gauge_pct = min(100.0, max(0.0, pct_saved))
gauge_deg = int((gauge_pct / 100.0) * 360)

# --- 6. TOP SUMMARY CARDS (ALIGNED EXACTLY WITH THEIR GRAPHS BELOW) ---
# Column 1 aligns with: Occupancy & Temperature / Climate Control
# Column 2 aligns with: Energy Usage & Power Grid
col_top_left, col_top_right = st.columns([1.0, 1.0])

with col_top_left:
    # Sub-columns for Occupancy and Temperature
    sub_col1, sub_col2, sub_col3 = st.columns([1.1, 1.2, 0.9])
    
    # 1. Occupancy Card
    with sub_col1:
        arrow = "↑" if pred_occ >= cur_occ else "↓"
        arrow_color = "#dc2626" if pred_occ >= cur_occ else "#16a34a"
        st.markdown(f"""
        <div class="metric-card-box">
            <div class="card-top-title">👥 Occupancy</div>
            <div style="display: flex; justify-content: space-around; align-items: center; text-align: center; margin: auto 0;">
                <div>
                    <div class="metric-label-muted">Current</div>
                    <div class="metric-main-val">{cur_occ}</div>
                    <div class="metric-sub-unit">people</div>
                </div>
                <div style="border-left: 2px solid #e2e8f0; height: 68px;"></div>
                <div>
                    <div class="metric-label-muted">15 min ahead</div>
                    <div class="metric-main-val">{pred_occ} <span style="font-size: 32px; color: {arrow_color};">{arrow}</span></div>
                    <div class="metric-sub-unit">people</div>
                </div>
            </div>
            <div style="height: 4px;"></div>
        </div>
        """, unsafe_allow_html=True)
        
    # 2. Temperature Card
    with sub_col2:
        st.markdown(f"""
        <div class="metric-card-box">
            <div class="card-top-title">🌡️ Temperature (°C)</div>
            <div style="display: flex; justify-content: space-around; align-items: center; text-align: center; margin: auto 0;">
                <div>
                    <div class="metric-label-muted">Zone Temp.</div>
                    <div class="metric-main-val" style="font-size: 42px;">{zone_temp:.1f}</div>
                    <div class="metric-sub-unit">°C</div>
                </div>
                <div>
                    <div class="metric-label-muted">Setpoint</div>
                    <div class="metric-main-val" style="font-size: 42px;">{setpoint_temp:.1f}</div>
                    <div class="metric-sub-unit">°C</div>
                </div>
                <div>
                    <div class="metric-label-muted">Outdoor</div>
                    <div class="metric-main-val" style="font-size: 42px;">{outdoor_temp:.1f}</div>
                    <div class="metric-sub-unit">°C</div>
                </div>
            </div>
            <div style="height: 4px;"></div>
        </div>
        """, unsafe_allow_html=True)
        
    # 3. Thermal Comfort Hero Card
    with sub_col3:
        is_comfort = (22.8 <= zone_temp <= 25.8)
        comfort_label = "COMFORTABLE" if is_comfort else "DEVIATION"
        comfort_icon = "😊" if is_comfort else "⚠️"
        bg_comfort = "linear-gradient(135deg, #16a34a 0%, #15803d 100%)" if is_comfort else "linear-gradient(135deg, #d97706 0%, #b45309 100%)"
        st.markdown(f"""
        <div class="comfort-card-box" style="background: {bg_comfort};">
            <span style="font-size: 44px;">{comfort_icon}</span>
            <div>
                <div style="font-size: 13px; font-weight: 800; color: rgba(255,255,255,0.85); text-transform: uppercase;">Comfort</div>
                <div style="font-size: 26px; font-weight: 900; letter-spacing: 0.5px;">{comfort_label}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

with col_top_right:
    # Energy Usage Card (Full Width in Right Column, Perfectly Aligned over Energy Chart)
    st.markdown(f"""
    <div class="metric-card-box">
        <div class="card-top-title">⚡ Energy Usage Summary (Since 08:00 AM)</div>
        <div class="gauge-container" style="padding: 0 16px;">
            <div style="display: flex; gap: 40px; align-items: center;">
                <div>
                    <div class="metric-label-muted">Predictive HVAC (Actual)</div>
                    <div style="font-size: 38px; font-weight: 900; color: #2563eb; line-height: 1.1;">{pred_energy_today:.2f} <span style="font-size: 16px; font-weight: 700; color: #64748b;">kWh</span></div>
                </div>
                <div style="border-left: 2px solid #e2e8f0; height: 60px;"></div>
                <div>
                    <div class="metric-label-muted">Scheduled Baseline</div>
                    <div style="font-size: 38px; font-weight: 900; color: #d97706; line-height: 1.1;">{sched_energy_today:.2f} <span style="font-size: 16px; font-weight: 700; color: #64748b;">kWh</span></div>
                </div>
            </div>
            <div class="circular-gauge" style="background: conic-gradient(#16a34a 0deg {gauge_deg}deg, #e2e8f0 {gauge_deg}deg 360deg);">
                <div class="circular-gauge-inner">
                    <div style="font-size: 11px; font-weight: 800; color: #16a34a; text-transform: uppercase; letter-spacing: 0.5px;">SAVING</div>
                    <div style="font-size: 28px; font-weight: 900; color: #0f172a; line-height: 1;">{pct_saved:.1f}%</div>
                    <div style="font-size: 11px; font-weight: 700; color: #64748b;">-{energy_saved:.2f} kWh</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 22px;'></div>", unsafe_allow_html=True)

# --- 7. MAIN BODY: GRAPHS DIRECTLY UNDER THEIR SUMMARIES ---
grid_left, grid_right = st.columns([1.0, 1.0])

# --- LEFT COLUMN: OCCUPANCY & TEMPERATURE GRAPHS ---
with grid_left:
    # Graph 1: Occupancy Tracking & 15 Minute Ahead Forecast
    st.markdown("<div class='card-top-title' style='margin-bottom: 12px;'>👥 Occupancy Tracking & 15 Minute Ahead Forecast</div>", unsafe_allow_html=True)
    
    day_window_data = df_day[(df_day.index >= t_start) & (df_day.index <= t_end)]
    max_occ_day = max(day_window_data['occupancy_now'].max(), day_window_data['occupancy_forecast_15min'].max())
    y_upper = max(8, int(max_occ_day) + 2) if pd.notna(max_occ_day) else 8

    fig_occ = go.Figure()
    fig_occ.add_trace(go.Scatter(
        x=df_live.index, y=df_live['occupancy_forecast_15min'],
        mode='lines', name='15 Minute Ahead Forecast',
        line=dict(color='#f97316', width=4, dash='dash')
    ))
    fig_occ.add_trace(go.Scatter(
        x=df_live.index, y=df_live['occupancy_now'],
        mode='lines', name='Actual Occupancy',
        line=dict(color='#0284c7', width=4.5)
    ))
    fig_occ.add_vline(x=datetime.combine(selected_date, active_time), line_width=2.5, line_color="#ef4444")

    fig_occ.update_layout(
        height=380,
        margin=dict(l=25, r=25, t=10, b=25),
        xaxis_title="", yaxis_title="People",
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(color="#334155", size=15),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=14), range=[t_start, t_end]),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=14), range=[0, y_upper], dtick=1),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=14))
    )
    st.plotly_chart(fig_occ, use_container_width=True)
    
    st.markdown("<div style='margin-bottom: 18px;'></div>", unsafe_allow_html=True)

    # Graph 2: Temperature Trend Graph
    st.markdown("<div class='card-top-title' style='margin-bottom: 12px;'>🌡️ Temperature Trend (Clear Movement Scale)</div>", unsafe_allow_html=True)
    fig_temp = go.Figure()
    
    fig_temp.add_hrect(
        y0=22.8, y1=25.8, line_width=0, fillcolor="#22c55e", opacity=0.18,
        annotation_text="Comfort Range (22.8 - 25.8°C)", annotation_position="top right", annotation_font_size=13
    )
    fig_temp.add_hline(
        y=24.0, line_dash="dash", line_color="#10b981", line_width=2.5, 
        annotation_text="Setpoint (24°C)", annotation_position="top left", annotation_font_size=13
    )
    fig_temp.add_trace(go.Scatter(
        x=df_live.index, y=df_live['predictive_room_temperature_C'],
        mode='lines', name='Zone Temperature',
        line=dict(color='#0284c7', width=4)
    ))
    fig_temp.add_trace(go.Scatter(
        x=df_live.index, y=df_live['outdoor_temperature_C'],
        mode='lines', name='Outdoor Temp (Ref)',
        line=dict(color='#f97316', width=2.5, dash='dot'),
        yaxis='y2'
    ))
    fig_temp.add_vline(x=datetime.combine(selected_date, active_time), line_width=2.5, line_color="#ef4444")

    if not day_window_data.empty:
        t_min = float(day_window_data['predictive_room_temperature_C'].min())
        t_max = float(day_window_data['predictive_room_temperature_C'].max())
        y_temp_min = round(min(23.8, t_min - 0.2), 1)
        y_temp_max = round(max(26.2, t_max + 0.2), 1)
    else:
        y_temp_min, y_temp_max = 23.8, 26.5

    fig_temp.update_layout(
        height=380,
        margin=dict(l=25, r=25, t=10, b=25),
        xaxis_title="", 
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(color="#334155", size=15),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=14), range=[t_start, t_end]),
        yaxis=dict(
            title="Zone Temperature (°C)",
            showgrid=True, 
            gridcolor="#f1f5f9", 
            tickfont=dict(size=14), 
            range=[y_temp_min, y_temp_max],
            dtick=0.5
        ),
        yaxis2=dict(
            title="Outdoor (°C)",
            overlaying='y',
            side='right',
            showgrid=False,
            tickfont=dict(size=12, color='#f97316'),
            range=[15.0, 36.0]
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=14))
    )
    st.plotly_chart(fig_temp, use_container_width=True)

# --- RIGHT COLUMN: ENERGY GRAPH & DEVICE STATUS ---
with grid_right:
    # Graph 3: Cumulative Energy Consumption Graph (Directly under Energy Summary Card)
    st.markdown("<div class='card-top-title' style='margin-bottom: 12px;'>📊 Cumulative Energy Consumption (kWh, Since 08:00)</div>", unsafe_allow_html=True)
    fig_energy = go.Figure()
    
    df_live_plot = df_live[df_live.index >= t_start]
    fig_energy.add_trace(go.Scatter(
        x=df_live_plot.index, y=df_live_plot['sched_energy_cum_day'],
        mode='lines', name='Scheduled Baseline (Cum. kWh)',
        line=dict(color='#ea580c', width=3.5, dash='dash')
    ))
    fig_energy.add_trace(go.Scatter(
        x=df_live_plot.index, y=df_live_plot['pred_energy_cum_day'],
        mode='lines', name='Predictive HVAC (Cum. kWh)',
        line=dict(color='#0284c7', width=4),
        fill='tozeroy', fillcolor='rgba(2, 132, 199, 0.12)'
    ))
    fig_energy.add_vline(x=datetime.combine(selected_date, active_time), line_width=2.5, line_color="#ef4444")
    
    max_cum_e = day_window_data['sched_energy_cum_day'].max() if not day_window_data.empty else 5.0
    y_energy_upper = max(2.0, round(float(max_cum_e) + 0.5, 1))

    fig_energy.update_layout(
        height=380,
        margin=dict(l=25, r=25, t=10, b=25),
        xaxis_title="", yaxis_title="Cumulative Energy (kWh)",
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(color="#334155", size=15),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=14), range=[t_start, t_end]),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=14), range=[0.0, y_energy_upper], zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=14))
    )
    st.plotly_chart(fig_energy, use_container_width=True)
    
    st.markdown("<div style='margin-bottom: 18px;'></div>", unsafe_allow_html=True)

    # Device Status Table (Directly underneath Energy)
    st.markdown("<div class='card-top-title' style='margin-bottom: 12px;'>⚙️ HVAC Device & Sensor Infrastructure Status</div>", unsafe_allow_html=True)
    
    hvac_status_str = "<span class='badge-on'><span class='circle-dot circle-green'></span> ON</span>" if hvac_on else "<span class='badge-off'><span class='circle-dot circle-gray'></span> OFF</span>"
    cooling_str = "<span class='badge-on'><span class='circle-dot circle-green'></span> ACTIVE</span>" if is_cooling else "<span class='badge-off'><span class='circle-dot circle-gray'></span> IDLE</span>"
    damper_str = "<span class='badge-on'><span class='circle-dot circle-green'></span> OPEN</span>" if cur_occ > 0 else "<span class='badge-off'><span class='circle-dot circle-gray'></span> MINIMUM</span>"
    occ_status_val = df_live['occupancystatus'].iloc[-1] if 'occupancystatus' in df_live.columns and pd.notna(df_live['occupancystatus'].iloc[-1]) else "ONLINE"
    
    table_html = f"""
    <div style="background-color: #ffffff; border-radius: 16px; border: 1.5px solid #cbd5e1; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.03); height: 380px; display: flex; flex-direction: column; justify-content: center;">
        <table class="status-table">
            <thead>
                <tr>
                    <th>Device Component</th>
                    <th>Operating State</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>HVAC Compressor Unit</td><td>{hvac_status_str}</td></tr>
                <tr><td>Variable Air Supply Fan</td><td>{hvac_status_str}</td></tr>
                <tr><td>Outdoor Air Damper</td><td>{damper_str}</td></tr>
                <tr><td>Cooling Loop Valve</td><td>{cooling_str}</td></tr>
                <tr><td>Occupancy IoT Sensor</td><td><span class='badge-on'><span class='circle-dot circle-green'></span> {occ_status_val}</span></td></tr>
                <tr><td>Indoor Room Temp. Sensor</td><td><span class='badge-on'><span class='circle-dot circle-green'></span> ONLINE</span></td></tr>
                <tr><td>Weather / Outdoor Sensor</td><td><span class='badge-on'><span class='circle-dot circle-green'></span> ONLINE</span></td></tr>
            </tbody>
        </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

# Bottom spacing to keep the auto-scroll loop smooth on all TV resolutions
st.markdown("<div style='height: 120px;'></div>", unsafe_allow_html=True)
