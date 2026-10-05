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

# --- 1. PAGE CONFIGURATION & STYLING ---
st.set_page_config(
    page_title="Innovation Lab – HVAC Monitoring",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS matching the reference UI design
st.markdown("""
<style>
    /* Clean light background matching the target UI */
    .stApp {
        background-color: #f1f5f9 !important;
        color: #1e293b !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Hide default sidebar */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 98%;
    }
    
    /* White Card Containers */
    .dashboard-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 16px 20px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    
    .card-header-title {
        font-size: 15px;
        font-weight: 700;
        color: #1e293b;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
    }
    
    /* Green Comfort Hero Badge */
    .comfort-card {
        background-color: #15803d;
        color: #ffffff;
        border-radius: 14px;
        padding: 18px 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 16px;
        height: 100%;
        box-shadow: 0 4px 10px rgba(21, 128, 61, 0.25);
    }
    .comfort-text {
        font-size: 24px;
        font-weight: 800;
        letter-spacing: 0.5px;
    }
    
    /* Device Status Table Styling */
    .status-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13.5px;
    }
    .status-table th {
        background-color: #e2e8f0;
        color: #475569;
        font-weight: 700;
        padding: 8px 12px;
        text-align: left;
    }
    .status-table td {
        padding: 7px 12px;
        border-bottom: 1px solid #f1f5f9;
        color: #1e293b;
    }
    .badge-on {
        color: #16a34a;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .badge-off {
        color: #94a3b8;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .circle-dot {
        height: 9px;
        width: 9px;
        border-radius: 50%;
        display: inline-block;
    }
    .circle-green { background-color: #16a34a; }
    .circle-gray { background-color: #94a3b8; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA LOADING & PRE-PROCESSING ---
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

    # Calculate interval energy consumption
    df['sched_energy_step'] = df['scheduled_energy_cumulative_kWh'].diff().fillna(0).clip(lower=0)
    df['pred_energy_step'] = df['predictive_energy_cumulative_kWh'].diff().fillna(0).clip(lower=0)
    
    return df

df_full = load_data()
available_dates = df_full.index.normalize().unique().date

# Select date (defaulting to Sep 29 if available, or the latest available date)
sep29_dates = [d for d in available_dates if d.month == 9 and d.day == 29]
selected_date = sep29_dates[0] if sep29_dates else available_dates[-1]

df_day = df_full[df_full.index.date == selected_date].copy()

# Real-time Melbourne Clock
try:
    import pytz
    melbourne_tz = pytz.timezone('Australia/Melbourne')
    now_melbourne = datetime.now(melbourne_tz)
except Exception:
    melbourne_tz = timezone(timedelta(hours=10))
    now_melbourne = datetime.now(melbourne_tz)

live_time = now_melbourne.time()

# Filter data up to current time (with fallback for full day inspection)
df_live = df_day[df_day.index.time <= live_time]
if df_live.empty:
    df_live = df_day.iloc[:1]

# Current Telemetry Values
cur_occ = int(df_live['occupancy_now'].iloc[-1])
pred_occ = int(df_live['occupancy_forecast_15min'].iloc[-1])
zone_temp = df_live['predictive_room_temperature_C'].iloc[-1]
outdoor_temp = df_live['outdoor_temperature_C'].iloc[-1]
setpoint_temp = 24.0

# Energy Metrics
pred_energy_total = df_live['predictive_energy_cumulative_kWh'].iloc[-1]
sched_energy_total = df_live['scheduled_energy_cumulative_kWh'].iloc[-1]
energy_saved = max(0.0, sched_energy_total - pred_energy_total)
pct_saved = (energy_saved / sched_energy_total * 100) if sched_energy_total > 0 else 0.0

cur_power = df_live['predictive_hvac_power_kW'].iloc[-1]
is_cooling = cur_power > 0.05
hvac_on = cur_power > 0.0

# --- 3. TOP HEADER BAR ---
col_head_left, col_head_mid, col_head_right = st.columns([2.5, 1.2, 0.9])

with col_head_left:
    st.markdown("""
        <div style="line-height: 1.2;">
            <div style="font-size: 26px; font-weight: 800; color: #0f172a;">Innovation Lab – HVAC Monitoring</div>
            <div style="font-size: 14px; font-weight: 600; color: #64748b; margin-top: 2px;">Occupancy Prediction Based Control</div>
        </div>
    """, unsafe_allow_html=True)

with col_head_mid:
    st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 20px; margin-top: 4px;">
            <div style="text-align: right; line-height: 1.2;">
                <div style="font-size: 12px; color: #64748b; font-weight: 600;">📅 {selected_date.strftime('%a, %d %b %Y')}</div>
                <div style="font-size: 16px; font-weight: 800; color: #0f172a;">{live_time.strftime('%H:%M:%S')}</div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="height: 12px; width: 12px; background-color: #22c55e; border-radius: 50%; display: inline-block;"></span>
                <div style="line-height: 1.1;">
                    <div style="font-size: 13px; font-weight: 700; color: #0f172a;">System Online</div>
                    <div style="font-size: 10px; color: #64748b;">All sensors connected</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_head_right:
    st.selectbox("Select Zone:", ["Zone: Innovation Lab", "Zone: Meeting Room", "Zone: Open Workspace"], label_visibility="collapsed")

st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

# --- 4. TOP 4 KPI CARDS ---
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns([1.1, 1.3, 1.2, 1.4])

# Card 1: Occupancy
with kpi_col1:
    arrow = "↑" if pred_occ >= cur_occ else "↓"
    arrow_color = "#dc2626" if pred_occ >= cur_occ else "#16a34a"
    st.markdown(f"""
    <div class="dashboard-card">
        <div class="card-header-title">👥 Occupancy</div>
        <div style="display: flex; justify-content: space-around; align-items: baseline; text-align: center;">
            <div>
                <div style="font-size: 11px; color: #64748b; font-weight: 600;">Current</div>
                <div style="font-size: 32px; font-weight: 800; color: #0f172a;">{cur_occ}</div>
                <div style="font-size: 11px; color: #64748b;">people</div>
            </div>
            <div style="border-left: 1px solid #e2e8f0; height: 45px;"></div>
            <div>
                <div style="font-size: 11px; color: #64748b; font-weight: 600;">Predicted<br><span style="font-size: 9px;">+15 min</span></div>
                <div style="font-size: 32px; font-weight: 800; color: #0f172a;">{pred_occ} <span style="font-size: 20px; color: {arrow_color};">{arrow}</span></div>
                <div style="font-size: 11px; color: #64748b;">people</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Card 2: Temperature
with kpi_col2:
    st.markdown(f"""
    <div class="dashboard-card">
        <div class="card-header-title">🌡️ Temperature (°C)</div>
        <div style="display: flex; justify-content: space-around; align-items: baseline; text-align: center;">
            <div>
                <div style="font-size: 11px; color: #64748b; font-weight: 600;">Zone Temp.</div>
                <div style="font-size: 28px; font-weight: 800; color: #0f172a;">{zone_temp:.1f}</div>
                <div style="font-size: 11px; color: #64748b;">°C</div>
            </div>
            <div>
                <div style="font-size: 11px; color: #64748b; font-weight: 600;">Setpoint</div>
                <div style="font-size: 28px; font-weight: 800; color: #0f172a;">{setpoint_temp:.1f}</div>
                <div style="font-size: 11px; color: #64748b;">°C</div>
            </div>
            <div>
                <div style="font-size: 11px; color: #64748b; font-weight: 600;">Outdoor</div>
                <div style="font-size: 28px; font-weight: 800; color: #0f172a;">{outdoor_temp:.1f}</div>
                <div style="font-size: 11px; color: #64748b;">°C</div>
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
    <div class="dashboard-card" style="padding: 10px;">
        <div class="card-header-title" style="margin-bottom: 6px;">🍃 Thermal Comfort</div>
        <div class="comfort-card" style="background-color: {bg_comfort};">
            <span style="font-size: 34px;">{comfort_icon}</span>
            <span class="comfort-text">{comfort_label}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Card 4: Energy Usage (Today)
with kpi_col4:
    st.markdown(f"""
    <div class="dashboard-card">
        <div class="card-header-title">⚡ Energy Usage (Today)</div>
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;">
            <div>
                <div style="font-size: 11px; color: #64748b; font-weight: 600;">Predictive HVAC</div>
                <div style="font-size: 22px; font-weight: 800; color: #2563eb;">{pred_energy_total:.2f} kWh</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 11px; color: #64748b; font-weight: 600;">Scheduled HVAC (Baseline)</div>
                <div style="font-size: 22px; font-weight: 800; color: #d97706;">{sched_energy_total:.2f} kWh</div>
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 8px; color: #15803d; font-size: 14px; font-weight: 700; border-top: 1px solid #f1f5f9; padding-top: 6px;">
            <span>🍃</span>
            <span>{energy_saved:.2f} kWh ({pct_saved:.1f}%) Energy Saving</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

# --- 5. MID-ROW: ENERGY CONSUMPTION & TEMPERATURE TREND ---
chart_col1, chart_col2 = st.columns(2)

# Chart 1: Energy Consumption
with chart_col1:
    st.markdown("<div class='card-header-title'>📊 Energy Consumption</div>", unsafe_allow_html=True)
    fig_energy = go.Figure()
    
    # Scheduled Baseline Curve (Orange dashed)
    fig_energy.add_trace(go.Scatter(
        x=df_live.index, y=df_live['scheduled_hvac_power_kW'],
        mode='lines', name='Scheduled HVAC (Baseline)',
        line=dict(color='#ea580c', width=2, dash='dash')
    ))
    # Predictive Actual Curve (Blue filled)
    fig_energy.add_trace(go.Scatter(
        x=df_live.index, y=df_live['predictive_hvac_power_kW'],
        mode='lines', name='Predictive HVAC (Actual)',
        line=dict(color='#0284c7', width=2),
        fill='tozeroy', fillcolor='rgba(2, 132, 199, 0.1)'
    ))
    
    fig_energy.update_layout(
        margin=dict(l=20, r=20, t=10, b=20),
        xaxis_title="", yaxis_title="Power (kW)",
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(color="#475569", size=11),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", range=[datetime.combine(selected_date, time(8, 0)), datetime.combine(selected_date, time(22, 0))]),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_energy, use_container_width=True)

# Chart 2: Temperature Trend
with chart_col2:
    st.markdown("<div class='card-header-title'>🌡️ Temperature Trend</div>", unsafe_allow_html=True)
    fig_temp = go.Figure()
    
    # Comfort Band Shading
    fig_temp.add_hrect(
        y0=22.8, y1=25.8, line_width=0, fillcolor="#22c55e", opacity=0.12,
        annotation_text="Comfort Range", annotation_position="top right", annotation_font_size=10
    )
    # Outdoor Temperature (Orange)
    fig_temp.add_trace(go.Scatter(
        x=df_live.index, y=df_live['outdoor_temperature_C'],
        mode='lines', name='Outdoor Temperature',
        line=dict(color='#f97316', width=2)
    ))
    # Setpoint (Green dashed line)
    fig_temp.add_hline(y=24.0, line_dash="dash", line_color="#10b981", annotation_text="Setpoint", annotation_position="top left")
    
    # Zone Temperature (Blue)
    fig_temp.add_trace(go.Scatter(
        x=df_live.index, y=df_live['predictive_room_temperature_C'],
        mode='lines', name='Zone Temperature',
        line=dict(color='#0284c7', width=2.5)
    ))

    fig_temp.update_layout(
        margin=dict(l=20, r=20, t=10, b=20),
        xaxis_title="", yaxis_title="Temperature (°C)",
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(color="#475569", size=11),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", range=[datetime.combine(selected_date, time(8, 0)), datetime.combine(selected_date, time(22, 0))]),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", range=[16, 32]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_temp, use_container_width=True)

st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

# --- 6. BOTTOM ROW: DEVICE STATUS & OCCUPANCY/MODE ---
bot_col1, bot_col2 = st.columns([1.1, 1.9])

# HVAC Device Status Table
with bot_col1:
    st.markdown("<div class='card-header-title'>⚙️ HVAC Device Status</div>", unsafe_allow_html=True)
    
    hvac_status_str = "<span class='badge-on'><span class='circle-dot circle-green'></span> ON</span>" if hvac_on else "<span class='badge-off'><span class='circle-dot circle-gray'></span> OFF</span>"
    cooling_str = "<span class='badge-on'><span class='circle-dot circle-green'></span> ACTIVE</span>" if is_cooling else "<span class='badge-off'><span class='circle-dot circle-gray'></span> IDLE</span>"
    damper_str = "<span class='badge-on'><span class='circle-dot circle-green'></span> OPEN</span>" if cur_occ > 0 else "<span class='badge-off'><span class='circle-dot circle-gray'></span> MINIMUM</span>"
    
    table_html = f"""
    <div style="background-color: #ffffff; border-radius: 10px; border: 1px solid #e2e8f0; overflow: hidden;">
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

# Occupancy & HVAC Mode Chart
with bot_col2:
    st.markdown("<div class='card-header-title'>👥 Occupancy & HVAC Mode</div>", unsafe_allow_html=True)
    fig_occ = go.Figure()
    
    # Background HVAC Mode Bars
    fig_occ.add_trace(go.Bar(
        x=df_live.index, y=(df_live['predictive_hvac_power_kW'] > 0).astype(int) * 45,
        name='HVAC Mode (Active)',
        marker_color='rgba(219, 234, 254, 0.6)',
        width=1000 * 60 * 4
    ))
    
    # Predicted Occupancy (+15 min) (Orange dashed)
    fig_occ.add_trace(go.Scatter(
        x=df_live.index, y=df_live['occupancy_forecast_15min'],
        mode='lines', name='Predicted Occupancy (+15 min)',
        line=dict(color='#f97316', width=2, dash='dash')
    ))
    
    # Actual Occupancy (Solid Blue)
    fig_occ.add_trace(go.Scatter(
        x=df_live.index, y=df_live['occupancy_now'],
        mode='lines', name='Actual Occupancy',
        line=dict(color='#0284c7', width=2.5)
    ))

    fig_occ.update_layout(
        margin=dict(l=20, r=20, t=10, b=20),
        xaxis_title="", yaxis_title="People",
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(color="#475569", size=11),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", range=[datetime.combine(selected_date, time(8, 0)), datetime.combine(selected_date, time(22, 0))]),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", range=[0, 50]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_occ, use_container_width=True)
