import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import datetime, date, time, timezone, timedelta

# Auto-refresh helper (fails gracefully if module is not installed)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30000, key="data_refresh")
except Exception:
    pass

# --- 1. PAGE CONFIGURATION & DARK-BLUE STYLING ---
st.set_page_config(
    page_title="HVAC Monitoring Dashboard based on Occupancy Prediction", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Dark-Blue Theme Custom CSS
st.markdown("""
<style>
    /* Dark-blue application background */
    .stApp {
        background-color: #0a1128 !important;
        color: #f1f5f9 !important;
    }
    
    /* Completely hide the sidebar */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 96%;
    }
    
    /* Dark-blue Metric Cards */
    .metric-card {
        background-color: #121e3a;
        border: 1px solid #1e325c;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-title { 
        color: #94a3b8; 
        font-size: 13px; 
        font-weight: 700; 
        text-transform: uppercase; 
        letter-spacing: 0.8px;
        margin-bottom: 8px; 
    }
    .metric-value { 
        color: #ffffff; 
        font-size: 32px; 
        font-weight: bold; 
    }
    .metric-subtext { 
        color: #38bdf8; 
        font-size: 15px; 
        font-weight: 600; 
        margin-top: 6px; 
    }
    
    /* Header Clock Banner Card */
    .clock-card {
        background-color: #121e3a;
        border: 1px solid #1e325c;
        border-radius: 12px;
        padding: 14px 22px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    }
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-weight: 700;
        font-size: 26px;
    }
    .circle-indicator { 
        width: 20px; 
        height: 20px; 
        border-radius: 50%; 
        display: inline-block;
    }
    .circle-on { 
        background: radial-gradient(circle at 30% 30%, #4ade80, #16a34a); 
        box-shadow: 0 0 12px rgba(74, 222, 128, 0.6); 
    }
    .circle-off { 
        background: radial-gradient(circle at 30% 30%, #94a3b8, #475569); 
    }
    
    /* Headers & Text color overrides */
    h1, h2, h3, h4, p {
        color: #ffffff !important;
    }
    .sub-description {
        color: #94a3b8 !important;
        font-size: 15px;
        margin-top: -8px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. AUTOMATIC LOOPING SCROLLER SCRIPT ---
components.html("""
<script>
    const parentWin = window.parent;
    let scrollSpeed = 1;      // Pixels per step (adjust speed here)
    let intervalTime = 30;    // Milliseconds per step
    let isPaused = false;

    function autoScroll() {
        if (!isPaused && parentWin) {
            let maxScroll = parentWin.document.documentElement.scrollHeight - parentWin.innerHeight;
            let currentScroll = parentWin.scrollY || parentWin.pageYOffset;

            // When reaching or nearing bottom, pause and smoothly reset to top
            if (currentScroll >= maxScroll - 2) {
                isPaused = true;
                setTimeout(() => {
                    parentWin.scrollTo({ top: 0, behavior: 'smooth' });
                    setTimeout(() => {
                        isPaused = false;
                    }, 2500); // 2.5s pause at the top before starting next loop
                }, 2000);     // 2.0s pause at the bottom
            } else {
                parentWin.scrollBy(0, scrollSpeed);
            }
        }
    }

    // Initialize auto scroll interval
    setInterval(autoScroll, intervalTime);
</script>
""", height=0, width=0)

# --- 3. DATA LOADING & 29 SEPTEMBER 2026 MAPPING ---
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

# Target date set to 29 September 2026
target_date = date(2026, 9, 29)

# Filter dataset for September 29 and map timestamp year to 2026
df_sep29 = df_full[(df_full.index.month == 9) & (df_full.index.day == 29)].copy()

if not df_sep29.empty:
    df_day = df_sep29
    df_day.index = df_day.index.map(lambda dt: dt.replace(year=2026))
else:
    # Fallback to first available date
    first_date = df_full.index.date[0]
    df_day = df_full[df_full.index.date == first_date].copy()
    df_day.index = df_day.index.map(lambda dt: dt.replace(year=2026, month=9, day=29))

# --- 4. LIVE MELBOURNE TIME TRACKING ---
try:
    import pytz
    melbourne_tz = pytz.timezone('Australia/Melbourne')
    now_melbourne = datetime.now(melbourne_tz)
except Exception:
    melbourne_tz = timezone(timedelta(hours=10))
    now_melbourne = datetime.now(melbourne_tz)

live_time = now_melbourne.time()

# Filter data dynamically up to current Melbourne live time
df_live = df_day[df_day.index.time <= live_time]
if df_live.empty:
    df_live = df_day.iloc[:1]

# --- 5. CURRENT METRIC VALUES ---
current_temp = df_live['T_pred'].iloc[-1]
current_power = df_live['power_pred'].iloc[-1]
current_occ = int(df_live['occ_true'].iloc[-1])
forecast_occ = int(df_live['occ_pred'].iloc[-1])
total_energy_today = df_live['energy_interval_pred'].sum()

if current_power > 0:
    hvac_status_html = "<span class='status-badge' style='color: #4ade80;'><span class='circle-indicator circle-on'></span> RUNNING</span>"
else:
    hvac_status_html = "<span class='status-badge' style='color: #94a3b8;'><span class='circle-indicator circle-off'></span> STANDBY</span>"

# --- 6. HEADER (TITLE WITH OCCUPANCY PREDICTION + CLOCK BANNER) ---
col_head_left, col_head_right = st.columns([2.3, 1.1])

with col_head_left:
    st.title("🏢 Smart HVAC Monitoring Dashboard based on Occupancy Prediction")
    st.markdown("<div class='sub-description'>Real-time facility environmental monitoring, equipment control state, and predictive demand tracking.</div>", unsafe_allow_html=True)

with col_head_right:
    st.markdown(f"""
    <div class="clock-card">
        <div>
            <div style="font-size: 11px; font-weight: bold; color: #f87171; display: flex; align-items: center; gap: 6px; letter-spacing: 0.5px;">
                <span style="height: 8px; width: 8px; background-color: #ef4444; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px #ef4444;"></span>
                LIVE SYSTEM CLOCK
            </div>
            <div style="font-size: 15px; font-weight: 600; color: #e2e8f0; margin-top: 3px;">
                {target_date.strftime('%A, %b %d, %Y')}
            </div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 600;">MELBOURNE TIME</div>
            <div style="font-size: 26px; font-weight: bold; color: #38bdf8; line-height: 1.1;">
                {live_time.strftime('%H:%M:%S')}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- 7. TOP KPI CARDS ---
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
        <div class="metric-value">{current_occ} <span style="font-size: 16px; font-weight: normal; color: #94a3b8;">Now</span></div>
        <div class="metric-subtext">📈 Forecast (15m): {forecast_occ}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- 8. CHARTS WITH DARK BLUE THEME ---
def create_dark_blue_plot(data, y_col, title, y_label, line_color, is_area=False, is_step=False, hlines=None):
    fig = go.Figure()
    
    if not data.empty:
        if is_area:
            r = int(line_color.lstrip("#")[0:2], 16)
            g = int(line_color.lstrip("#")[2:4], 16)
            b = int(line_color.lstrip("#")[4:6], 16)
            fill_color = f'rgba({r}, {g}, {b}, 0.2)'
            fig.add_trace(go.Scatter(
                x=data.index, y=data[y_col], 
                mode='lines', 
                line=dict(color=line_color, width=2.5), 
                fill='tozeroy', 
                fillcolor=fill_color, 
                name=y_label
            ))
        elif is_step:
            fig.add_trace(go.Scatter(
                x=data.index, y=data[y_col], 
                mode='lines', 
                line=dict(color=line_color, width=2.5), 
                line_shape='hv', 
                name=y_label
            ))
        else:
            fig.add_trace(go.Scatter(
                x=data.index, y=data[y_col], 
                mode='lines', 
                line=dict(color=line_color, width=2.5), 
                name=y_label
            ))
    
    if hlines:
        for hline in hlines:
            fig.add_hline(y=hline, line_dash="dash", line_color="#ef4444", opacity=0.7)

    # Red vertical marker tracking current Melbourne live time
    live_marker_dt = datetime.combine(target_date, live_time)
    fig.add_vline(
        x=live_marker_dt, 
        line_width=2, 
        line_dash="solid", 
        line_color="#ef4444", 
        annotation_text="LIVE", 
        annotation_position="top right",
        annotation_font_color="#ef4444"
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#f1f5f9")),
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="", 
        yaxis_title=y_label,
        hovermode="x unified",
        plot_bgcolor="#121e3a", 
        paper_bgcolor="#121e3a",
        font=dict(color="#94a3b8"),
        xaxis=dict(
            showgrid=True, 
            gridcolor="#1e325c", 
            zeroline=False,
            range=[datetime.combine(target_date, time.min), datetime.combine(target_date, time.max)]
        ),
        yaxis=dict(showgrid=True, gridcolor="#1e325c", zeroline=False),
        legend=dict(font=dict(color="#f1f5f9"))
    )
    return fig

# Temperature Chart
st.subheader("🌡️ Temperature Profile")
fig_temp = create_dark_blue_plot(df_live, 'T_pred', "Indoor Temperature Tracking", "Temperature (°C)", "#38bdf8", hlines=[22.8, 25.8])
fig_temp.add_hrect(
    y0=22.8, y1=25.8, 
    line_width=0, 
    fillcolor="#22c55e", 
    opacity=0.15, 
    annotation_text="Comfort Band (22.8 - 25.8°C)", 
    annotation_position="top left",
    annotation_font_color="#4ade80"
)
st.plotly_chart(fig_temp, use_container_width=True)

# Energy and Occupancy Charts
col_c1, col_c2 = st.columns(2)

with col_c1:
    st.subheader("⚡ Energy Usage")
    fig_energy = create_dark_blue_plot(df_live, 'power_pred', "HVAC Power Draw (Demand)", "Power (kW)", "#fb923c", is_area=True)
    st.plotly_chart(fig_energy, use_container_width=True)

with col_c2:
    st.subheader("👥 Occupancy Demand")
    fig_occ = create_dark_blue_plot(df_live, 'occ_pred', "Predicted Occupancy (15m Horizon)", "People", "#a855f7", is_step=True)
    if not df_live.empty:
        fig_occ.add_trace(go.Scatter(
            x=df_live.index, 
            y=df_live['occ_true'], 
            mode='lines', 
            line=dict(color="#94a3b8", width=2, dash="dot"), 
            line_shape='hv', 
            name="Actual Now"
        ))
    st.plotly_chart(fig_occ, use_container_width=True)
