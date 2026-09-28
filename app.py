import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd

# 1. Page Configuration
st.set_page_config(page_title="Digital Twin 3D Dashboard", layout="wide", initial_sidebar_state="collapsed")

# 2. Custom CSS for Cyberpunk / Dark Green UI
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #04120a;
        color: #ffffff;
    }
    
    /* Panel styling to match the image's rounded green borders */
    .glass-panel {
        background-color: rgba(10, 30, 20, 0.6);
        border: 2px solid #2eb84e;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 0 10px rgba(46, 184, 78, 0.2);
    }
    
    /* Top metrics circular styling */
    .metric-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        text-align: center;
    }
    .circle-metric {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        border: 4px solid #39ff14;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        background-color: rgba(57, 255, 20, 0.05);
        box-shadow: 0 0 15px rgba(57, 255, 20, 0.3) inset;
    }
    .circle-value { font-size: 28px; font-weight: bold; margin: 0; line-height: 1; }
    .circle-label { font-size: 12px; color: #a0c4a8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;}
    .circle-unit { font-size: 14px; color: #a0c4a8; }
    
    /* Standard text styling */
    .panel-title { font-size: 12px; color: #a0c4a8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px; font-weight: 600;}
    .main-heading { font-size: 24px; font-weight: bold; margin-bottom: 15px; color: #ffffff;}
    .predictive-text { font-size: 26px; font-weight: bold; color: #ffffff; margin: 5px 0;}
    .sub-text { font-size: 14px; color: #a0c4a8;}
    .confidence { color: #39ff14; font-size: 14px; font-weight: bold; float: right;}
    
    /* Hide Streamlit default elements */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# 3. Layout Generation
col1, col2 = st.columns([2.2, 1], gap="large")

# ==========================================
# LEFT COLUMN: 3D Spatial Heatmap
# ==========================================
with col1:
    st.markdown("""
    <div style='margin-bottom: 10px;'>
        <div class='panel-title'>WHOLE-BUILDING WIREFRAME</div>
        <div class='main-heading'>3D spatial heatmap</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Generate dummy 3D data to mimic a building wireframe and activity clusters
    np.random.seed(42)
    # Wireframe background points
    x_wire = np.random.uniform(0, 10, 500)
    y_wire = np.random.uniform(0, 3, 500)
    z_wire = np.random.uniform(0, 2, 500)
    
    # High activity clusters (dark dots in the image)
    x_clust = np.random.normal(3, 1, 50)
    y_clust = np.random.normal(1.5, 0.5, 50)
    z_clust = np.random.normal(1, 0.5, 50)

    fig_3d = go.Figure()
    
    # Add wireframe points
    fig_3d.add_trace(go.Scatter3d(
        x=x_wire, y=y_wire, z=z_wire,
        mode='markers',
        marker=dict(size=2, color='rgba(57, 255, 20, 0.3)'),
        name='Structure'
    ))
    
    # Add activity hot spots
    fig_3d.add_trace(go.Scatter3d(
        x=x_clust, y=y_clust, z=z_clust,
        mode='markers',
        marker=dict(size=8, color='#04120a', line=dict(color='#39ff14', width=2)),
        name='Activity'
    ))

    # Dark theme 3D layout styling
    fig_3d.update_layout(
        margin=dict(l=0, r=0, b=0, t=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        scene=dict(
            xaxis=dict(showbackground=False, showgrid=True, gridcolor='#144021', zeroline=False, showticklabels=False, title=''),
            yaxis=dict(showbackground=False, showgrid=True, gridcolor='#144021', zeroline=False, showticklabels=False, title=''),
            zaxis=dict(showbackground=False, showgrid=True, gridcolor='#144021', zeroline=False, showticklabels=False, title=''),
            camera=dict(eye=dict(x=1.5, y=-1.5, z=0.5))
        ),
        height=650
    )
    
    # Wrap plot in a styled container
    st.markdown("<div class='glass-panel'>", unsafe_allow_html=True)
    st.plotly_chart(fig_3d, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# RIGHT COLUMN: Metrics & Forecasts
# ==========================================
with col2:
    
    # Panel 1: Top Metrics (Gauges)
    st.markdown("""
    <div class='glass-panel' style='padding: 30px 20px;'>
        <div class='metric-container'>
            <div class='circle-metric'>
                <div class='circle-label'>TEMPERATURE</div>
                <div class='circle-value'>23.4</div>
                <div class='circle-unit'>°C</div>
            </div>
            <div class='circle-metric'>
                <div class='circle-label'>CO₂</div>
                <div class='circle-value'>838</div>
                <div class='circle-unit'>ppm</div>
            </div>
            <div style='text-align: center; margin-right: 15px;'>
                <div style='font-size: 36px; color: #ffffff;'>👥</div>
                <div class='circle-value' style='font-size: 32px;'>7</div>
                <div style='color: #ffaa00; font-weight: bold; font-size: 14px;'>Moderate</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Panel 2: Predictive Output
    st.markdown("""
    <div class='glass-panel'>
        <div class='panel-title'>MODEL OUTPUT - 30 MIN AHEAD <span class='confidence'>Medium Confidence</span></div>
        <div class='predictive-text'>Predicted CO₂ 912 <span style='font-size: 16px; font-weight: normal; color: #a0c4a8;'>ppm</span></div>
        <div class='sub-text' style='margin-top: 10px;'>Consider increasing fresh-air ventilation.</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Panel 3: Trend Chart
    st.markdown("""
    <div class='glass-panel' style='padding-bottom: 0px;'>
        <div class='panel-title'>CALENDAR-MATCHED ARCHIVE</div>
        <div class='main-heading' style='margin-bottom: 0px;'>CO₂ trend</div>
    """, unsafe_allow_html=True)
    
    # Generate line chart data
    time_x = pd.date_range("2026-09-28 08:00", periods=20, freq="15min")
    co2_y = [400, 410, 420, 450, 500, 600, 650, 620, 600, 580, 550, 560, 590, 630, 680, 750, 800, 838, 850, 840]
    
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=time_x, y=co2_y,
        mode='lines',
        line=dict(color='#39ff14', width=3),
        fill='tozeroy',
        fillcolor='rgba(57, 255, 20, 0.1)'
    ))
    
    fig_line.update_layout(
        margin=dict(l=0, r=0, b=0, t=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=180,
        xaxis=dict(showgrid=True, gridcolor='#144021', showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='#144021', showticklabels=False, zeroline=False, range=[350, 950])
    )
    
    st.plotly_chart(fig_line, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)
