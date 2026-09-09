import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, date, timedelta, time

st.set_page_config(page_title="Live HVAC & Grid Simulator", layout="wide")
st.title("🏢 LIVE: Occupancy HVAC & Grid Frequency Support")

# --- LIVE TIME FEED ---
st.sidebar.header("🔴 Live Time Feed")
st.sidebar.write("Scrub through the day to simulate the passage of time.")
# Create a dummy time index to generate options
dummy_times = pd.date_range("00:00", "23:55", freq="5min").time
current_time = st.sidebar.select_slider(
    "Current Time of Day",
    options=dummy_times,
    value=time(14, 0) # Default to 2 PM
)

# --- CONTROL CENTRE INSTRUCTION (LIVE OVERRIDE) ---
st.sidebar.markdown("---")
st.sidebar.header("⚡ Grid Control Centre")
st.sidebar.write("Issue an immediate command to stabilize grid frequency.")
# Instant instruction toggle rather than schedulable times
issue_load_shed = st.sidebar.toggle("🚨 Issue Immediate Load Shed Command", value=False)

st.sidebar.markdown("---")
st.sidebar.header("💰 Financials")
energy_rate = st.sidebar.number_input("Electricity Rate ($/kWh)", value=0.15, step=0.01)

# Calculate dynamic event window based on the live instruction
today_date = date.today()
if issue_load_shed:
    event_start_time = current_time
    # Instruction lasts for 1 hour from the moment it is issued
    event_end_dt = datetime.combine(today_date, current_time) + timedelta(hours=1)
    event_end_time = event_end_dt.time()
else:
    event_start_time = None
    event_end_time = None

# --- DUMMY DATA GENERATOR ---
@st.cache_data(show_spinner=False)
def generate_live_data(sim_date, grid_active, grid_start, grid_end):
    """Generates 5-minute interval dummy data reflecting live physical responses."""
    times = pd.date_range(start=sim_date, end=sim_date + timedelta(days=1), freq='5min', inclusive='left')
    df = pd.DataFrame({'timestamp': times})
    df = df.set_index('timestamp')
    
    np.random.seed(42) # Consistent daily pattern
    
    # 1. Occupancy Profile (Office: 8 AM - 6 PM with Lunch dip)
    occupancy = np.zeros(len(df))
    occupancy[96:144] = np.random.randint(20, 50, 48)  # Morning (8am - 12pm)
    occupancy[144:156] = np.random.randint(5, 15, 12)  # Lunch (12pm - 1pm)
    occupancy[156:216] = np.random.randint(20, 45, 60) # Afternoon (1pm - 6pm)
    
    df['occ_true'] = occupancy
    df['occ_pred'] = df['occ_true'] + np.random.randint(-3, 4, len(df))
    df['occ_pred'] = df['occ_pred'].clip(lower=0)

    # 2. Outdoor Temp (Peaks at 28C around 3 PM)
    df['outdoor_temp'] = 18 + 10 * np.sin(np.pi * (df.index.hour - 6) / 12)

    # 3. Simulate Scheduled HVAC (Rigid baseline)
    t_sched, p_sched = [], []
    curr_t = 20.0
    for i, t_stamp in enumerate(df.index):
        if 8 <= t_stamp.hour < 18:
            curr_t = 23.5 + np.random.normal(0, 0.1) 
            p_sched.append(15.0 + np.random.normal(0, 0.5)) 
        else:
            curr_t += (df['outdoor_temp'].iloc[i] - curr_t) * 0.05 
            p_sched.append(0.0)
        t_sched.append(curr_t)

    df['T_true'] = t_sched
    df['power_true'] = np.maximum(0, p_sched)

    # 4. Simulate Predictive HVAC (Responds to Occupancy AND Live Instructions)
    t_pred, p_pred = [], []
    curr_t_pred = 20.0
    for i, t_stamp in enumerate(df.index):
        occ = df['occ_true'].iloc[i]
        
        # Check if the current time step falls within the live instruction window
        if grid_active and grid_start and grid_end:
            # Handle end-of-day wrap around for the 1-hour window
            if grid_start <= grid_end:
                is_grid_event = grid_start <= t_stamp.time() <= grid_end
            else:
                is_grid_event = t_stamp.time() >= grid_start or t_stamp.time() <= grid_end
        else:
            is_grid_event = False
            
        if is_grid_event:
            # GRID STABILIZATION OVERRIDE: Shed load completely
            curr_t_pred += (df['outdoor_temp'].iloc[i] - curr_t_pred) * 0.05
            p_pred.append(0.0)
        elif occ > 5:
            # Normal smart occupancy control
            curr_t_pred = 24.0 + np.random.normal(0, 0.2) 
            p_pred.append(8.0 + np.random.normal(0, 1.0)) 
        else:
            # Unoccupied drift
            curr_t_pred += (df['outdoor_temp'].iloc[i] - curr_t_pred) * 0.05
            p_pred.append(0.0)
        t_pred.append(curr_t_pred)
        
    df['T_pred'] = t_pred
    df['power_pred'] = np.maximum(0, p_pred)

    # 5. Energy and Comfort Math
    df['energy_interval_true'] = df['power_true'] * (5/60) 
    df['energy_interval_pred'] = df['power_pred'] * (5/60)
    df['energy_true'] = df['energy_interval_true'].cumsum()
    df['energy_pred'] = df['energy_interval_pred'].cumsum()
    
    df['scheduled_comfort_ok'] = np.where(df['occ_true'] > 0, (df['T_true'] >= 22.8) & (df['T_true'] <= 25.8), np.nan)
    df['predictive_comfort_ok'] = np.where(df['occ_true'] > 0, (df['T_pred'] >= 22.8) & (df['T_pred'] <= 25.8), np.nan)

    return df

# Re-run generator dynamically if the instruction state or current time changes
full_day_df = generate_live_data(
    datetime.combine(today_date, datetime.min.time()), 
    issue_load_shed, event_start_time, event_end_time
)

# Filter to simulate "Live" data feed up to the slider time
df_live = full_day_df[full_day_df.index.time <= current_time]

# --- LIVE METRICS CALCULATION ---
def calc_live_metrics(data):
    if data.empty:
        return 0, 0, 1.0, 1.0, 0
    
    energy_diff = data['energy_interval_pred'].sum() - data['energy_interval_true'].sum()
    
    comf_true = data['scheduled_comfort_ok'].dropna().mean()
    comf_pred = data['predictive_comfort_ok'].dropna().mean()
    if pd.isna(comf_true): comf_true = 1.0
    if pd.isna(comf_pred): comf_pred = 1.0
    
    load_reduction = 0
    if issue_load_shed and event_start_time and event_end_time:
        if event_start_time <= event_end_time:
            event_mask = (data.index.time >= event_start_time) & (data.index.time <= event_end_time)
        else:
            event_mask = (data.index.time >= event_start_time) | (data.index.time <= event_end_time)
            
        event_data = data[event_mask]
        if not event_data.empty:
            load_reduction = event_data['power_true'].mean() - event_data['power_pred'].mean()

    return energy_diff, comf_true, comf_pred, load_reduction

energy_diff, comf_true, comf_pred, load_reduction = calc_live_metrics(df_live)
savings_usd = abs(energy_diff) * energy_rate if energy_diff < 0 else (energy_diff * energy_rate)

# --- DASHBOARD HEADER ---
st.subheader(f"📊 System Status: **{today_date} | Time: {current_time}**")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if issue_load_shed:
        st.metric("⚡ Grid Frequency Support (Load Shed)", f"{load_reduction:.2f} kW", 
                  help="Average power dropped since instruction was issued.")
    else:
        st.metric("⚡ Grid Frequency Support", "Standby")
with col2:
    label = "💸 Total Cost Savings" if energy_diff <= 0 else "💸 Extra Cost"
    st.metric(label, f"${savings_usd:.2f}", 
              delta=f"{energy_diff:.2f} kWh vs Sched", delta_color="inverse")
with col3:
    st.metric("Occupied Comfort (Sched)", f"{comf_true*100:.1f}%")
with col4:
    delta_comf = (comf_pred - comf_true) * 100
    st.metric("Occupied Comfort (Pred)", f"{comf_pred*100:.1f}%", 
              delta=f"{delta_comf:.1f}% vs Sched", delta_color="normal")

st.markdown("---")

# --- CHARTS ---
tab1, tab2, tab3 = st.tabs(["🔴 Live Telemetry", "📈 Energy Accumulation", "📖 Data Dictionary"])

def create_plot(data, y_true_col, y_pred_col, title, y_label, true_name, pred_name, hlines=[], show_grid=False):
    fig = go.Figure()
    
    if not data.empty:
        fig.add_trace(go.Scatter(x=data.index, y=data[y_true_col], name=true_name, line=dict(color='#1f77b4', width=2)))
        fig.add_trace(go.Scatter(x=data.index, y=data[y_pred_col], name=pred_name, line=dict(color='#ff7f0e', dash='dash', width=2)))
        
    for hline in hlines:
        fig.add_hline(y=hline, line_dash="dot", line_color="gray")
        
    # Lock X-axis to full 24 hours
    full_day_start = datetime.combine(today_date, datetime.min.time())
    full_day_end = datetime.combine(today_date, time(23, 59))
        
    if show_grid and issue_load_shed and event_start_time and event_end_time:
        event_start_dt = datetime.combine(today_date, event_start_time)
        event_end_dt = datetime.combine(today_date, event_end_time)
        fig.add_vrect(
            x0=event_start_dt, x1=event_end_dt,
            fillcolor="red", opacity=0.15, layer="below", line_width=0,
            annotation_text="ACTIVE INSTRUCTION", annotation_position="top left"
        )
        
    fig.update_layout(
        title=title, xaxis_title="Time", yaxis_title=y_label,
        hovermode="x unified", margin=dict(l=0, r=0, t=40, b=0),
        xaxis_range=[full_day_start, full_day_end] 
    )
    return fig

with tab1:
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.plotly_chart(create_plot(df_live, 'occ_true', 'occ_pred', "Live Occupancy Tracking", "Occupants", "Actual", "Predicted"), use_container_width=True)
        st.plotly_chart(create_plot(df_live, 'power_true', 'power_pred', "Live HVAC Power Draw (kW)", "Power (kW)", "Scheduled", "Predictive", show_grid=True), use_container_width=True)
    with col_chart2:
        st.plotly_chart(create_plot(df_live, 'T_true', 'T_pred', "Live Indoor Temp vs Comfort Band", "Temp (°C)", "Scheduled", "Predictive", hlines=[22.8, 25.8], show_grid=True), use_container_width=True)

with tab2:
    st.plotly_chart(create_plot(df_live, 'energy_true', 'energy_pred', "Cumulative Energy Used", "Energy (kWh)", "Scheduled Base", "Predictive Opt", show_grid=True), use_container_width=True)

with tab3:
    st.header("Data Dictionary")
    st.write("Contains definitions for Base Inputs, Thermal Responses, Control Signals, Power/Energy Consumption, and Comfort Metrics as previously defined.")
