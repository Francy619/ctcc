import streamlit as st
import os
import zipfile
import shutil
import streamlit.components.v1 as components

# Import only the 6 active modules
from modules import interaction, led, nbo, qtaim, structural, cvb

# --- AUTO-EXTRACT MULTIWFN ---
if not os.path.exists("Multiwfn") and os.path.exists("Multiwfn.zip"):
    with zipfile.ZipFile("Multiwfn.zip", 'r') as zip_ref:
        zip_ref.extractall(".")
    for root, dirs, files in os.walk("."):
        if "Multiwfn" in files:
            file_path = os.path.join(root, "Multiwfn")
            if os.path.abspath(file_path) != os.path.abspath("Multiwfn"):
                shutil.move(file_path, "Multiwfn")
            break
    if os.path.exists("Multiwfn"):
        os.chmod("Multiwfn", 0o755)

st.set_page_config(page_title="CTCC Dashboard", layout="wide", initial_sidebar_state="collapsed")

if 'app_mode' not in st.session_state: 
    st.session_state.app_mode = "Home"

# ---------------------------------------------------------
# GLOBAL MODERN CSS
# ---------------------------------------------------------
st.markdown("""
<style>
    /* Hide default Streamlit elements */
    footer, [data-testid="stFooter"], .stStatusWidget { display: none !important; visibility: hidden !important; height: 0px !important; }
    button[title="View fullscreen"] { display: none !important; }
    header { visibility: hidden !important; display: none !important; }
    [data-testid="collapsedControl"] { display: none; }
    
    /* Global Background & Typography */
    .stApp {
        background-color: #F8FAFC;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Module Header Styling */
    .main-header-container { 
        text-align: center; 
        margin-bottom: 2.5rem; 
        padding-bottom: 1.5rem; 
        border-bottom: 1px solid #E2E8F0; 
    }
    .main-title { 
        font-size: 2.8rem; 
        color: #0F172A; 
        font-weight: 800; 
        letter-spacing: -0.02em;
        margin-bottom: 8px; 
    }
    .sub-title { 
        font-size: 1.15rem; 
        color: #64748B; 
        font-weight: 400;
    }
    .section-header { 
        font-size: 1.25rem; 
        color: #1E293B; 
        font-weight: 700; 
        margin-bottom: 12px; 
    }
    
    /* Buttons (Primary & Secondary) */
    button[kind="primary"] { 
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important; 
        color: #FFFFFF !important; 
        border: none !important; 
        border-radius: 8px !important; 
        font-weight: 600 !important; 
        padding: 10px 20px !important; 
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2), 0 2px 4px -1px rgba(37, 99, 235, 0.1) !important;
        transition: all 0.2s ease !important;
    }
    button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3), 0 4px 6px -2px rgba(37, 99, 235, 0.15) !important;
    }
    
    /* File Uploader styling */
    [data-testid="stFileUploaderDropzone"] {
        border: 2px dashed #CBD5E1 !important;
        border-radius: 12px !important;
        background-color: #FFFFFF !important;
        transition: border-color 0.2s ease !important;
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        border-color: #3B82F6 !important;
    }
    [data-testid="stFileUploaderDropzone"] > div { 
        display: flex !important; 
        flex-direction: row !important; 
        align-items: center !important; 
        flex-wrap: nowrap !important; 
        gap: 12px !important; 
        padding: 15px !important; 
    }
    [data-testid="stFileUploaderDropzone"] small { 
        white-space: nowrap !important; 
        margin-top: 0 !important; 
        font-size: 0.9rem !important; 
        color: #64748B !important;
    }
    
    /* Standard UI Containers */
    [data-testid="stVerticalBlockBorderWrapper"] > div {
        border: 1px solid #E2E8F0 !important;
        border-radius: 16px !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05) !important;
        padding: 1.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# ROUTER LOGIC
# ---------------------------------------------------------
if st.session_state.app_mode == "Home":
    st.markdown("""
    <style>
        .menu-title { 
            font-size: 3.8rem; 
            font-weight: 800; 
            color: #0F172A; 
            text-align: center; 
            margin-top: 40px; 
            margin-bottom: 50px; 
            letter-spacing: -0.03em;
            line-height: 1.15; 
        }
        .menu-title span { color: #2563EB; }
        
        .footer-text { 
            text-align: center; 
            color: #64748B; 
            font-size: 0.95rem; 
            line-height: 1.6;
            margin-top: 100px; 
            border-top: 1px solid #E2E8F0; 
            padding-top: 40px;
        }
        
        /* Modern Home Screen Buttons */
        button[kind="secondary"] { 
            background-color: #FFFFFF !important; 
            color: #1E293B !important; 
            font-size: 1.25rem !important; 
            font-weight: 600 !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 16px !important;
            min-height: 120px !important; 
            padding: 20px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
        button[kind="secondary"]:hover {
            border-color: #93C5FD !important;
            transform: translateY(-4px) !important;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;
            color: #2563EB !important;
        }
    </style>
    """, unsafe_allow_html=True)
        
    st.markdown('<p class="menu-title">CompChem <span>Data Extraction Suite</span></p>', unsafe_allow_html=True)
    st.write("")
    
    # 3 centered columns for 6 modules
    c_space_l, c_btn_1, c_btn_2, c_btn_3, c_space_r = st.columns([1, 4, 4, 4, 1])
    
    with c_btn_1:
        if st.button("🔬 Interaction Energy", use_container_width=True, type="secondary"): st.session_state.app_mode = "Interaction Energy"; st.rerun()
        st.write("")
        if st.button("⚛️ NBO E(2) Analysis", use_container_width=True, type="secondary"): st.session_state.app_mode = "NBO E(2) Analysis"; st.rerun()
    with c_btn_2:
        if st.button("📊 LED Parser", use_container_width=True, type="secondary"): st.session_state.app_mode = "LED Analysis"; st.rerun()
        st.write("")
        if st.button("📏 Vibrational Data", use_container_width=True, type="secondary"): st.session_state.app_mode = "Structural Analysis"; st.rerun()
    with c_btn_3:
        if st.button("⭕ QTAIM Properties", use_container_width=True, type="secondary"): st.session_state.app_mode = "QTAIM Analysis"; st.rerun()
        st.write("")
        if st.button("📈 CVB Index", use_container_width=True, type="secondary"): st.session_state.app_mode = "CVB Index"; st.rerun()
            
    st.markdown("""
        <div class="footer-text">
            <strong>Developed by:</strong> Francis Thomas & Dr. Renjith Thomas <br> 
            <strong>Research Group:</strong> Centre for Theoretical and Computational Chemistry (CTCC) <br> 
            <strong>Institutions:</strong> St. Dominic's College, Kanjirapally & St. Berchmans College, Changanassery <br><br>
            Automated tools for parsing outputs from Gaussian, ORCA, and Multiwfn.
        </div>
    """, unsafe_allow_html=True)

# Call the correct module based on the state
elif st.session_state.app_mode == "Interaction Energy": interaction.render()
elif st.session_state.app_mode == "LED Analysis": led.render()
elif st.session_state.app_mode == "NBO E(2) Analysis": nbo.render()
elif st.session_state.app_mode == "QTAIM Analysis": qtaim.render()
elif st.session_state.app_mode == "Structural Analysis": structural.render()
elif st.session_state.app_mode == "CVB Index": cvb.render()
