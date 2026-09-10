import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, date, timedelta, time

st.set_page_config(page_title="Live GEB Simulator", layout="wide")
st.title("🏢 LIVE: Grid-Interactive Efficient Building (GEB)")

# --- LIVE TIME FEED ---
st.sidebar.header("🔴 Live Time Feed")
dummy_times = pd.date_range("00:00", "23:55", freq="5min").time
current_time = st.sidebar.select_slider(
    "Current Time of Day",
    options=dummy_times,
    value=time(14, 0) # Default to 2 PM
)

# --- TRANSMISSION CONTROL CENTRE ---
st.sidebar.markdown("---")
st.sidebar.header("⚡ Grid Control Centre (AEMO/Utility)")
st.sidebar.write("Issue dynamic instructions based on grid conditions.")

event_type = st.sidebar.selectbox(
    "Grid Instruction Type",
    options=[
        "Contingency FCAS (Fast Frequency Drop)", 
        "Peak Demand / RERT (Capacity Shortfall)"
    ],
    help="FCAS is a short 15-min emergency response. Peak Demand is a long 2-hour capacity shed."
)

issue_load_shed = st.sidebar.toggle("🚨 Dispatch Load Shed Command", value=False)

# Auto-set duration based on standard Grid preferences
if "FCAS" in event_type:
    shed_duration_mins = 15
else:
    shed_duration_mins = 120

st.sidebar.markdown("---")
st.sidebar.header("🛡️ Building Safety Constraints")
st.sidebar.write("Grid compliance must not violate critical safety.")
max_temp_override = st.sidebar.slider(
    "Safety Temp Override (°C)", 
    min_value=26.0, max_value=30.0, value=27.5, step=0.1,
    help="If internal temp hits this threshold, HVAC ignores the grid and cools the room."
)

st.sidebar.markdown("---")
st.sidebar.header("💰 Financials")
energy_rate = st.sidebar.number_input("Electricity Rate ($/kWh)", value=0.35, step=0.01) # higher rate for peak

# Calculate Event Window
today_date = date.today()
if issue_load_shed:
    event_start_time = current_time
    event_end_dt = datetime.combine(today_date, current_time) + timedelta(minutes=shed_duration_mins)
    event_end_time = event_end_dt.time()
else:
    event_start_time = None
    event_end_time = None

# --- DUMMY DATA GENERATOR ---
@st.cache_data(show_spinner=False)
def generate_live_data(sim_date, grid_active, grid_start, grid_end, max_temp):
    times = pd.date_range(start=sim_date, end=sim_date + timedelta(days=1), freq='5min', inclusive='left')
    df = pd.DataFrame({'timestamp': times})
    df = df.set_index('timestamp')
    
    np.random.seed(42)
    
    # 1. Occupancy & Outdoor Temp
    occupancy = np.zeros(len(df))
    occupancy[96:144] = np.random.randint(20, 50, 48)  
    occupancy[144:156] = np.random.randint(5, 15, 12)  
    occupancy[156:216] = np.random.randint(20, 45, 60) 
    
    df['occ_true'] = occupancy
    df['occ_pred'] = df['occ_true'] + np.random.randint(-3, 4, len(df))
    df['occ_pred'] = df['occ_pred'].clip(lower=0)
    df['outdoor_temp'] = 22 + 12 * np.sin(np.pi * (df.index.hour - 6) / 12) # Hotter day to force override

    # 2. Sched Baseline
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

    # 3. Predictive HVAC (Grid + Safety Logic)
    t_pred, p_pred, override_flag = [], [], []
    curr_t_pred = 20.0
    for i, t_stamp in enumerate(df.index):
        occ = df['occ_true'].iloc[i]
        
        # Grid Event Check
        if grid_active and grid_start is not None and grid_end is not None:
            if grid_start <= grid_end:
                is_grid_event = grid_start <= t_stamp.time() <= grid_end
            else:
                is_grid_event = t_stamp.time() >= grid_start or t_stamp.time() <= grid_end
        else:
            is_grid_event = False
            
        # SAFETY OVERRIDE LOGIC
        is_overridden = False
        if is_grid_event and curr_t_pred >= max_temp:
            is_grid_event = False # Cancel the grid instruction to save occupants
            is_overridden = True
            
        override_flag.append(is_overridden)

        if is_grid_event:
            # SHED LOAD
            curr_t_pred += (df['outdoor_temp'].iloc[i] - curr_t_pred) * 0.05
            p_pred.append(0.0)
        elif occ > 5 or is_overridden:
            # COOLING (Normal or Emergency Recovery)
            power_draw = 12.0 + np.random.normal(0, 1.0) if is_overridden else 8.0 + np.random.normal(0, 1.0)
            target_temp = 23.0 if is_overridden else 24.0
            
            curr_t_pred += (target_temp - curr_t_pred) * 0.2 # Faster cooling during recovery
            p_pred.append(power_draw)
        else:
            # UNOCCUPIED DRIFT
            curr_t_pred += (df['outdoor_temp'].iloc[i] - curr_t_pred) * 0.05
            p_pred.append(0.0)
            
        t_pred.append(curr_t_pred)
        
    df['T_pred'] = t_pred
    df['power_pred'] = np.maximum(0, p_pred)
    df['safety_override_active'] = override_flag

    # 4. Energy & Comfort Math
    df['energy_interval_true'] = df['power_true'] * (5/60) 
    df['energy_interval_pred'] = df['power_pred'] * (5/60)
    df['energy_true'] = df['energy_interval_true'].cumsum()
    df['energy_pred'] = df['energy_interval_pred'].cumsum()
    
    df['scheduled_comfort_ok'] = np.where(df['occ_true'] > 0, (df['T_true'] >= 22.8) & (df['T_true'] <= 25.8), np.nan)
    df['predictive_comfort_ok'] = np.where(df['occ_true'] > 0, (df['T_pred'] >= 22.8) & (df['T_pred'] <= 25.8), np.nan)

    return df

full_day_df = generate_live_data(
    datetime.combine(today_date, datetime.min.time()), 
    issue_load_shed, event_start_time, event_end_time, max_temp_override
)
df_live = full_day_df[full_day_df.index.time <= current_time]

# --- LIVE METRICS CALCULATION ---
def calc_live_metrics(data):
    if data.empty:
        return 0, 1.0, 1.0, 0, False
    
    energy_diff = data['energy_interval_pred'].sum() - data['energy_interval_true'].sum()
    comf_true = data['scheduled_comfort_ok'].dropna().mean()
    comf_pred = data['predictive_comfort_ok'].dropna().mean()
    if pd.isna(comf_true): comf_true = 1.0
    if pd.isna(comf_pred): comf_pred = 1.0
    
    load_reduction = 0
    override_triggered = data['safety_override_active'].any()
    
    if issue_load_shed and event_start_time and event_end_time:
        if event_start_time <= event_end_time:
            event_mask = (data.index.time >= event_start_time) & (data.index.time <= event_end_time)
        else:
            event_mask = (data.index.time >= event_start_time) | (data.index.time <= event_end_time)
            
        event_data = data[event_mask]
        if not event_data.empty:
            load_reduction = event_data['power_true'].mean() - event_data['power_pred'].mean()

    return energy_diff, comf_true, comf_pred, load_reduction, override_triggered

energy_diff, comf_true, comf_pred, load_reduction, has_override = calc_live_metrics(df_live)
savings_usd = abs(energy_diff) * energy_rate if energy_diff < 0 else (energy_diff * energy_rate)

# --- DASHBOARD HEADER ---
st.subheader(f"📊 System Status: **{today_date} | Time: {current_time}**")
if has_override:
    st.error("⚠️ SAFETY OVERRIDE TRIGGERED: Grid instruction was cancelled to prevent building overheating.")

col1, col2, col3, col4 = st.columns(4)
with col1:
    if issue_load_shed:
        st.metric("⚡ Average Load Shed", f"{load_reduction:.2f} kW", 
                  help=f"Target: {shed_duration_mins} MINS | Type: {event_type.split(' ')[0]}")
    else:
        st.metric("⚡ Grid Instruction", "Standby")
with col2:
    label = "💸 Total Cost Savings" if energy_diff <= 0 else "💸 Extra Cost"
    st.metric(label, f"${savings_usd:.2f}", delta=f"{energy_diff:.2f} kWh vs Sched", delta_color="inverse")
with col3:
    st.metric("Occupied Comfort (Sched)", f"{comf_true*100:.1f}%")
with col4:
    delta_comf = (comf_pred - comf_true) * 100
    st.metric("Occupied Comfort (Pred)", f"{comf_pred*100:.1f}%", delta=f"{delta_comf:.1f}% vs Sched", delta_color="normal")

st.markdown("---")

# --- CHARTS ---
tab1, tab2 = st.tabs(["🔴 Live Telemetry", "📈 Energy Accumulation"])

def create_plot(data, y_true_col, y_pred_col, title, y_label, true_name, pred_name, hlines=[], show_grid=False):
    fig = go.Figure()
    
    if not data.empty:
        fig.add_trace(go.Scatter(x=data.index, y=data[y_true_col], name=true_name, line=dict(color='#1f77b4', width=2)))
        fig.add_trace(go.Scatter(x=data.index, y=data[y_pred_col], name=pred_name, line=dict(color='#ff7f0e', dash='dash', width=2)))
        
        # Highlight safety override periods
        if 'safety_override_active' in data.columns and data['safety_override_active'].any():
            override_data = data[data['safety_override_active']]
            fig.add_trace(go.Scatter(
                x=override_data.index, y=override_data[y_pred_col],
                mode='markers', name='Safety Override',
                marker=dict(color='red', size=8, symbol='x')
            ))
        
    for hline in hlines:
        fig.add_hline(y=hline, line_dash="dot", line_color="gray")
        
    full_day_start = datetime.combine(today_date, datetime.min.time())
    full_day_end = datetime.combine(today_date, time(23, 59))
        
    if show_grid and issue_load_shed and event_start_time and event_end_time:
        event_start_dt = datetime.combine(today_date, event_start_time)
        event_end_dt = datetime.combine(today_date, event_end_time)
        if event_end_dt.time() < event_start_dt.time():
            event_end_dt += timedelta(days=1)

        fig.add_vrect(
            x0=event_start_dt, x1=event_end_dt,
            fillcolor="orange", opacity=0.15, layer="below", line_width=0,
            annotation_text=f"GRID EVENT ({shed_duration_mins}m)", annotation_position="top left"
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
        st.plotly_chart(create_plot(df_live, 'occ_true', 'occ_pred', "Live Occupancy", "Occupants", "Actual", "Predicted"), use_container_width=True)
        st.plotly_chart(create_plot(df_live, 'power_true', 'power_pred', "HVAC Power Draw (kW)", "Power (kW)", "Scheduled", "Predictive", show_grid=True), use_container_width=True)
    with col_chart2:
        st.plotly_chart(create_plot(df_live, 'T_true', 'T_pred', "Live Temp vs Constraints", "Temp (°C)", "Scheduled", "Predictive", hlines=[22.8, 25.8, max_temp_override], show_grid=True), use_container_width=True)

with tab2:
    st.plotly_chart(create_plot(df_live, 'energy_true', 'energy_pred', "Cumulative Energy Used", "Energy (kWh)", "Scheduled", "Predictive", show_grid=True), use_container_width=True)
