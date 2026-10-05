import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, date, time, timezone, timedelta

# Auto-refresh helper (optional)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30000, key="data_refresh")
except Exception:
    pass

# --- 1. PAGE CONFIGURATION & BIG SCREEN CSS ---
st.set_page_config(
    page_title="Innovation Lab – HVAC Monitoring",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS scaled specifically for 1080p / 4K TV screens
st.markdown("""
<style>
    .stApp {
        background-color: #f8fafc !important;
        color: #0f172a !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 98%;
    }
    
    /* Search Toolbar */
    .filter-toolbar {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 14px;
        padding: 10px 18px;
        margin-bottom: 16px;
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.04);
    }
    
    /* Large Screen Card Containers */
    .dashboard-card {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 16px;
        padding: 18px 24px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    
    .card-header-title {
        font-size: 18px;
        font-weight: 700;
        color: #1e293b;
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
    }
    
    /* Green Comfort Hero Badge */
    .comfort-card {
        background-color: #15803d;
        color: #ffffff;
        border-radius: 16px;
        padding: 24px 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 18px;
        height: 100%;
        box-shadow: 0 6px 14px rgba(21, 128, 61, 0.25);
    }
    .comfort-text {
        font-size: 32px;
        font-weight: 800;
        letter-spacing: 1px;
    }
    
    /* TV Sized Status Table */
    .status-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 17px;
    }
    .status-table th {
        background-color: #e2e8f0;
        color: #334155;
        font-weight: 800;
        padding: 12px 18px;
        text-align: left;
    }
    .status-table td {
        padding: 11px 18px;
        border-bottom: 1px solid #f1f5f9;
        color: #0f172a;
        font-weight: 500;
    }
    .badge-on {
        color: #16a34a;
        font-weight: 800;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    .badge-off {
        color: #94a3b8;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    .circle-dot {
        height: 13px;
        width: 13px;
        border-radius: 50%;
        display: inline-block;
    }
    .circle-green { background-color: #16a34a; box-shadow: 0 0 6px rgba(22, 163, 74, 0.6); }
    .circle-gray { background-color: #94a3b8; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA LOADING ---
@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv('hvac_comparison.csv')
    except Exception as e:
        st.error(f"Could not read dataset: {e}")
        st.stop()

    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')

    df = df.sort_index()
    df['sched_energy_step'] = df['scheduled_energy_cumulative_kWh'].diff().fillna(0).clip(lower=0)
    df['pred_energy_step'] = df['predictive_energy_cumulative_kWh'].diff().fillna(0).clip(lower=0)
    return df

df_full = load_data()
available_dates = df_full.index.normalize().unique().date

# Default to Sep 29 or latest date
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

# --- 3. TOP HEADER BAR ---
col_head_left, col_head_mid, col_head_right = st.columns([2.5, 1.3, 1.0])

with col_head_left:
    st.markdown("""
        <div style="line-height: 1.2;">
            <div style="font-size: 34px; font-weight: 800; color: #0f172a;">Innovation Lab – HVAC Monitoring</div>
            <div style="font-size: 18px; font-weight: 600; color: #64748b; margin-top: 3px;">Occupancy Prediction Based Control</div>
        </div>
    """, unsafe_allow_html=True)

with col_head_mid:
    st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 24px; margin-top: 6px;">
            <div style="text-align: right; line-height: 1.2;">
                <div style="font-size: 14px; color: #64748b; font-weight: 700;">📅 {default_date.strftime('%a, %d %b %Y')}</div>
                <div style="font-size: 24px; font-weight: 800; color: #0f172a;">{real_live_time.strftime('%H:%M:%S')}</div>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="height: 16px; width: 16px; background-color: #22c55e; border-radius: 50%; display: inline-block; box-shadow: 0 0 10px rgba(34, 197, 94, 0.6);"></span>
                <div style="line-height: 1.1;">
                    <div style="font-size: 16px; font-weight: 800; color: #0f172a;">System Online</div>
                    <div style="font-size: 12px; color: #64748b; font-weight: 500;">All sensors connected</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_head_right:
    st.selectbox("Select Zone:", ["Zone: Innovation Lab", "Zone: Meeting Room", "Zone: Open Workspace"], label_visibility="collapsed")

# --- 4. SEARCHABLE DATE & TIME CONTROL TOOLBAR ---
st.markdown("<div class='filter-toolbar'>", unsafe_allow_html=True)
c_mode, c_date, c_time = st.columns([1.1, 1.4, 2.0])

with c_mode:
    is_live_mode = st.toggle("🔴 Real-Time Clock Sync", value=True, help="Toggle OFF to search and jump to any historical date/time.")

if is_live_mode:
    selected_date = default_date
    active_time = real_live_time
    with c_date:
        st.markdown(f"<div style='font-size: 15px; font-weight: 600; padding-top: 6px; color: #334155;'>📅 Active Date: <b>{selected_date.strftime('%Y-%m-%d')}</b></div>", unsafe_allow_html=True)
    with c_time:
        st.markdown(f"<div style='font-size: 15px; font-weight: 600; padding-top: 6px; color: #2563eb;'>⏱️ Real-Time Tracking: <b>{active_time.strftime('%H:%M:%S')} (AEST)</b></div>", unsafe_allow_html=True)
else:
    with c_date:
        # Searchable Date Dropdown
        date_options = [d.strftime('%Y-%m-%d') for d in available_dates]
        default_idx = date_options.index(default_date.strftime('%Y-%m-%d')) if default_date.strftime('%Y-%m-%d') in date_options else len(date_options)-1
        sel_date_str = st.selectbox("🔍 Search Date:", options=date_options, index=default_idx)
        selected_date = datetime.strptime(sel_date_str, '%Y-%m-%d').date()

    df_day_candidates = df_full[df_full.index.date == selected_date]
    day_times = [t.strftime('%H:%M') for t in df_day_candidates.index.time]

    with c_time:
        # Searchable Time Dropdown
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

# Current Telemetry Values
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

# --- 5. TOP 4 KPI CARDS (TV SCALED) ---
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns([1.1, 1.3, 1.2, 1.5])

# Card 1: Occupancy
with kpi_col1:
    arrow = "↑" if pred_occ >= cur_occ else "↓"
    arrow_color = "#dc2626" if pred_occ >= cur_occ else "#16a34a"
    st.markdown(f"""
    <div class="dashboard-card">
        <div class="card-header-title">👥 Occupancy</div>
        <div style="display: flex; justify-content: space-around; align-items: baseline; text-align: center; margin-top: 4px;">
            <div>
                <div style="font-size: 14px; color: #64748b; font-weight: 700;">Current</div>
                <div style="font-size: 46px; font-weight: 900; color: #0f172a; line-height: 1;">{cur_occ}</div>
                <div style="font-size: 14px; color: #64748b; font-weight: 600;">people</div>
            </div>
            <div style="border-left: 2px solid #e2e8f0; height: 60px;"></div>
            <div>
                <div style="font-size: 14px; color: #64748b; font-weight: 700;">Predicted<br><span style="font-size: 11px;">+15 min</span></div>
                <div style="font-size: 46px; font-weight: 900; color: #0f172a; line-height: 1;">{pred_occ} <span style="font-size: 28px; color: {arrow_color};">{arrow}</span></div>
                <div style="font-size: 14px; color: #64748b; font-weight: 600;">people</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Card 2: Temperature
with kpi_col2:
    st.markdown(f"""
    <div class="dashboard-card">
        <div class="card-header-title">🌡️ Temperature (°C)</div>
        <div style="display: flex; justify-content: space-around; align-items: baseline; text-align: center; margin-top: 4px;">
            <div>
                <div style="font-size: 14px; color: #64748b; font-weight: 700;">Zone Temp.</div>
                <div style="font-size: 40px; font-weight: 900; color: #0f172a; line-height: 1;">{zone_temp:.1f}</div>
                <div style="font-size: 14px; color: #64748b; font-weight: 600;">°C</div>
            </div>
            <div>
                <div style="font-size: 14px; color: #64748b; font-weight: 700;">Setpoint</div>
                <div style="font-size: 40px; font-weight: 900; color: #0f172a; line-height: 1;">{setpoint_temp:.1f}</div>
                <div style="font-size: 14px; color: #64748b; font-weight: 600;">°C</div>
            </div>
            <div>
                <div style="font-size: 14px; color: #64748b; font-weight: 700;">Outdoor</div>
                <div style="font-size: 40px; font-weight: 900; color: #0f172a; line-height: 1;">{outdoor_temp:.1f}</div>
                <div style="font-size: 14px; color: #64748b; font-weight: 600;">°C</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Card 3: Thermal Comfort
with kpi_col3:
    is_comfort = (22.8 <= zone_temp <= 25.8)
    comfort_label = "COMFORTABLE" if is_comfort else "DEVIATION"
    comfort_icon = "😊" if is_comfort else "⚠️"
    bg_comfort = "#15803d" if is_comfort else "#b45309"
    st.markdown(f"""
    <div class="dashboard-card" style="padding: 12px;">
        <div class="card-header-title" style="margin-bottom: 8px;">🍃 Thermal Comfort</div>
        <div class="comfort-card" style="background-color: {bg_comfort};">
            <span style="font-size: 48px;">{comfort_icon}</span>
            <span class="comfort-text">{comfort_label}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Card 4: Energy Usage (Today)
with kpi_col4:
    st.markdown(f"""
    <div class="dashboard-card">
        <div class="card-header-title">⚡ Energy Usage (Today)</div>
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 2px;">
            <div>
                <div style="font-size: 13px; color: #64748b; font-weight: 700;">Predictive HVAC</div>
                <div style="font-size: 28px; font-weight: 900; color: #2563eb;">{pred_energy_total:.2f} kWh</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 13px; color: #64748b; font-weight: 700;">Scheduled Baseline</div>
                <div style="font-size: 28px; font-weight: 900; color: #d97706;">{sched_energy_total:.2f} kWh</div>
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 10px; color: #15803d; font-size: 17px; font-weight: 800; border-top: 1px solid #f1f5f9; padding-top: 8px; margin-top: 4px;">
            <span style="font-size: 20px;">🍃</span>
            <span>{energy_saved:.2f} kWh ({pct_saved:.1f}%) Energy Saving</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 18px;'></div>", unsafe_allow_html=True)

# --- 6. MID-ROW: ENERGY CONSUMPTION & TEMPERATURE TREND (LARGER PLOTS) ---
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.markdown("<div class='card-header-title'>📊 Energy Consumption</div>", unsafe_allow_html=True)
    fig_energy = go.Figure()
    
    fig_energy.add_trace(go.Scatter(
        x=df_live.index, y=df_live['scheduled_hvac_power_kW'],
        mode='lines', name='Scheduled HVAC (Baseline)',
        line=dict(color='#ea580c', width=3, dash='dash')
    ))
    fig_energy.add_trace(go.Scatter(
        x=df_live.index, y=df_live['predictive_hvac_power_kW'],
        mode='lines', name='Predictive HVAC (Actual)',
        line=dict(color='#0284c7', width=3.5),
        fill='tozeroy', fillcolor='rgba(2, 132, 199, 0.12)'
    ))
    
    fig_energy.update_layout(
        height=380,
        margin=dict(l=25, r=25, t=10, b=25),
        xaxis_title="", yaxis_title="Power (kW)",
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(color="#334155", size=14),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=13), range=[datetime.combine(selected_date, time(8, 0)), datetime.combine(selected_date, time(22, 0))]),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=13), zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=13))
    )
    st.plotly_chart(fig_energy, use_container_width=True)

with chart_col2:
    st.markdown("<div class='card-header-title'>🌡️ Temperature Trend</div>", unsafe_allow_html=True)
    fig_temp = go.Figure()
    
    fig_temp.add_hrect(
        y0=22.8, y1=25.8, line_width=0, fillcolor="#22c55e", opacity=0.15,
        annotation_text="Comfort Range (22.8 - 25.8°C)", annotation_position="top right", annotation_font_size=12
    )
    fig_temp.add_trace(go.Scatter(
        x=df_live.index, y=df_live['outdoor_temperature_C'],
        mode='lines', name='Outdoor Temperature',
        line=dict(color='#f97316', width=3)
    ))
    fig_temp.add_hline(y=24.0, line_dash="dash", line_color="#10b981", line_width=2, annotation_text="Setpoint (24°C)", annotation_position="top left", annotation_font_size=12)
    fig_temp.add_trace(go.Scatter(
        x=df_live.index, y=df_live['predictive_room_temperature_C'],
        mode='lines', name='Zone Temperature',
        line=dict(color='#0284c7', width=3.5)
    ))

    fig_temp.update_layout(
        height=380,
        margin=dict(l=25, r=25, t=10, b=25),
        xaxis_title="", yaxis_title="Temperature (°C)",
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(color="#334155", size=14),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=13), range=[datetime.combine(selected_date, time(8, 0)), datetime.combine(selected_date, time(22, 0))]),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=13), range=[16, 32]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=13))
    )
    st.plotly_chart(fig_temp, use_container_width=True)

st.markdown("<div style='margin-bottom: 18px;'></div>", unsafe_allow_html=True)

# --- 7. BOTTOM ROW: DEVICE STATUS & OCCUPANCY/MODE ---
bot_col1, bot_col2 = st.columns([1.1, 1.9])

with bot_col1:
    st.markdown("<div class='card-header-title'>⚙️ HVAC Device Status</div>", unsafe_allow_html=True)
    
    hvac_status_str = "<span class='badge-on'><span class='circle-dot circle-green'></span> ON</span>" if hvac_on else "<span class='badge-off'><span class='circle-dot circle-gray'></span> OFF</span>"
    cooling_str = "<span class='badge-on'><span class='circle-dot circle-green'></span> ACTIVE</span>" if is_cooling else "<span class='badge-off'><span class='circle-dot circle-gray'></span> IDLE</span>"
    damper_str = "<span class='badge-on'><span class='circle-dot circle-green'></span> OPEN</span>" if cur_occ > 0 else "<span class='badge-off'><span class='circle-dot circle-gray'></span> MINIMUM</span>"
    
    table_html = f"""
    <div style="background-color: #ffffff; border-radius: 14px; border: 1px solid #cbd5e1; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
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
                <tr><td>Occupancy Sensor</td><td><span class='badge-on'><span class='circle-dot circle-green'></span> ONLINE</span></td></tr>
                <tr><td>Temperature Sensor</td><td><span class='badge-on'><span class='circle-dot circle-green'></span> ONLINE</span></td></tr>
                <tr><td>Outdoor Temp. Sensor</td><td><span class='badge-on'><span class='circle-dot circle-green'></span> ONLINE</span></td></tr>
            </tbody>
        </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

with bot_col2:
    st.markdown("<div class='card-header-title'>👥 Occupancy & HVAC Mode</div>", unsafe_allow_html=True)
    fig_occ = go.Figure()
    
    fig_occ.add_trace(go.Bar(
        x=df_live.index, y=(df_live['predictive_hvac_power_kW'] > 0).astype(int) * 45,
        name='HVAC Mode (Active)',
        marker_color='rgba(191, 219, 254, 0.65)',
        width=1000 * 60 * 4
    ))
    fig_occ.add_trace(go.Scatter(
        x=df_live.index, y=df_live['occupancy_forecast_15min'],
        mode='lines', name='Predicted Occupancy (+15 min)',
        line=dict(color='#f97316', width=3, dash='dash')
    ))
    fig_occ.add_trace(go.Scatter(
        x=df_live.index, y=df_live['occupancy_now'],
        mode='lines', name='Actual Occupancy',
        line=dict(color='#0284c7', width=3.5)
    ))

    fig_occ.update_layout(
        height=360,
        margin=dict(l=25, r=25, t=10, b=25),
        xaxis_title="", yaxis_title="People",
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(color="#334155", size=14),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=13), range=[datetime.combine(selected_date, time(8, 0)), datetime.combine(selected_date, time(22, 0))]),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=13), range=[0, 50]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=13))
    )
    st.plotly_chart(fig_occ, use_container_width=True)
