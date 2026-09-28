import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date, time, timezone, timedelta

# Auto-refresh helper (fails gracefully if module is not installed)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30000, key="data_refresh")
except Exception:
    pass

# --- 1. PAGE CONFIGURATION & STYLING ---
st.set_page_config(page_title="Smart HVAC Monitoring Dashboard", layout="wide", initial_sidebar_state="collapsed")

# Hide the gray sidebar completely and format KPI cards
st.markdown("""
<style>
    /* Completely hide the sidebar to reclaim full screen width */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        display: none !important;
    }
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 96%;
    }
    /* Metric Card Styling */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-title { 
        color: #6c757d; 
        font-size: 13px; 
        font-weight: 700; 
        text-transform: uppercase; 
        letter-spacing: 0.5px;
        margin-bottom: 8px; 
    }
    .metric-value { 
        color: #212529; 
        font-size: 32px; 
        font-weight: bold; 
    }
    .metric-subtext { 
        color: #59359a; 
        font-size: 15px; 
        font-weight: 600; 
        margin-top: 6px; 
    }
    /* Clock Banner Card */
    .clock-card {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 10px;
        padding: 12px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-weight: 700;
        font-size: 28px;
    }
    .circle-indicator { 
        width: 22px; 
        height: 22px; 
        border-radius: 50%; 
        display: inline-block;
    }
    .circle-on { 
        background: radial-gradient(circle at 30% 30%, #51f28b, #28a745); 
        box-shadow: 0 0 10px rgba(40, 167, 69, 0.5); 
    }
    .circle-off { 
        background: radial-gradient(circle at 30% 30%, #adb5bd, #6c757d); 
    }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA LOADING & 29 SEPTEMBER 2026 MAPPING ---
@st.cache_data(ttl=60)
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
    
    # Calculate interval energy from cumulative
    df['energy_interval_pred'] = df['predictive_energy_cumulative_kWh'].diff().fillna(0).clip(lower=0)
    
    return df

df_full = load_data()

# Lock target operation date to 29 September 2026
target_date = date(2026, 9, 29)

# Filter dataset for September 29 and update timestamp year to 2026
df_sep29 = df_full[(df_full.index.month == 9) & (df_full.index.day == 29)].copy()

if not df_sep29.empty:
    df_day = df_sep29
    df_day.index = df_day.index.map(lambda dt: dt.replace(year=2026))
else:
    # Fallback to the first date if September 29 is not in dataset
    first_date = df_full.index.date[0]
    df_day = df_full[df_full.index.date == first_date].copy()
    df_day.index = df_day.index.map(lambda dt: dt.replace(year=2026, month=9, day=29))

# --- 3. LIVE MELBOURNE TIME TRACKING ---
try:
    import pytz
    melbourne_tz = pytz.timezone('Australia/Melbourne')
    now_melbourne = datetime.now(melbourne_tz)
except Exception:
    melbourne_tz = timezone(timedelta(hours=10))
    now_melbourne = datetime.now(melbourne_tz)

live_time = now_melbourne.time()

# Filter data dynamically up to current live Melbourne time
df_live = df_day[df_day.index.time <= live_time]
if df_live.empty:
    df_live = df_day.iloc[:1]

# --- 4. CURRENT METRIC VALUES ---
current_temp = df_live['T_pred'].iloc[-1]
current_power = df_live['power_pred'].iloc[-1]
current_occ = int(df_live['occ_true'].iloc[-1])
forecast_occ = int(df_live['occ_pred'].iloc[-1])
total_energy_today = df_live['energy_interval_pred'].sum()

if current_power > 0:
    hvac_status_html = "<span class='status-badge' style='color: #28a745;'><span class='circle-indicator circle-on'></span> RUNNING</span>"
else:
    hvac_status_html = "<span class='status-badge' style='color: #6c757d;'><span class='circle-indicator circle-off'></span> STANDBY</span>"

# --- 5. HEADER (MERGED TITLE & CLOCK BANNER) ---
col_head_left, col_head_right = st.columns([2.2, 1.2])

with col_head_left:
    st.title("🏢 Smart HVAC Monitoring Dashboard")
    st.write("Real-time monitoring of facility environmental conditions, equipment status, and energy usage.")

with col_head_right:
    st.markdown(f"""
    <div class="clock-card">
        <div>
            <div style="font-size: 12px; font-weight: bold; color: #dc3545; display: flex; align-items: center; gap: 6px;">
                <span style="height: 9px; width: 9px; background-color: #dc3545; border-radius: 50%; display: inline-block;"></span>
                LIVE SYSTEM CLOCK
            </div>
            <div style="font-size: 15px; font-weight: 600; color: #495057; margin-top: 2px;">
                {target_date.strftime('%A, %b %d, %Y')}
            </div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 11px; color: #6c757d; font-weight: 600;">MELBOURNE TIME</div>
            <div style="font-size: 26px; font-weight: bold; color: #dc3545; line-height: 1.1;">
                {live_time.strftime('%H:%M:%S')}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- 6. TOP KPI CARDS ---
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
        <div class="metric-title">Occupancy Demand</div>
        <div class="metric-value">{current_occ} <span style="font-size: 16px; font-weight: normal; color: #6c757d;">Now</span></div>
        <div class="metric-subtext">📈 Forecast (15m): {forecast_occ}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- 7. CHARTS ---
def create_clean_plot(data, y_col, title, y_label, color, is_area=False, is_step=False, hlines=None):
    fig = go.Figure()
    if not data.empty:
        if is_area:
            r = int(color.lstrip("#")[0:2], 16)
            g = int(color.lstrip("#")[2:4], 16)
            b = int(color.lstrip("#")[4:6], 16)
            fill_color = f'rgba({r}, {g}, {b}, 0.12)'
            fig.add_trace(go.Scatter(x=data.index, y=data[y_col], mode='lines', line=dict(color=color, width=2.5), fill='tozeroy', fillcolor=fill_color, name=y_label))
        elif is_step:
            fig.add_trace(go.Scatter(x=data.index, y=data[y_col], mode='lines', line=dict(color=color, width=2.5), line_shape='hv', name=y_label))
        else:
            fig.add_trace(go.Scatter(x=data.index, y=data[y_col], mode='lines', line=dict(color=color, width=2.5), name=y_label))
    
    if hlines:
        for hline in hlines:
            fig.add_hline(y=hline, line_dash="dash", line_color="#dc3545", opacity=0.4)

    # Red vertical marker tracking current Melbourne live time
    live_marker_dt = datetime.combine(target_date, live_time)
    fig.add_vline(x=live_marker_dt, line_width=2, line_dash="solid", line_color="#dc3545", annotation_text="LIVE", annotation_position="top right")

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#343a40")),
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="", yaxis_title=y_label,
        hovermode="x unified",
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        xaxis=dict(
            showgrid=True, 
            gridcolor="#f1f3f5", 
            range=[datetime.combine(target_date, time.min), datetime.combine(target_date, time.max)]
        ),
        yaxis=dict(showgrid=True, gridcolor="#f1f3f5")
    )
    return fig

# Temperature Chart
st.subheader("🌡️ Temperature Profile")
fig_temp = create_clean_plot(df_live, 'T_pred', "Indoor Temperature Tracking", "Temperature (°C)", "#007bff", hlines=[22.8, 25.8])
fig_temp.add_hrect(y0=22.8, y1=25.8, line_width=0, fillcolor="#28a745", opacity=0.1, annotation_text="Comfort Band (22.8 - 25.8°C)", annotation_position="top left")
st.plotly_chart(fig_temp, use_container_width=True)

# Energy and Occupancy Charts
col_c1, col_c2 = st.columns(2)

with col_c1:
    st.subheader("⚡ Energy Usage")
    fig_energy = create_clean_plot(df_live, 'power_pred', "HVAC Power Draw (Demand)", "Power (kW)", "#fd7e14", is_area=True)
    st.plotly_chart(fig_energy, use_container_width=True)

with col_c2:
    st.subheader("👥 Occupancy Demand")
    fig_occ = create_clean_plot(df_live, 'occ_pred', "Predicted Occupancy (15m Horizon)", "People", "#6f42c1", is_step=True)
    if not df_live.empty:
        fig_occ.add_trace(go.Scatter(x=df_live.index, y=df_live['occ_true'], mode='lines', line=dict(color="#6c757d", width=2, dash="dot"), line_shape='hv', name="Actual Now"))
    st.plotly_chart(fig_occ, use_container_width=True)
