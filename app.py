Here is the clean, corrected code. Simply copy this and replace your entire `app.py` file to get the clean, intuitive monitoring dashboard working.

```python
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="HVAC Monitoring Dashboard", layout="wide", initial_sidebar_state="expanded")

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
    }
    .metric-title { color: #6c757d; font-size: 14px; font-weight: 600; text-transform: uppercase; margin-bottom: 8px; }
    .metric-value { color: #212529; font-size: 32px; font-weight: bold; }
    .status-on { color: #28a745; font-weight: bold; }
    .status-off { color: #6c757d; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA LOADING ---
@st.cache_data
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
unique_dates = df_full.index.normalize().unique().date

# --- 3. SIDEBAR: TIME SIMULATION ---
st.sidebar.markdown("### 🕒 Time Controls")
st.sidebar.write("Scrub through the day to monitor system behavior.")

if len(unique_dates) == 0:
    st.error("No valid dates found in the dataset.")
    st.stop()

selected_day = st.sidebar.selectbox("Select Date", options=unique_dates)
df_day = df_full[df_full.index.date == selected_day]

if not df_day.empty:
    time_options = df_day.index.time
    current_time = st.sidebar.select_slider("Current Time", options=time_options, value=time_options[len(time_options)//2])
else:
    current_time = time(12, 0)

# Filter data up to the simulated current time
df_live = df_day[df_day.index.time <= current_time]

# --- 4. CURRENT METRICS CALCULATIONS ---
if not df_live.empty:
    current_temp = df_live['T_pred'].iloc[-1]
    current_power = df_live['power_pred'].iloc[-1]
    current_occ = int(df_live['occ_true'].iloc[-1])
    total_energy_today = df_live['energy_interval_pred'].sum()
    
    # Determine device status based on power draw
    if current_power > 0:
        hvac_status_html = "<span class='status-on'>🟢 RUNNING</span>"
    else:
        hvac_status_html = "<span class='status-off'>⚪ STANDBY</span>"
else:
    current_temp, current_power, current_occ, total_energy_today = 0, 0, 0, 0
    hvac_status_html = "<span class='status-off'>⚪ OFFLINE</span>"

# --- 5. MAIN DASHBOARD UI ---
st.title("🏢 Smart HVAC Monitoring Dashboard")
st.markdown("Real-time monitoring of facility environmental conditions, equipment status, and energy usage.")

# TOP ROW: KPI CARDS
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Device Status (HVAC)</div>
        <div class="metric-value">{hvac_status_html}</div>
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
        <div class="metric-title">Current Occupants</div>
        <div class="metric-value">{current_occ}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- 6. CHARTS ---
# Helper function for clean Plotly charts
def create_clean_plot(data, y_col, title, y_label, color, is_area=False, is_step=False, hlines=None):
    fig = go.Figure()
    if not data.empty:
        if is_area:
            # Manually construct rgba for fillcolor to avoid tuples in f-strings
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
    st.plotly_chart(fig_occ, use_container_width=True)
