import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, date, timedelta

st.set_page_config(page_title="Live HVAC & Grid Simulator", layout="wide")
st.title("🏢 LIVE: HVAC Predictive Control & Grid Support")

# --- DUMMY DATA GENERATOR ---
@st.cache_data
def generate_live_data(sim_date):
    """Generates 15-minute interval dummy data for a single day."""
    times = pd.date_range(start=sim_date, end=sim_date + timedelta(days=1), freq='15min', inclusive='left')
    df = pd.DataFrame({'timestamp': times})
    df = df.set_index('timestamp')
    
    np.random.seed(42) # For consistent daily pattern
    
    # 1. Simulate Occupancy (Office hours 08:00 - 18:00)
    occupancy = np.zeros(len(df))
    occupancy[32:48] = np.random.randint(10, 50, 16) # Morning spike (8am - 12pm)
    occupancy[48:52] = np.random.randint(5, 20, 4)   # Lunch dip (12pm - 1pm)
    occupancy[52:72] = np.random.randint(10, 45, 20) # Afternoon (1pm - 6pm)
    
    df['occ_true'] = occupancy
    df['occ_pred'] = df['occ_true'] + np.random.randint(-5, 6, len(df))
    df['occ_pred'] = df['occ_pred'].clip(lower=0) # No negative occupancy

    # 2. Simulate Outdoor Temperature (Peaks at 25C around 3 PM)
    df['outdoor_temp'] = 15 + 10 * np.sin(np.pi * (df.index.hour - 6) / 12)

    # 3. Simulate Scheduled HVAC (Rigid baseline: Always ON 8am-6pm)
    t_sched, p_sched = [], []
    curr_t = 18.0
    for i, time in enumerate(df.index):
        if 8 <= time.hour < 18:
            curr_t = 22.0 + np.random.normal(0, 0.2) # Maintains rigid 22C
            p_sched.append(15.0 + np.random.normal(0, 1.0)) # High rigid power
        else:
            curr_t += (df['outdoor_temp'].iloc[i] - curr_t) * 0.15 # Drifts
            p_sched.append(0.0)
        t_sched.append(curr_t)

    df['T_true'] = t_sched
    df['power_true'] = np.maximum(0, p_sched)

    # 4. Simulate Predictive HVAC (Occupancy-driven: Turns down during lunch/low occ)
    t_pred, p_pred = [], []
    curr_t_pred = 18.0
    for i, time in enumerate(df.index):
        occ = df['occ_true'].iloc[i]
        if occ > 5:
            curr_t_pred = 22.5 + np.random.normal(0, 0.4) # Wider comfort band
            p_pred.append(10.0 + np.random.normal(0, 1.5)) # Lower optimized power
        else:
            curr_t_pred += (df['outdoor_temp'].iloc[i] - curr_t_pred) * 0.15
            p_pred.append(0.0)
        t_pred.append(curr_t_pred)
        
    df['T_pred'] = t_pred
    df['power_pred'] = np.maximum(0, p_pred)

    # 5. Energy Calculations (15 mins = 0.25 hours)
    df['energy_interval_true'] = df['power_true'] * 0.25
    df['energy_interval_pred'] = df['power_pred'] * 0.25
    df['energy_true'] = df['energy_interval_true'].cumsum()
    df['energy_pred'] = df['energy_interval_pred'].cumsum()

    return df

# Use today's date for live simulation
today_date = date.today()
full_day_df = generate_live_data(datetime.combine(today_date, datetime.min.time()))

# --- LIVE SIMULATION CONTROLS ---
st.sidebar.header("🔴 Live Time Control")
st.sidebar.write("Slide to simulate the time of day passing.")

# Extract available times for the slider
time_options = full_day_df.index.time
current_time = st.sidebar.select_slider(
    "Current Time of Day",
    options=time_options,
    value=time_options[len(time_options)//2 + 6] # Default to early afternoon
)

# Filter dataset up to the selected "Live Time"
live_mask = full_day_df.index.time <= current_time
df_live = full_day_df.loc[live_mask]

st.sidebar.markdown("---")
st.sidebar.header("💰 Financials & Grid")
energy_rate = st.sidebar.number_input("Electricity Rate ($/kWh)", value=0.15, step=0.01)
grid_event_active = st.sidebar.checkbox("Activate Grid Signal Today", value=True)
event_start_time = st.sidebar.time_input("Instruction Start", value=datetime.strptime("14:00", "%H:%M").time())
event_end_time = st.sidebar.time_input("Instruction End", value=datetime.strptime("17:00", "%H:%M").time())

# --- LIVE METRICS ---
def calc_metrics(data_slice):
    if data_slice.empty:
        return 0, 0, 0, 0, 0
    rmse = np.sqrt(np.mean((data_slice['T_pred'] - data_slice['T_true'])**2))
    energy_diff = data_slice['energy_interval_pred'].sum() - data_slice['energy_interval_true'].sum()
    
    comf_true = ((data_slice['T_true'] < 20) | (data_slice['T_true'] > 26)).mean()
    comf_pred = ((data_slice['T_pred'] < 20) | (data_slice['T_pred'] > 26)).mean()
    
    load_reduction = 0
    if grid_event_active:
        event_mask = (data_slice.index.time >= event_start_time) & (data_slice.index.time <= event_end_time)
        event_data = data_slice[event_mask]
        if not event_data.empty:
            load_reduction = event_data['power_true'].mean() - event_data['power_pred'].mean()

    return rmse, energy_diff, comf_true, comf_pred, load_reduction

rmse, energy_diff, comf_true, comf_pred, load_reduction = calc_metrics(df_live)
savings_usd = abs(energy_diff) * energy_rate if energy_diff < 0 else (energy_diff * energy_rate)

# Display Metrics
st.subheader(f"📊 Live Dashboard: **{today_date} | Time: {current_time}**")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Live Temp RMSE", f"{rmse:.2f} °C")
with col2:
    label = "💸 Money Saved (So Far)" if energy_diff <= 0 else "💸 Extra Cost (So Far)"
    st.metric(label, f"${savings_usd:.2f}", 
              delta=f"{energy_diff:.2f} kWh vs Sched", delta_color="inverse")
with col3:
    st.metric("Comfort Violation (Pred)", f"{comf_pred*100:.1f}%", 
              delta=f"{(comf_pred - comf_true)*100:.1f}% vs Sched", delta_color="inverse")
with col4:
    if grid_event_active and current_time >= event_start_time:
        st.metric("⚡ Grid Load Shedding", f"{load_reduction:.2f} kW")
    else:
        st.metric("⚡ Grid Support", "Pending/Inactive")

st.markdown("---")

# --- CHARTS SETUP ---
def create_plot(data, y_true_col, y_pred_col, title, y_label, true_name, pred_name, hlines=[], show_grid=False):
    fig = go.Figure()
    
    # Add traces if data exists
    if not data.empty:
        fig.add_trace(go.Scatter(x=data.index, y=data[y_true_col], name=true_name, line=dict(color='#1f77b4', width=2)))
        fig.add_trace(go.Scatter(x=data.index, y=data[y_pred_col], name=pred_name, line=dict(color='#ff7f0e', dash='dash', width=2)))
        
    for hline in hlines:
        fig.add_hline(y=hline, line_dash="dot", line_color="gray")
        
    # Full day x-axis range lock so the chart doesn't shrink/grow weirdly
    full_day_start = datetime.combine(today_date, datetime.min.time())
    full_day_end = datetime.combine(today_date, datetime.max.time())
        
    if show_grid and grid_event_active:
        event_start_dt = datetime.combine(today_date, event_start_time)
        event_end_dt = datetime.combine(today_date, event_end_time)
        fig.add_vrect(
            x0=event_start_dt, x1=event_end_dt,
            fillcolor="red", opacity=0.1, layer="below", line_width=0,
            annotation_text="Grid Event", annotation_position="top left"
        )
        
    fig.update_layout(
        title=title, xaxis_title="Time", yaxis_title=y_label,
        hovermode="x unified", margin=dict(l=0, r=0, t=40, b=0),
        xaxis_range=[full_day_start, full_day_end] # Locks the view to a full 24 hours
    )
    return fig

# Render Charts
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.plotly_chart(create_plot(df_live, 'occ_true', 'occ_pred', "Live Occupancy Status", "Occupants", "Actual", "Predicted"), use_container_width=True)
    st.plotly_chart(create_plot(df_live, 'power_true', 'power_pred', "Live Power Demand (kW)", "Power (kW)", "Scheduled Base", "Predictive Opt", show_grid=True), use_container_width=True)

with col_chart2:
    st.plotly_chart(create_plot(df_live, 'T_true', 'T_pred', "Live Indoor Temp vs Comfort", "Temp (°C)", "Scheduled Base", "Predictive Opt", hlines=[20, 26], show_grid=True), use_container_width=True)
    st.plotly_chart(create_plot(df_live, 'energy_true', 'energy_pred', "Cumulative Energy Used", "Energy (kWh)", "Scheduled Base", "Predictive Opt"), use_container_width=True)
