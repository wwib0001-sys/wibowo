import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 1. PAGE CONFIGURATION & AUTOREFRESH ---
st.set_page_config(page_title="HVAC Monitoring Dashboard", layout="wide", initial_sidebar_state="expanded")
# Refresh the dashboard automatically every 60 seconds (60000 ms) to keep the live time moving
st_autorefresh(interval=60000, key="data_refresh")

# Custom CSS for a clean, intuitive, and professional monitoring layout
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-title { color: #6c757d; font-size: 14px; font-weight: 600; text-transform: uppercase; margin-bottom: 8px; }
    .metric-value { color: #212529; font-size: 32px; font-weight: bold; }
    .metric-subtext { color: #6f42c1; font-size: 16px; font-weight: bold; margin-top: 5px; }
    .status-on { color: #28a745; font-weight: bold; display: flex; align-items: center; justify-content: center; gap: 8px;}
    .status-off { color: #6c757d; font-weight: bold; display: flex; align-items: center; justify-content: center; gap: 8px;}
    .circle-indicator { width: 24px; height: 24px; border-radius: 50%; }
    .circle-on { background: radial-gradient(circle at 30% 30%, #51f28b, #28a745); box-shadow: 0 4px 6px rgba(40, 167, 69, 0.4); }
    .circle-off { background: radial-gradient(circle at 30% 30%, #adb5bd, #6c757d); }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA LOADING ---
@st.cache_data(ttl=60) # Re-cache data every minute if the file updates
def load_data():
    try:
        df = pd.read_csv('hvac_comparison.csv')
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        st.stop()

    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')

    df = df.sort_index()

    # Map standard columns
    df['occ_true'] = df['occupancy_now']
    df['occ_pred'] = df['occupancy_forecast_15min']
    df['T_pred'] = df['predictive_room_temperature_C']
    df['power_pred'] = df['predictive_hvac_power_kW']
    
    # Calculate energy from cumulative
    df['energy_interval_pred'] = df['predictive_energy_cumulative_kWh'].diff().fillna(0).clip(lower=0)
    
    return df

df_full = load_data()

# --- 3. LIVE TIME SYNC (MELBOURNE AEST) ---
melbourne_tz = pytz.timezone('Australia/Melbourne')
actual_now = datetime.now(melbourne_tz)
live_date = actual_now.date()
live_time = actual_now.time()

# Check if the real-world date exists in our CSV dataset
unique_dates = df_full.index.normalize().unique().date
if live_date in unique_dates:
    selected_day = live_date
else:
    # Fallback to the first date in the dataset if the real date isn't found (for demonstration)
    selected_day = unique_dates[0] if len(unique_dates) > 0 else date.today()

df_day = df_full[df_full.index.date == selected_day]

st.sidebar.markdown("### 🔴 LIVE SYSTEM CLOCK")
st.sidebar.markdown(f"**Date:** {selected_day.strftime('%A, %b %d, %Y')}")
st.sidebar.markdown(f"**Time (AEST):** <span style='color: #dc3545; font-size: 24px; font-weight: bold;'>{live_time.strftime('%H:%M:%S')}</span>", unsafe_allow_html=True)

# Filter data dynamically up to the literal current time
df_live = df_day[df_day.index.time <= live_time]

# --- 4. CURRENT METRICS CALCULATIONS ---
if not df_live.empty:
    current_temp = df_live['T_pred'].iloc[-1]
    current_power = df_live['power_pred'].iloc[-1]
    current_occ = int(df_live['occ_true'].iloc[-1])
    
    # Extract the 15-minute forecast
    forecast_occ = int(df_live['occ_pred'].iloc[-1])
    
    total_energy_today = df_live['energy_interval_pred'].sum()
    
    # Determine device status based on power draw
    if current_power > 0:
        hvac_status_html = "<div class='status-on'><div class='circle-indicator circle-on'></div> RUNNING</div>"
    else:
        hvac_status_html = "<div class='status-off'><div class='circle-indicator circle-off'></div> STANDBY</div>"
else:
    current_temp, current_power, current_occ, forecast_occ, total_energy_today = 0, 0, 0, 0, 0
    hvac_status_html = "<div class='status-off'><div class='circle-indicator circle-off'></div> OFFLINE</div>"

# --- 5. MAIN DASHBOARD UI ---
st.title("🏢 Smart HVAC Monitoring Dashboard")
st.markdown("Real-time monitoring of facility environmental conditions, equipment status, and energy usage.")

# TOP ROW: KPI CARDS
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Device Status (HVAC)</div>
        <div class="metric-value" style="margin-top: 5px;">{hvac_status_html}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Indoor Temperature</div>
        <div class="metric-value">{current_temp:.1f} °C</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Total Energy Today</div>
        <div class="metric-value">{total_energy_today:.1f} kWh</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Occupancy Demand</div>
        <div class="metric-value">{current_occ} <span style="font-size: 16px; font-weight: normal; color: #6c757d;">Now</span></div>
        <div class="metric-subtext">📈 Forecast (15m): {forecast_occ}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- 6. CHARTS ---
# Helper function for clean Plotly charts
def create_clean_plot(data, y_col, title, y_label, color, is_area=False, is_step=False, hlines=None):
    fig = go.Figure()
    if not data.empty:
        if is_area:
            r = int(color.lstrip("#")[0:2], 16)
            g = int(color.lstrip("#")[2:4], 16)
            b = int(color.lstrip("#")[4:6], 16)
            fill_color = f'rgba({r}, {g}, {b}, 0.1)'
            fig.add_trace(go.Scatter(x=data.index, y=data[y_col], mode='lines', line=dict(color=color, width=2), fill='tozeroy', fillcolor=fill_color, name=y_label))
        elif is_step:
            fig.add_trace(go.Scatter(x=data.index, y=data[y_col], mode='lines', line=dict(color=color, width=2), line_shape='hv', name=y_label))
        else:
            fig.add_trace(go.Scatter(x=data.index, y=data[y_col], mode='lines', line=dict(color=color, width=2), name=y_label))
    
    if hlines:
        for hline in hlines:
            fig.add_hline(y=hline, line_dash="dash", line_color="#dc3545", opacity=0.5)

    # Add a vertical line to indicate the current LIVE time on the charts
    current_dt = datetime.combine(selected_day, live_time)
    fig.add_vline(x=current_dt, line_width=2, line_dash="solid", line_color="#dc3545", annotation_text="LIVE", annotation_position="top right")

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#495057")),
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="", yaxis_title=y_label,
        hovermode="x unified",
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#f8f9fa", range=[datetime.combine(selected_day, time.min), datetime.combine(selected_day, time.max)]),
        yaxis=dict(showgrid=True, gridcolor="#f8f9fa")
    )
    return fig

# ROW 1: Temperature Monitoring
st.subheader("🌡️ Temperature Profile")
fig_temp = create_clean_plot(df_live, 'T_pred', "Indoor Temperature Tracking", "Temperature (°C)", "#007bff", hlines=[22.8, 25.8])
# Add context for comfort band
fig_temp.add_hrect(y0=22.8, y1=25.8, line_width=0, fillcolor="#28a745", opacity=0.1, annotation_text="Comfort Zone", annotation_position="top left")
st.plotly_chart(fig_temp, use_container_width=True)

# ROW 2: Energy and Occupancy
col_c1, col_c2 = st.columns(2)

with col_c1:
    st.subheader("⚡ Energy Usage")
    fig_energy = create_clean_plot(df_live, 'power_pred', "HVAC Power Draw (Demand)", "Power (kW)", "#fd7e14", is_area=True)
    st.plotly_chart(fig_energy, use_container_width=True)

with col_c2:
    st.subheader("👥 Occupancy")
    fig_occ = create_clean_plot(df_live, 'occ_pred', "Predicted Occupancy (15m Horizon)", "People", "#6f42c1", is_step=True)
    
    # Overlay the actual current occupancy on the same chart for comparison
    if not df_live.empty:
        fig_occ.add_trace(go.Scatter(x=df_live.index, y=df_live['occ_true'], mode='lines', line=dict(color="#6c757d", width=2, dash="dot"), line_shape='hv', name="Actual Now"))
    
    st.plotly_chart(fig_occ, use_container_width=True)

