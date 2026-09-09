import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import timedelta, datetime

st.set_page_config(page_title="HVAC & Grid Simulator", layout="wide")
st.title("🏢 HVAC Predictive Control & Grid Support Simulator")

@st.cache_data
def load_data():
    try:
        df = pd.read_csv('backtest_hvac_comparison.csv')
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        st.stop()

    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
    else:
        first_col = df.columns[0]
        df[first_col] = pd.to_datetime(df[first_col])
        df = df.set_index(first_col)

    df = df.sort_index()

    # Base Mappings
    df['occ_true'] = df['occupancy_actual']
    df['occ_pred'] = df['occupancy_predicted']
    df['T_true'] = df['scheduled_room_temperature_C']
    df['T_pred'] = df['predictive_room_temperature_C']
    df['energy_true'] = df['scheduled_energy_cumulative_kWh']
    df['energy_pred'] = df['predictive_energy_cumulative_kWh']
    
    # Interval Energy and Power for Grid load tracking
    df['energy_interval_true'] = df['scheduled_energy_interval_kWh']
    df['energy_interval_pred'] = df['predictive_energy_interval_kWh']
    df['power_true'] = df['scheduled_hvac_power_kW']
    df['power_pred'] = df['predictive_hvac_power_kW']

    return df

df = load_data()

# --- SIDEBAR CONTROLS ---
st.sidebar.header("⏳ Simulation Controls")
unique_dates = df.index.normalize().unique().date
simulated_day = st.sidebar.select_slider(
    "Select Simulated Current Day",
    options=unique_dates,
    value=unique_dates[-1]
)

st.sidebar.markdown("---")
st.sidebar.header("💰 Financials")
energy_rate = st.sidebar.number_input("Electricity Rate ($/kWh)", value=0.15, step=0.01)

st.sidebar.markdown("---")
st.sidebar.header("⚡ Grid Support Instruction")
st.sidebar.write("Simulate a Transmission System load reduction request (Demand Response).")
grid_event_active = st.sidebar.checkbox("Activate Grid Signal Today", value=True)
event_start_time = st.sidebar.time_input("Instruction Start", value=datetime.strptime("14:00", "%H:%M").time())
event_end_time = st.sidebar.time_input("Instruction End", value=datetime.strptime("17:00", "%H:%M").time())

# Filter datasets
df_history = df[df.index.date <= simulated_day]
df_today = df[df.index.date == simulated_day]
yesterday = simulated_day - timedelta(days=1)
df_yesterday = df[df.index.date == yesterday]

# --- METRICS CALCULATION ---
def calc_metrics(data_slice):
    if data_slice.empty:
        return 0, 0, 0, 0, 0
    rmse = np.sqrt(np.mean((data_slice['T_pred'] - data_slice['T_true'])**2))
    energy_diff = data_slice['energy_interval_pred'].sum() - data_slice['energy_interval_true'].sum()
    comf_true = ((data_slice['T_true'] < 20) | (data_slice['T_true'] > 26)).mean()
    comf_pred = ((data_slice['T_pred'] < 20) | (data_slice['T_pred'] > 26)).mean()
    
    # Calculate Grid Event Load Reduction (kW) if applicable
    load_reduction = 0
    if grid_event_active:
        event_mask = (data_slice.index.time >= event_start_time) & (data_slice.index.time <= event_end_time)
        event_data = data_slice[event_mask]
        if not event_data.empty:
            load_reduction = event_data['power_true'].mean() - event_data['power_pred'].mean()

    return rmse, energy_diff, comf_true, comf_pred, load_reduction

today_rmse, today_energy_diff, today_comf_true, today_comf_pred, today_load_reduction = calc_metrics(df_today)
yest_rmse, yest_energy_diff, _, _, _ = calc_metrics(df_yesterday)

today_savings_usd = abs(today_energy_diff) * energy_rate if today_energy_diff < 0 else (today_energy_diff * energy_rate)

# --- DISPLAY TOP METRICS ---
st.subheader(f"📊 Live Dashboard: **{simulated_day}**")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Today's Temp RMSE", f"{today_rmse:.2f} °C")
with col2:
    label = "💸 Money Saved Today" if today_energy_diff < 0 else "💸 Extra Cost Today"
    st.metric(label, f"${today_savings_usd:.2f}", 
              delta=f"{today_energy_diff:.2f} kWh", delta_color="inverse")
with col3:
    st.metric("Comfort Violation (Pred)", f"{today_comf_pred*100:.1f}%", 
              delta=f"{(today_comf_pred - today_comf_true)*100:.1f}% vs Sched", delta_color="inverse")
with col4:
    if grid_event_active:
        st.metric("⚡ Grid Avg Load Shedding", f"{today_load_reduction:.2f} kW", 
                  help="Average power reduced during the Grid Instruction window.")
    else:
        st.metric("⚡ Grid Support", "Inactive")

st.markdown("---")

# --- CHARTS SETUP ---
tab1, tab2 = st.tabs(["📅 Today's Operations", "📈 Cumulative History"])

def create_plot(data, y_true_col, y_pred_col, title, y_label, true_name, pred_name, hlines=[], show_grid_event=False):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data[y_true_col], name=true_name, line=dict(color='#1f77b4', width=2)))
    fig.add_trace(go.Scatter(x=data.index, y=data[y_pred_col], name=pred_name, line=dict(color='#ff7f0e', dash='dash', width=2)))
    
    for hline in hlines:
        fig.add_hline(y=hline, line_dash="dot", line_color="gray")
        
    # Highlight Grid Instruction Window
    if show_grid_event and grid_event_active and not data.empty:
        event_start_dt = datetime.combine(data.index[0].date(), event_start_time)
        event_end_dt = datetime.combine(data.index[0].date(), event_end_time)
        fig.add_vrect(
            x0=event_start_dt, x1=event_end_dt,
            fillcolor="red", opacity=0.1, layer="below", line_width=0,
            annotation_text="Grid Instruction", annotation_position="top left"
        )
        
    fig.update_layout(
        title=title, xaxis_title="Time", yaxis_title=y_label,
        hovermode="x unified", margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(rangeslider=dict(visible=True), type="date")
    )
    return fig

with tab1:
    # Power Chart to visualize Grid Load Shedding
    st.plotly_chart(create_plot(df_today, 'power_true', 'power_pred', "HVAC Power Demand (kW)", "Power (kW)", 
                                "Scheduled Load", "Predictive Load", show_grid_event=True), use_container_width=True)
    st.plotly_chart(create_plot(df_today, 'T_true', 'T_pred', "Indoor Temperature", "Temp (°C)", 
                                "Scheduled Temp", "Predictive Temp", hlines=[20, 26], show_grid_event=True), use_container_width=True)

with tab2:
    st.plotly_chart(create_plot(df_history, 'T_true', 'T_pred', "Historical Indoor Temperature", "Temp (°C)", "Scheduled", "Predictive", hlines=[20, 26]), use_container_width=True)
    st.plotly_chart(create_plot(df_history, 'energy_true', 'energy_pred', "Cumulative HVAC Energy", "Energy (kWh)", "Scheduled", "Predictive"), use_container_width=True)
