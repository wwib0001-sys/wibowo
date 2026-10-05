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
    
    /* Enlarged Square Metric Cards */
    .metric-card-box {
        background-color: #ffffff;
        border: 1.5px solid #cbd5e1;
        border-radius: 18px;
        padding: 22px 24px;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.05);
        height: 200px;
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
        font-size: 54px;
        font-weight: 900;
        color: #0f172a;
        line-height: 1.0;
        margin: 6px 0 2px 0;
    }
    
    .metric-label-muted {
        font-size: 15px;
        font-weight: 800;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .metric-sub-unit {
        font-size: 15px;
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
        height: 200px;
        box-shadow: 0 6px 24px rgba(22, 163, 74, 0.4);
        animation: comfortPulse 3s infinite ease-in-out;
        box-sizing: border-box;
    }
    @keyframes comfortPulse {
        0%, 100% { box-shadow: 0 0 16px rgba(22, 163, 74, 0.3); }
        50% { box-shadow: 0 0 30px rgba(22, 163, 74, 0.65); }
    }
    
    /* Device Status Table */
    .status-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 19px;
    }
    .status-table th {
        background-color: #e2e8f0;
        color: #334155;
        font-weight: 800;
        padding: 14px 22px;
        text-align: left;
    }
    .status-table td {
        padding: 13px 22px;
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

# Filter dataset to selected date and time
df_day = df_full[df_full.index.date == selected_date].copy()
df_live = df_day[df_day.index.time <= active_time]
if df_live.empty:
    df_live = df_day.iloc[:1]

cur_occ = int(df_live['occupancy_now'].iloc[-1])
pred_occ = int(df_live['occupancy_forecast_15min'].iloc[-1])
zone_temp = df_live['predictive_room_temperature_C'].iloc[-1]
outdoor_temp = df_live['outdoor_temperature_C'].iloc[-1]
setpoint_temp = 24.0

pred_energy_total = df_live['predictive_energy_cumulative_kWh'].iloc[-1]
sched_energy_total = df_live['scheduled_energy_cumulative_kWh'].iloc[-1]
energy_saved = max(0.0, sched_energy_total - pred_energy_total)
pct_saved = (energy_saved / sched_energy_total * 100) if sched_energy_total > 0 else 0.0

cur_power = df_live['predictive_hvac_power_kW'].iloc[-1]
is_cooling = cur_power > 0.05
hvac_on = cur_power > 0.0

# --- 6. TOP 4 KPI CARDS ---
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns([1.1, 1.3, 1.1, 1.5])

# Box 1: Occupancy
with kpi_col1:
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
                <div class="metric-label-muted">Predicted <span style="font-size: 13px;">+15m</span></div>
                <div class="metric-main-val">{pred_occ} <span style="font-size: 32px; color: {arrow_color};">{arrow}</span></div>
                <div class="metric-sub-unit">people</div>
            </div>
        </div>
        <div style="height: 4px;"></div>
    </div>
    """, unsafe_allow_html=True)

# Box 2: Temperature
with kpi_col2:
    st.markdown(f"""
    <div class="metric-card-box">
        <div class="card-top-title">🌡️ Temperature (°C)</div>
        <div style="display: flex; justify-content: space-around; align-items: center; text-align: center; margin: auto 0;">
            <div>
                <div class="metric-label-muted">Zone Temp.</div>
                <div class="metric-main-val" style="font-size: 44px;">{zone_temp:.1f}</div>
                <div class="metric-sub-unit">°C</div>
            </div>
            <div>
                <div class="metric-label-muted">Setpoint</div>
                <div class="metric-main-val" style="font-size: 44px;">{setpoint_temp:.1f}</div>
                <div class="metric-sub-unit">°C</div>
            </div>
            <div>
                <div class="metric-label-muted">Outdoor</div>
                <div class="metric-main-val" style="font-size: 44px;">{outdoor_temp:.1f}</div>
                <div class="metric-sub-unit">°C</div>
            </div>
        </div>
        <div style="height: 4px;"></div>
    </div>
    """, unsafe_allow_html=True)

# Box 3: Thermal Comfort
with kpi_col3:
    is_comfort = (22.8 <= zone_temp <= 25.8)
    comfort_label = "COMFORTABLE" if is_comfort else "DEVIATION"
    comfort_icon = "😊" if is_comfort else "⚠️"
    bg_comfort = "linear-gradient(135deg, #16a34a 0%, #15803d 100%)" if is_comfort else "linear-gradient(135deg, #d97706 0%, #b45309 100%)"
    st.markdown(f"""
    <div class="comfort-card-box" style="background: {bg_comfort};">
        <span style="font-size: 54px;">{comfort_icon}</span>
        <div>
            <div style="font-size: 15px; font-weight: 800; color: rgba(255,255,255,0.85); text-transform: uppercase;">Thermal Comfort</div>
            <div style="font-size: 34px; font-weight: 900; letter-spacing: 0.5px;">{comfort_label}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Box 4: Energy Usage (Today)
with kpi_col4:
    st.markdown(f"""
    <div class="metric-card-box">
        <div class="card-top-title">⚡ Energy Usage (Today)</div>
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin: auto 0;">
            <div>
                <div class="metric-label-muted">Predictive HVAC</div>
                <div class="metric-main-val" style="font-size: 38px; color: #2563eb;">{pred_energy_total:.2f} <span style="font-size: 16px; font-weight: 700; color: #64748b;">kWh</span></div>
            </div>
            <div style="text-align: right;">
                <div class="metric-label-muted">Scheduled Baseline</div>
                <div class="metric-main-val" style="font-size: 38px; color: #d97706;">{sched_energy_total:.2f} <span style="font-size: 16px; font-weight: 700; color: #64748b;">kWh</span></div>
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 8px; color: #15803d; font-size: 18px; font-weight: 900; border-top: 1.5px solid #f1f5f9; padding-top: 8px;">
            <span>🍃</span>
            <span>{energy_saved:.2f} kWh ({pct_saved:.1f}%) Energy Saved</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 22px;'></div>", unsafe_allow_html=True)

# Locked timeframe: 08:00 AM to 06:00 PM (18:00)
t_start = datetime.combine(selected_date, time(8, 0))
t_end = datetime.combine(selected_date, time(18, 0))

# --- 7. MID-ROW: ENERGY CONSUMPTION & TEMPERATURE TREND ---
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.markdown("<div class='card-top-title' style='margin-bottom: 12px;'>📊 Energy Consumption</div>", unsafe_allow_html=True)
    fig_energy = go.Figure()
    
    fig_energy.add_trace(go.Scatter(
        x=df_live.index, y=df_live['scheduled_hvac_power_kW'],
        mode='lines', name='Scheduled HVAC (Baseline)',
        line=dict(color='#ea580c', width=3.5, dash='dash')
    ))
    fig_energy.add_trace(go.Scatter(
        x=df_live.index, y=df_live['predictive_hvac_power_kW'],
        mode='lines', name='Predictive HVAC (Actual)',
        line=dict(color='#0284c7', width=4),
        fill='tozeroy', fillcolor='rgba(2, 132, 199, 0.12)'
    ))
    
    fig_energy.add_vline(x=datetime.combine(selected_date, active_time), line_width=2.5, line_color="#ef4444")
    
    fig_energy.update_layout(
        height=400,
        margin=dict(l=25, r=25, t=10, b=25),
        xaxis_title="", yaxis_title="Power (kW)",
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(color="#334155", size=15),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=14), range=[t_start, t_end]),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=14), zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=14))
    )
    st.plotly_chart(fig_energy, use_container_width=True)

with chart_col2:
    st.markdown("<div class='card-top-title' style='margin-bottom: 12px;'>🌡️ Temperature Trend</div>", unsafe_allow_html=True)
    fig_temp = go.Figure()
    
    # Comfort Band Shading (22.8 - 25.8°C)
    fig_temp.add_hrect(
        y0=22.8, y1=25.8, line_width=0, fillcolor="#22c55e", opacity=0.18,
        annotation_text="Comfort Range (22.8 - 25.8°C)", annotation_position="top right", annotation_font_size=13
    )
    
    # Setpoint line at 24.0°C
    fig_temp.add_hline(
        y=24.0, line_dash="dash", line_color="#10b981", line_width=2.5, 
        annotation_text="Setpoint (24°C)", annotation_position="top left", annotation_font_size=13
    )
    
    # Zone Temperature (Primary focus line, high visibility)
    fig_temp.add_trace(go.Scatter(
        x=df_live.index, y=df_live['predictive_room_temperature_C'],
        mode='lines', name='Zone Temperature',
        line=dict(color='#0284c7', width=4)
    ))
    
    # Outdoor Temperature placed on secondary y-axis to prevent compressing zone temperature
    fig_temp.add_trace(go.Scatter(
        x=df_live.index, y=df_live['outdoor_temperature_C'],
        mode='lines', name='Outdoor Temp (Ref)',
        line=dict(color='#f97316', width=2.5, dash='dot'),
        yaxis='y2'
    ))
    
    fig_temp.add_vline(x=datetime.combine(selected_date, active_time), line_width=2.5, line_color="#ef4444")

    # Ultra-compact 3°C scale: 23.5°C to 26.5°C with 0.5°C steps
    fig_temp.update_layout(
        height=400,
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
            range=[23.5, 26.5],  # Tight 3-degree view
            dtick=0.5            # 0.5°C increments
        ),
        yaxis2=dict(
            title="Outdoor (°C)",
            overlaying='y',
            side='right',
            showgrid=False,
            tickfont=dict(size=12, color='#f97316'),
            range=[15.0, 35.0]
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=14))
    )
    st.plotly_chart(fig_temp, use_container_width=True)

st.markdown("<div style='margin-bottom: 22px;'></div>", unsafe_allow_html=True)

# --- 8. BOTTOM ROW: DEVICE STATUS & OCCUPANCY (SCALE 0-8) ---
bot_col1, bot_col2 = st.columns([1.1, 1.9])

with bot_col1:
    st.markdown("<div class='card-top-title' style='margin-bottom: 12px;'>⚙️ HVAC Device Status</div>", unsafe_allow_html=True)
    
    hvac_status_str = "<span class='badge-on'><span class='circle-dot circle-green'></span> ON</span>" if hvac_on else "<span class='badge-off'><span class='circle-dot circle-gray'></span> OFF</span>"
    cooling_str = "<span class='badge-on'><span class='circle-dot circle-green'></span> ACTIVE</span>" if is_cooling else "<span class='badge-off'><span class='circle-dot circle-gray'></span> IDLE</span>"
    damper_str = "<span class='badge-on'><span class='circle-dot circle-green'></span> OPEN</span>" if cur_occ > 0 else "<span class='badge-off'><span class='circle-dot circle-gray'></span> MINIMUM</span>"
    
    occ_status_val = df_live['occupancystatus'].iloc[-1] if 'occupancystatus' in df_live.columns and pd.notna(df_live['occupancystatus'].iloc[-1]) else "ONLINE"
    
    table_html = f"""
    <div style="background-color: #ffffff; border-radius: 16px; border: 1.5px solid #cbd5e1; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.03);">
        <table class="status-table">
            <thead>
                <tr>
                    <th>Device</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>HVAC Unit</td><td>{hvac_status_str}</td></tr>
                <tr><td>Supply Fan</td><td>{hvac_status_str}</td></tr>
                <tr><td>Damper</td><td>{damper_str}</td></tr>
                <tr><td>Cooling</td><td>{cooling_str}</td></tr>
                <tr><td>Occupancy Sensor</td><td><span class='badge-on'><span class='circle-dot circle-green'></span> {occ_status_val}</span></td></tr>
                <tr><td>Temperature Sensor</td><td><span class='badge-on'><span class='circle-dot circle-green'></span> ONLINE</span></td></tr>
                <tr><td>Outdoor Temp. Sensor</td><td><span class='badge-on'><span class='circle-dot circle-green'></span> ONLINE</span></td></tr>
            </tbody>
        </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

with bot_col2:
    st.markdown("<div class='card-top-title' style='margin-bottom: 12px;'>👥 Occupancy Tracking & Prediction</div>", unsafe_allow_html=True)
    fig_occ = go.Figure()
    
    day_window_data = df_day[(df_day.index >= t_start) & (df_day.index <= t_end)]
    max_occ_day = max(day_window_data['occupancy_now'].max(), day_window_data['occupancy_forecast_15min'].max())
    y_upper = max(8, int(max_occ_day) + 2) if pd.notna(max_occ_day) else 8

    # Predicted Occupancy (+15 min) (Orange dashed)
    fig_occ.add_trace(go.Scatter(
        x=df_live.index, y=df_live['occupancy_forecast_15min'],
        mode='lines', name='Predicted Occupancy (+15 min)',
        line=dict(color='#f97316', width=4, dash='dash')
    ))
    
    # Actual Occupancy (Solid Blue)
    fig_occ.add_trace(go.Scatter(
        x=df_live.index, y=df_live['occupancy_now'],
        mode='lines', name='Actual Occupancy',
        line=dict(color='#0284c7', width=4.5)
    ))
    
    fig_occ.add_vline(x=datetime.combine(selected_date, active_time), line_width=2.5, line_color="#ef4444")

    fig_occ.update_layout(
        height=400,
        margin=dict(l=25, r=25, t=10, b=25),
        xaxis_title="", yaxis_title="People",
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(color="#334155", size=15),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=14), range=[t_start, t_end]),
        yaxis=dict(
            showgrid=True, 
            gridcolor="#f1f5f9", 
            tickfont=dict(size=14), 
            range=[0, y_upper],
            dtick=1
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=14))
    )
    st.plotly_chart(fig_occ, use_container_width=True)

# Bottom spacing to keep the auto-scroll loop smooth on all TV resolutions
st.markdown("<div style='height: 120px;'></div>", unsafe_allow_html=True)
