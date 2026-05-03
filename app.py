import streamlit as st
import time
from datetime import date, timedelta

# CONFIG
APP_TITLE = "Tech Trend Research - An AI Augmentation"
APP_ICON = "🤖"
PAGE_TITLE = "Retail Trends AI"

WORKFLOW_STEPS = [
    {"id": 1, "name": "Research", "icon": "🔍", "description": "Web search using Tavily API", "duration_seconds": 5},
    {"id": 2, "name": "Pulse Ledger", "icon": "📊", "description": "Extract 100 unique pulses", "duration_seconds": 5},
    {"id": 3, "name": "Whisper Tags", "icon": "🏷️", "description": "Cluster pulses into tags", "duration_seconds": 5},
    {"id": 4, "name": "Macro Trend Map", "icon": "🎯", "description": "Form 6 macro trends", "duration_seconds": 5},
    {"id": 5, "name": "CIPHER Map", "icon": "🔐", "description": "CIPHER regrouping", "duration_seconds": 5},
    {"id": 6, "name": "Attribute Map", "icon": "🗂️", "description": "Attribute regrouping", "duration_seconds": 5},
    {"id": 7, "name": "Tech Trends", "icon": "💻", "description": "Extract tech trends", "duration_seconds": 5},
    {"id": 8, "name": "Output", "icon": "📄", "description": "Generate reports", "duration_seconds": 5}
]

COLORS = {"primary": "#4F46E5", "success": "#10B981", "text_primary": "#111827", "text_secondary": "#6B7280"}
DISPLAY_TOTAL_TIME = "1h 57m"
DISPLAY_TOTAL_SECONDS = 7020
REAL_TOTAL_TIME = 40

st.set_page_config(page_title=PAGE_TITLE, page_icon=APP_ICON, layout="wide")

if 'screen' not in st.session_state:
    st.session_state.screen = 'input'
    st.session_state.current_step = 0
    st.session_state.progress = 0

# SIDEBAR
with st.sidebar:
    st.markdown(f"### {APP_ICON} {APP_TITLE}")
    st.markdown("---")
    for idx, step in enumerate(WORKFLOW_STEPS):
        icon = '✅' if st.session_state.screen == 'results' or (st.session_state.screen == 'processing' and idx < st.session_state.current_step) else ('⏳' if st.session_state.screen == 'processing' and idx == st.session_state.current_step else '⏸️')
        with st.expander(f"{icon} {step['icon']} {step['name']}"):
            st.write(step['description'])

# INPUT SCREEN
if st.session_state.screen == 'input':
    st.title("Configure Your Analysis")
    country = st.text_input("🌍 Country")
    retailers = st.text_area("🏬 Retailers (one per line)", height=150)
    col1, col2 = st.columns(2)
    date_start = col1.date_input("📅 Start Date", value=date.today() - timedelta(days=180))
    date_end = col2.date_input("📅 End Date", value=date.today())
    
    if st.button("🚀 Start Analysis", type="primary"):
        if country and retailers:
            st.session_state.country = country
            st.session_state.screen = 'processing'
            st.rerun()

# PROCESSING SCREEN
elif st.session_state.screen == 'processing':
    status = st.empty()
    timer = st.empty()
    prog = st.empty()
    
    for step_idx, step in enumerate(WORKFLOW_STEPS):
        st.session_state.current_step = step_idx
        status.markdown(f"<h2 style='text-align:center'>🤖 Agent is Thinking...</h2><h3 style='text-align:center'>{step['icon']} {step['name']}</h3>", unsafe_allow_html=True)
        
        for i in range(11):
            progress = ((step_idx + i/10) / len(WORKFLOW_STEPS)) * 100
            elapsed = int((step_idx * 5 + i * 0.5) * (DISPLAY_TOTAL_SECONDS / REAL_TOTAL_TIME))
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            timer.markdown(f"<h1 style='text-align:center; color:{COLORS['primary']}'>{h:01d}:{m:02d}:{s:02d}</h1>", unsafe_allow_html=True)
            prog.progress(progress / 100)
            time.sleep(0.5)
    
    st.session_state.screen = 'results'
    st.rerun()

# RESULTS SCREEN
elif st.session_state.screen == 'results':
    st.title("Analysis Results")
    st.success(f"✅ Analysis Complete! ⏱️ Time Taken: {DISPLAY_TOTAL_TIME}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 Pulses", 100)
    col2.metric("🏷️ Whisper Tags", 24)
    col3.metric("🎯 Macro Trends", 6)
    col4.metric("💻 Tech Trends", 8)
    
    st.markdown("---")
    st.markdown("### 📥 Download Reports")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("📥 Download Excel Report", type="primary", use_container_width=True):
            st.info("📥 Download functionality is disabled in demo mode")
    
    with col_btn2:
        if st.button("📄 Download Analysis Document", type="primary", use_container_width=True):
            st.info("📥 Download functionality is disabled in demo mode")
    
    st.markdown("---")
    
    if st.button("🔄 Start New Analysis", use_container_width=True):
        st.session_state.screen = 'input'
        st.rerun()