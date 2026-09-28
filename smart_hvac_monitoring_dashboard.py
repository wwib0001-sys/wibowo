import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time, date

# --- 1. TIMEZONE HANDLING ---
try:
    import pytz
    melbourne_tz = pytz.timezone('Australia/Melbourne')
except Exception:
    from zoneinfo import ZoneInfo
    melbourne_tz = ZoneInfo('Australia/Melbourne')

# Optional autorefresh to keep the live clock ticking every 10 seconds
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=10000, key="live_clock_sync")
except Exception:
    pass

# --- 2. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Smart HVAC Monitoring Dashboard",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS: Hide sidebar completely and style merged header + KPI cards
st.markdown("""
<style>
    /* Hide the left sidebar completely to merge space into the main canvas */
    [data-testid="stSidebar"], [data-testid="collapsedControl"] {
        display: none !important;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 95%;
    }

    /* Top Live Clock Card */
    .clock-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 22px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: flex-end;
    }
    .clock-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        font-weight: 700;
        color: #0f172a;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .pulse-dot {
        width: 10px;
        height: 10px;
        background-color: #ef4444;
        border-radius: 50%;
        box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.2);
    }
    .clock-date {
        font-size: 14px;
        color: #64748b;
        font-weight: 500;
        margin-bottom: 2px;
    }
    .clock-time {
        font-size: 28px;
        font-weight: 800;
        color: #dc2626;
        line-height: 1.1;
    }
    .clock-tz {
        font-size: 14px;
        color: #94a3b8;
        font-weight: 600;
        margin-left: 4px;
    }

    /* KPI Cards */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 22px 18px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-title {
        color: #64748b;
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 10px;
    }
    .metric-value {
        color: #0f172a;
        font-size: 34px;
        font-weight: 800;
        line-height: 1.1;
    }
    .metric-subtext {
        color: #7c3aed;
        font-size: 15px;
        font-weight: 600;
        margin-top: 8px;
    }
    .status-on {
        color: #16a34a;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
    }
    .status-off {
        color: #64748b;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
    }
    .circle-indicator {
        width: 22px;
        height: 22px;
        border-radius: 50%;
        display: inline-block;
    }
    .circle-on {
        background: radial-gradient(circle at 30% 30%, #4ade80, #16a34a);
        box-shadow: 0 0 10px rgba(34, 197, 94, 0.5);
    }
    .circle-off {
        background: radial-gradient(circle at 30% 30%, #cbd5e1, #94a3b8);
    }
</style>
""", unsafe_allow_html=True)

# --- 3. DATA LOADING ---
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

    # Column mappings
    df['occ_true'] = df['occupancy_now']
    df['occ_pred'] = df['occupancy_forecast_15min']
    df['T_pred'] = df['predictive_room_temperature_C']
    df['power_pred'] = df['predictive_hvac_power_kW']
    
    # Calculate interval energy from cumulative totals
    df['energy_interval_pred'] = df['predictive_energy_cumulative_kWh'].diff().fillna(0).clip(lower=0)
    
    return df

df_full = load_data()
unique_dates = df_full.index.normalize().unique().date

# --- 4. REAL-TIME CLOCK SYNC (MELBOURNE TIME) ---
now_melbourne = datetime.now(melbourne_tz)
live_time = now_melbourne.time()
live_time_str = now_melbourne.strftime('%H:%M:%S')
tz_abbr = now_melbourne.strftime('%Z')

# Choose operational date from dataset (defaults to current date if present, or first available)
if now_melbourne.date() in unique_dates:
    selected_day = now_melbourne.date()
else:
    selected_day = unique_dates[0] if len(unique_dates) > 0 else date.today()

df_day = df_full[df_full.index.date == selected_day]

# Live data stream filtered up to current time
df_live = df_day[df_day.index.time <= live_time]
if df_live.empty:
    df_live = df_day.head(1)

# --- 5. CURRENT METRICS ---
if not df_live.empty:
    current_temp = df_live['T_pred'].iloc[-1]
    current_power = df_live['power_pred'].iloc[-1]
    current_occ = int(df_live['occ_true'].iloc[-1])
    forecast_occ = int(df_live['occ_pred'].iloc[-1])
    total_energy_today = df_live['energy_interval_pred'].sum()

    if current_power > 0.05:
        hvac_status_html = "<div class='status-on'><span class='circle-indicator circle-on'></span> RUNNING</div>"
    else:
        hvac_status_html = "<div class='status-off'><span class='circle-indicator circle-off'></span> STANDBY</div>"
else:
    current_temp, current_power, current_occ, forecast_occ, total_energy_today = 0, 0, 0, 0, 0
    hvac_status_html = "<div class='status-off'><span class='circle-indicator circle-off'></span> OFFLINE</div>"

# --- 6. MERGED DASHBOARD HEADER (CLOCK EMBEDDED) ---
col_head_left, col_head_right = st.columns([3, 1.4], gap="medium")

with col_head_left:
    st.markdown("""
    <div style="padding-top: 6px;">
        <h1 style="font-size: 32px; font-weight: 800; color: #0f172a; margin: 0 0 6px 0;">
            🏢 Smart HVAC Monitoring Dashboard
        </h1>
        <p style="color: #64748b; font-size: 15px; margin: 0;">
            Real-time monitoring of facility environmental conditions, equipment status, and energy usage.
        </p>
    </div>
    """, unsafe_allow_html=True)

with col_head_right:
    # Merged Live Clock card directly inside the main dashboard view
    date_display_str = selected_day.strftime('%A, %b %d, %Y')
    st.markdown(f"""
    <div class="clock-card">
        <div class="clock-badge">
            <span class="pulse-dot"></span> LIVE SYSTEM CLOCK
        </div>
        <div class="clock-date">{date_display_str}</div>
        <div class="clock-time">
            {live_time_str} <span class="clock-tz">{tz_abbr}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

# --- 7. TOP ROW: KPI METRIC CARDS ---
col1, col2, col3, col4 = st.columns(4, gap="medium")

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
        <div class="metric-value">{current_occ} <span style="font-size: 16px; font-weight: normal; color: #64748b;">Now</span></div>
        <div class="metric-subtext">📈 Forecast (15m): {forecast_occ}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)

# --- 8. TELEMETRY CHARTS ---
def create_clean_plot(data, y_col, title, y_label, color, is_area=False, is_step=False, hlines=None):
    fig = go.Figure()
    
    if not data.empty:
        if is_area:
            r = int(color.lstrip("#")[0:2], 16)
            g = int(color.lstrip("#")[2:4], 16)
            b = int(color.lstrip("#")[4:6], 16)
            fill_color = f'rgba({r}, {g}, {b}, 0.12)'
            fig.add_trace(go.Scatter(
                x=data.index, y=data[y_col], mode='lines',
                line=dict(color=color, width=2.5),
                fill='tozeroy', fillcolor=fill_color, name=y_label
            ))
        elif is_step:
            fig.add_trace(go.Scatter(
                x=data.index, y=data[y_col], mode='lines',
                line=dict(color=color, width=2.5), line_shape='hv', name=y_label
            ))
        else:
            fig.add_trace(go.Scatter(
                x=data.index, y=data[y_col], mode='lines',
                line=dict(color=color, width=2.5), name=y_label
            ))

    if hlines:
        for hline in hlines:
            fig.add_hline(y=hline, line_dash="dash", line_color="#ef4444", opacity=0.5)

    # Current live timestamp marker line
    current_dt = datetime.combine(selected_day, live_time)
    fig.add_vline(
        x=current_dt, line_width=2, line_dash="solid", line_color="#dc2626",
        annotation_text="LIVE", annotation_position="top right",
        annotation_font=dict(color="#dc2626", size=11, weight="bold")
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#1e293b", family="sans-serif")),
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="", yaxis_title=y_label,
        hovermode="x unified",
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        xaxis=dict(
            showgrid=True, gridcolor="#f1f5f9",
            range=[datetime.combine(selected_day, time.min), datetime.combine(selected_day, time.max)]
        ),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

# Temperature chart (Full Width)
st.subheader("🌡️ Temperature Profile")
fig_temp = create_clean_plot(df_live, 'T_pred', "Indoor Temperature Tracking", "Temperature (°C)", "#2563eb", hlines=[22.8, 25.8])
fig_temp.add_hrect(
    y0=22.8, y1=25.8, line_width=0, fillcolor="#22c55e", opacity=0.1,
    annotation_text="Comfort Zone (22.8 - 25.8 °C)", annotation_position="top left",
    annotation_font=dict(color="#15803d", size=12)
)
st.plotly_chart(fig_temp, use_container_width=True)

# Energy and Occupancy row
col_c1, col_c2 = st.columns(2, gap="medium")

with col_c1:
    st.subheader("⚡ Energy Usage")
    fig_energy = create_clean_plot(df_live, 'power_pred', "HVAC Power Draw (Demand)", "Power (kW)", "#f97316", is_area=True)
    st.plotly_chart(fig_energy, use_container_width=True)

with col_c2:
    st.subheader("👥 Occupancy")
    fig_occ = create_clean_plot(df_live, 'occ_pred', "Occupancy Forecast vs Actual", "People", "#7c3aed", is_step=True)
    if not df_live.empty:
        fig_occ.add_trace(go.Scatter(
            x=df_live.index, y=df_live['occ_true'], mode='lines',
            line=dict(color="#64748b", width=2, dash="dot"),
            line_shape='hv', name="Actual Now"
        ))
    st.plotly_chart(fig_occ, use_container_width=True)