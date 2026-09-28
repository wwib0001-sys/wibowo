import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, date, timedelta, time
import pytz

# Configure page for Master Control layout
st.set_page_config(page_title="GEB Master Control", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for Cyberpunk / Dark Green UI
st.markdown("""
<style>
    .stApp { background-color: #04120a; color: #ffffff; }
    .glass-panel {
        background-color: rgba(10, 30, 20, 0.6);
        border: 2px solid #2eb84e;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 0 10px rgba(46, 184, 78, 0.2);
    }
    .metric-container { display: flex; justify-content: space-between; align-items: center; text-align: center; }
    .circle-metric {
        width: 120px; height: 120px; border-radius: 50%; border: 4px solid #39ff14;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        background-color: rgba(57, 255, 20, 0.05); box-shadow: 0 0 15px rgba(57, 255, 20, 0.3) inset;
    }
    .circle-value { font-size: 28px; font-weight: bold; margin: 0; line-height: 1; }
    .circle-label { font-size: 12px; color: #a0c4a8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;}
    .circle-unit { font-size: 14px; color: #a0c4a8; }
    .panel-title { font-size: 12px; color: #a0c4a8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px; font-weight: 600;}
    .main-heading { font-size: 24px; font-weight: bold; margin-bottom: 15px; color: #ffffff;}
    .predictive-text { font-size: 26px; font-weight: bold; color: #ffffff; margin: 5px 0;}
    .sub-text { font-size: 14px; color: #a0c4a8;}
    .confidence { color: #39ff14; font-size: 14px; font-weight: bold; float: right;}
    header {visibility: hidden;} #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

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
    df['occ_true'] = df['occupancy_now']
    df['occ_pred_15m'] = df['occupancy_forecast_15min']
    df['occ_actual_15m'] = df['occupancy_actual_15min_later']
    df['T_true'] = df['scheduled_room_temperature_C']
    df['T_pred'] = df['predictive_room_temperature_C']
    df['power_true'] = df['scheduled_hvac_power_kW']
    df['power_pred_base'] = df['predictive_hvac_power_kW']
    df['energy_interval_true'] = df['scheduled_energy_cumulative_kWh'].diff().fillna(0).clip(lower=0)
    df['energy_interval_pred_base'] = df['predictive_energy_cumulative_kWh'].diff().fillna(0).clip(lower=0)
    return df

df_full = load_data()

# --- LIVE CLOCK SYNC ---
# Get current time in Melbourne (AEST/AEDT)
melbourne_tz = pytz.timezone('Australia/Melbourne')
actual_now = datetime.now(melbourne_tz)
live_date = actual_now.date()
live_time = actual_now.time()

# Check if today's date exists in the CSV. If not, fallback to the first available date for demonstration.
unique_dates = df_full.index.normalize().unique().date
if live_date in unique_dates:
    selected_day = live_date
else:
    selected_day = unique_dates[0] if len(unique_dates) > 0 else date.today()
    
df_day = df_full[df_full.index.date == selected_day]

# --- DISPATCH CONSOLE (SIDEBAR) ---
st.sidebar.markdown("## 🎛️ DISPATCH CONSOLE")
st.sidebar.markdown(f"**Live Date:** {selected_day}")
st.sidebar.markdown(f"**Live Time:** {live_time.strftime('%H:%M:%S')} AEST")

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ TRANSMISSION INSTRUCTIONS")
event_type = st.sidebar.selectbox("Grid Event Type", options=["Contingency FCAS (15m)", "Peak Demand / RERT (2h)"])
issue_load_shed = st.sidebar.toggle("🚨 INITIATE LOAD SHED", value=False)
shed_duration_mins = 15 if "FCAS" in event_type else 120

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛡️ LOCAL SAFETY OVERRIDES")
max_temp_override = st.sidebar.slider("Critical Temp Limit (°C)", min_value=26.0, max_value=30.0, value=27.5, step=0.1)

# --- GRID OVERRIDE ENGINE ---
if issue_load_shed:
    event_start_time = live_time
    event_end_dt = datetime.combine(selected_day, live_time) + timedelta(minutes=shed_duration_mins)
    event_end_time = event_end_dt.time()
else:
    event_start_time = None
    event_end_time = None

def apply_grid_override(df_day_subset):
    df_dyn = df_day_subset.copy()
    if df_dyn.empty:
        df_dyn['power_pred'] = []
        df_dyn['T_pred_dynamic'] = []
        df_dyn['safety_override_active'] = []
        df_dyn['energy_interval_pred'] = []
        return df_dyn

    df_dyn['power_pred'] = df_dyn['power_pred_base']
    df_dyn['T_pred_dynamic'] = df_dyn['T_pred']
    df_dyn['safety_override_active'] = False
    df_dyn['energy_interval_pred'] = df_dyn['energy_interval_pred_base']
    
    if not issue_load_shed or event_start_time is None:
        return df_dyn

    temp_drift = 0.0 
    for i in range(len(df_dyn)):
        t_stamp = df_dyn.index[i].time()
        if event_start_time <= event_end_time:
            is_grid_event = event_start_time <= t_stamp <= event_end_time
        else:
            is_grid_event = t_stamp >= event_start_time or t_stamp <= event_end_time
            
        current_temp_with_drift = df_dyn['T_pred'].iloc[i] + temp_drift

        if is_grid_event:
            if current_temp_with_drift >= max_temp_override:
                df_dyn.loc[df_dyn.index[i], 'safety_override_active'] = True
                temp_drift = 0.0 
            else:
                df_dyn.loc[df_dyn.index[i], 'power_pred'] = 0.0
                outdoor_t = df_dyn['outdoor_temperature_C'].iloc[i] if 'outdoor_temperature_C' in df_dyn.columns else 28.0
                if current_temp_with_drift < outdoor_t:
                    temp_drift += (outdoor_t - current_temp_with_drift) * 0.05 
        else:
            if temp_drift > 0: temp_drift *= 0.5 
            if temp_drift < 0.1: temp_drift = 0.0
        df_dyn.loc[df_dyn.index[i], 'T_pred_dynamic'] = df_dyn['T_pred'].iloc[i] + temp_drift
    df_dyn['energy_interval_pred'] = df_dyn['power_pred'] * (5/60) 
    return df_dyn

# Filter data to simulate the live feed up to the current time
df_live = df_day[df_day.index.time <= live_time]
df_live_dyn = apply_grid_override(df_live)

# Extract current live metrics safely
current_temp = df_live_dyn['T_pred_dynamic'].iloc[-1] if not df_live_dyn.empty else 0.0
current_occ = df_live_dyn['occ_true'].iloc[-1] if not df_live_dyn.empty else 0
forecast_occ = df_live_dyn['occ_pred_15m'].iloc[-1] if not df_live_dyn.empty else 0

occ_status = "High" if current_occ > 15 else "Moderate" if current_occ > 5 else "Low"
occ_color = "#ff2a2a" if occ_status == "High" else "#ffaa00" if occ_status == "Moderate" else "#a0c4a8"

# ==========================================
# UI: DARK THEME MASTER DASHBOARD
# ==========================================
col1, col2 = st.columns([2.2, 1], gap="large")

with col1:
    st.markdown("""
    <div style='margin-bottom: 10px;'>
        <div class='panel-title'>HVAC PREDICTIVE CONTROL</div>
        <div class='main-heading'>Occupancy-Driven Demand Response</div>
    </div>
    """, unsafe_allow_html=True)
    
    def create_dark_plot(data, y_true_col, y_pred_col, title, y_label, true_name, pred_name, hlines=[], is_step=False):
        fig = go.Figure()
        if not data.empty and y_true_col in data.columns and y_pred_col in data.columns:
            if is_step:
                fig.add_trace(go.Scatter(x=data.index, y=data[y_true_col], name=true_name, line=dict(color='#39ff14', width=2), mode='lines', line_shape='hv'))
                fig.add_trace(go.Scatter(x=data.index, y=data[y_pred_col], name=pred_name, line=dict(color='#ff2a2a', dash='dash', width=2), mode='lines', line_shape='hv'))
            else:
                fig.add_trace(go.Scatter(x=data.index, y=data[y_true_col], name=true_name, line=dict(color='#39ff14', width=2)))
                fig.add_trace(go.Scatter(x=data.index, y=data[y_pred_col], name=pred_name, line=dict(color='#ff2a2a', dash='dash', width=2)))
                
            if 'safety_override_active' in data.columns and data['safety_override_active'].any():
                override_data = data[data['safety_override_active']]
                fig.add_trace(go.Scatter(x=override_data.index, y=override_data[y_pred_col], mode='markers', name='Override', marker=dict(color='red', size=8, symbol='x')))
        
        for hline in hlines:
            fig.add_hline(y=hline, line_dash="dot", line_color="gray")
            
        full_day_start = datetime.combine(selected_day, datetime.min.time())
        full_day_end = datetime.combine(selected_day, time(23, 59))
        
        if issue_load_shed and event_start_time and event_end_time:
            event_start_dt = datetime.combine(selected_day, event_start_time)
            event_end_dt = datetime.combine(selected_day, event_end_time)
            if event_end_dt.time() < event_start_dt.time(): event_end_dt += timedelta(days=1)
            fig.add_vrect(x0=event_start_dt, x1=event_end_dt, fillcolor="orange", opacity=0.2, layer="below", line_width=0, annotation_text=f"GRID DISPATCH", annotation_position="top left")
            
        fig.update_layout(
            title=dict(text=title, font=dict(size=14, color='#a0c4a8', family="monospace")),
            xaxis_title="", yaxis_title=y_label, hovermode="x unified",
            margin=dict(l=20, r=20, t=40, b=20), xaxis_range=[full_day_start, full_day_end],
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#a0c4a8"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#144021')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#144021')
        return fig

    # Stack charts vertically in the left column
    st.markdown("<div class='glass-panel'>", unsafe_allow_html=True)
    st.plotly_chart(create_dark_plot(df_live_dyn, 'occ_true', 'occ_pred_15m', "OCCUPANCY FORECAST (15m Ahead)", "Occupants", "Actual", "Forecasted", is_step=True), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='glass-panel'>", unsafe_allow_html=True)
    st.plotly_chart(create_dark_plot(df_live_dyn, 'power_true', 'power_pred', "ELECTRICAL LOAD (kW)", "Power (kW)", "Base Load", "Predictive Load", is_step=True), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


with col2:
    # Panel 1: Live Status Metrics
    st.markdown(f"""
    <div class='glass-panel' style='padding: 30px 20px;'>
        <div class='metric-container'>
            <div class='circle-metric'>
                <div class='circle-label'>TEMPERATURE</div>
                <div class='circle-value'>{current_temp:.1f}</div>
                <div class='circle-unit'>°C</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 36px; color: #ffffff;'>👥</div>
                <div class='circle-value' style='font-size: 32px;'>{int(current_occ)}</div>
                <div style='color: {occ_color}; font-weight: bold; font-size: 14px;'>{occ_status}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Panel 2: Predictive Alert
    st.markdown(f"""
    <div class='glass-panel'>
        <div class='panel-title'>MODEL OUTPUT - 15 MIN AHEAD <span class='confidence'>High Confidence</span></div>
        <div class='predictive-text'>Forecast Occupancy {int(forecast_occ)}</div>
        <div class='sub-text' style='margin-top: 10px;'>Adjusting HVAC setpoints based on incoming thermal load.</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Panel 3: Thermal Safety Zone Chart
    st.markdown("""
    <div class='glass-panel'>
    """, unsafe_allow_html=True)
    st.plotly_chart(create_dark_plot(df_live_dyn, 'T_true', 'T_pred_dynamic', "THERMAL SAFETY ZONE (°C)", "Temp (°C)", "Base Temp", "Predictive Temp", hlines=[22.8, 25.8, max_temp_override]), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Automatically rerun the app periodically to fetch the new live time
    from streamlit_autorefresh import st_autorefresh
    # Refresh every 60 seconds to update the clock and the charts
    st_autorefresh(interval=60000, key="live_clock_refresh")