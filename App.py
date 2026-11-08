import streamlit as st
import os
import zipfile
import shutil
import streamlit.components.v1 as components

# Import all custom modules including the new NCI module
from modules import interaction, led, nbo, qtaim, structural, cvb, nci

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

st.set_page_config(page_title="Computational Chemistry Dashboard", layout="wide", initial_sidebar_state="collapsed")

if 'app_mode' not in st.session_state: 
    st.session_state.app_mode = "Home"

# GLOBAL CSS
st.markdown("""
<style>
    footer, [data-testid="stFooter"], .stStatusWidget { display: none !important; visibility: hidden !important; height: 0px !important; max-height: 0px !important; }
    button[title="View fullscreen"] { display: none !important; }
    header { visibility: hidden !important; display: none !important; }
    [data-testid="collapsedControl"] { display: none; }
    .main-header-container { text-align: center; margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 2px solid #E2E8F0; }
    .main-title { font-size: 3.2rem; color: #1E3A8A; font-weight: 800; margin-bottom: 5px; font-family: 'Segoe UI', sans-serif; }
    .sub-title { font-size: 1.1rem; color: #4B5563; font-family: 'Segoe UI', sans-serif; }
    .section-header { font-size: 1.1rem; color: #1E3A8A; font-weight: 700; margin-bottom: 10px; }
    button[kind="primary"] { background-color: #1E3A8A !important; color: #FFFFFF !important; border: none !important; border-radius: 6px !important; font-weight: 700 !important; padding: 8px 16px !important; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important; }
    button[kind="secondary"] { border-radius: 6px !important; font-weight: 600 !important; }
    [data-testid="stFileUploaderDropzone"] > div { display: flex !important; flex-direction: row !important; align-items: center !important; flex-wrap: nowrap !important; gap: 10px !important; padding: 10px !important; }
    [data-testid="stFileUploaderDropzone"] small { white-space: nowrap !important; margin-top: 0 !important; font-size: 0.85rem !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# ROUTER LOGIC
# ---------------------------------------------------------
if st.session_state.app_mode == "Home":
    st.markdown("""
    <style>
        .menu-title { font-size: 4.8rem; font-weight: 600; color: #1E3A8A; text-align: center; margin-top: 20px; margin-bottom: 40px; font-family: 'Inter', 'Roboto', 'Helvetica Neue', sans-serif; line-height: 1.1; }
        .footer-text { text-align: center; color: #64748B; font-size: 1rem; margin-top: 80px; border-top: 1px solid #E2E8F0; padding-top: 30px;}
        [data-testid="stAppViewContainer"] { overflow-y: hidden !important; }
        button[kind="secondary"] { background-color: #1E3A8A !important; color: #FFFFFF !important; font-size: 2.1rem !important; min-height: 100px !important; padding: 25px 15px !important; }
    </style>
    """, unsafe_allow_html=True)
        
    st.markdown('<p class="menu-title">CompChem Data Extraction Suite</p>', unsafe_allow_html=True)
    st.write("")
    
    # Updated to 4 buttons per row to fit the NCI module!
    c_btn_1, c_btn_2, c_btn_3, c_btn_4 = st.columns([1, 1, 1, 1])
    
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
    with c_btn_4:
        if st.button("🌌 NCI & RDG Plots", use_container_width=True, type="secondary"): st.session_state.app_mode = "NCI Analysis"; st.rerun()
            
    st.markdown("""<div class="footer-text"><strong>Developed by:</strong> Francis Thomas & Dr. Renjith Thomas <br> Automated tools for parsing outputs.</div>""", unsafe_allow_html=True)

# Call the correct module based on the state
elif st.session_state.app_mode == "Interaction Energy": interaction.render()
elif st.session_state.app_mode == "LED Analysis": led.render()
elif st.session_state.app_mode == "NBO E(2) Analysis": nbo.render()
elif st.session_state.app_mode == "QTAIM Analysis": qtaim.render()
elif st.session_state.app_mode == "Structural Analysis": structural.render()
elif st.session_state.app_mode == "CVB Index": cvb.render()
elif st.session_state.app_mode == "NCI Analysis": nci.render()
import streamlit as st
import os
import zipfile
import shutil
import streamlit.components.v1 as components

# Import your custom modules (we will create these next)
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

st.set_page_config(page_title="Computational Chemistry Dashboard", layout="wide", initial_sidebar_state="collapsed")

if 'app_mode' not in st.session_state: 
    st.session_state.app_mode = "Home"

# GLOBAL CSS
st.markdown("""
<style>
    footer, [data-testid="stFooter"], .stStatusWidget { display: none !important; visibility: hidden !important; height: 0px !important; max-height: 0px !important; }
    button[title="View fullscreen"] { display: none !important; }
    header { visibility: hidden !important; display: none !important; }
    [data-testid="collapsedControl"] { display: none; }
    .main-header-container { text-align: center; margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 2px solid #E2E8F0; }
    .main-title { font-size: 3.2rem; color: #1E3A8A; font-weight: 800; margin-bottom: 5px; font-family: 'Segoe UI', sans-serif; }
    .sub-title { font-size: 1.1rem; color: #4B5563; font-family: 'Segoe UI', sans-serif; }
    .section-header { font-size: 1.1rem; color: #1E3A8A; font-weight: 700; margin-bottom: 10px; }
    button[kind="primary"] { background-color: #1E3A8A !important; color: #FFFFFF !important; border: none !important; border-radius: 6px !important; font-weight: 700 !important; padding: 8px 16px !important; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important; }
    button[kind="secondary"] { border-radius: 6px !important; font-weight: 600 !important; }
    [data-testid="stFileUploaderDropzone"] > div { display: flex !important; flex-direction: row !important; align-items: center !important; flex-wrap: nowrap !important; gap: 10px !important; padding: 10px !important; }
    [data-testid="stFileUploaderDropzone"] small { white-space: nowrap !important; margin-top: 0 !important; font-size: 0.85rem !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# ROUTER LOGIC
# ---------------------------------------------------------
if st.session_state.app_mode == "Home":
    st.markdown("""
    <style>
        .menu-title { font-size: 4.8rem; font-weight: 600; color: #1E3A8A; text-align: center; margin-top: 20px; margin-bottom: 40px; font-family: 'Inter', 'Roboto', 'Helvetica Neue', sans-serif; line-height: 1.1; }
        .footer-text { text-align: center; color: #64748B; font-size: 1rem; margin-top: 80px; border-top: 1px solid #E2E8F0; padding-top: 30px;}
        [data-testid="stAppViewContainer"] { overflow-y: hidden !important; }
        button[kind="secondary"] { background-color: #1E3A8A !important; color: #FFFFFF !important; font-size: 2.4rem !important; min-height: 100px !important; padding: 30px 20px !important; }
    </style>
    """, unsafe_allow_html=True)
        
    st.markdown('<p class="menu-title">CompChem Data Extraction Suite</p>', unsafe_allow_html=True)
    st.write("")
    
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
        if st.button("📈 CVB Index (Multiwfn)", use_container_width=True, type="secondary"): st.session_state.app_mode = "CVB Index"; st.rerun()
            
    st.markdown("""<div class="footer-text"><strong>Developed by:</strong> Francis Thomas & Dr. Renjith Thomas <br> Automated tools for parsing outputs.</div>""", unsafe_allow_html=True)

# Call the correct module based on the state
elif st.session_state.app_mode == "Interaction Energy": interaction.render()
elif st.session_state.app_mode == "LED Analysis": led.render()
elif st.session_state.app_mode == "NBO E(2) Analysis": nbo.render()
elif st.session_state.app_mode == "QTAIM Analysis": qtaim.render()
elif st.session_state.app_mode == "Structural Analysis": structural.render()
elif st.session_state.app_mode == "CVB Index": cvb.render()
