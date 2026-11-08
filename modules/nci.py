import streamlit as st
import os
import subprocess
import shutil
import re

def update_multiwfn_settings(target_folder, format_choice):
    """
    Forces Multiwfn into silent mode (to prevent server crashes) 
    and dynamically changes the export graph format to ps or png.
    """
    settings_path = os.path.join(target_folder, "settings.ini")
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        content = re.sub(r'isilent\s*=\s*0', 'isilent= 1', content, flags=re.IGNORECASE)
        content = re.sub(r'graphformat\s*=\s*\w+', f'graphformat={format_choice}', content, flags=re.IGNORECASE)
        
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write(content)

def render():
    st.markdown('<div class="home-btn-container">', unsafe_allow_html=True)
    col_home, _ = st.columns([1, 6])
    with col_home:
        if st.button("🏠 Back to Home", type="secondary", key="home_nci"): 
            st.session_state.app_mode = "Home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="main-header-container"><div class="main-title">🌌 NCI & RDG Generator</div><div class="sub-title">Preview plots on-screen and instantly download publication-ready .ps files.</div></div>', unsafe_allow_html=True)
    
    if not os.path.exists("Multiwfn"):
        st.error("🚨 **Multiwfn Binary Missing:** Please ensure Multiwfn.zip is uploaded to the root of your GitHub repository.")
        st.stop()
        
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            w_file = st.file_uploader("Upload .wfn or .wfx File", type=["wfn", "wfx"], key="nci_wfn")
        with col2:
            quality = st.selectbox("Grid Quality", options=[
                ("1", "Low (Fast rendering)"), 
                ("2", "Medium (Standard)"), 
                ("3", "High (Publication quality, slower)")
            ], format_func=lambda x: x[1], index=1)
        with col3:
            plot_choice = st.radio("What to generate?", ["Scatter Plot", "NCI 3D Surface", "Both"])

    st.divider()
    
    # Store the individual files in a dictionary instead of a zip!
    if 'nci_files' not in st.session_state:
        st.session_state.nci_files = None
        st.session_state.nci_scatter_img = None
        st.session_state.nci_3d_img = None
        
    btn_placeholder = st.empty()
    
    with btn_placeholder.container():
        if st.session_state.nci_files is None:
            if st.button("Generate Plots & Extract Data", type="primary", use_container_width=True):
                if not w_file:
                    st.error("Please upload a wavefunction file first.")
                else:
                    with st.spinner(f"Running Multiwfn in the background... Rendering previews and .ps files..."):
                        
                        tmp_dir = "temp_nci_dir"
                        os.makedirs(tmp_dir, exist_ok=True)
                        
                        file_path = os.path.join(tmp_dir, w_file.name)
                        with open(file_path, "wb") as f:
                            f.write(w_file.getbuffer())
                            
                        do_scatter = plot_choice in ["Scatter Plot", "Both"]
                        do_nci = plot_choice in ["NCI 3D Surface", "Both"]
                        
                        cmd_scatter = f"20\n1\n{quality[0]}\n1\n2\n0\nq\n"
                        cmd_3d = f"20\n3\n{quality[0]}\nq\n\n\n"
                        
                        generated_files = {}
                        
                        try:
                            shutil.copy("Multiwfn", os.path.join(tmp_dir, "Multiwfn"))
                            if os.path.exists("settings.ini"):
                                shutil.copy("settings.ini", os.path.join(tmp_dir, "settings.ini"))
                            
                            basename = os.path.splitext(w_file.name)[0]
                            
                            # ==========================================
                            # SCATTER PLOT LOGIC
                            # ==========================================
                            if do_scatter:
                                # 1. Generate PNG for Streamlit Preview
                                update_multiwfn_settings(tmp_dir, "png")
                                subprocess.run(["./Multiwfn", w_file.name], input=cmd_scatter, capture_output=True, text=True, cwd=tmp_dir)
                                if os.path.exists(os.path.join(tmp_dir, "scatter.png")):
                                    with open(os.path.join(tmp_dir, "scatter.png"), "rb") as img:
                                        st.session_state.nci_scatter_img = img.read()
                                    
                                # 2. Generate PS file for Download
                                update_multiwfn_settings(tmp_dir, "ps")
                                subprocess.run(["./Multiwfn", w_file.name], input=cmd_scatter, capture_output=True, text=True, cwd=tmp_dir)
                                
                                # Read files directly into Python memory
                                if os.path.exists(os.path.join(tmp_dir, "scatter.ps")):
                                    with open(os.path.join(tmp_dir, "scatter.ps"), "rb") as f:
                                        generated_files[f"RDG_Scatter_{basename}.ps"] = f.read()
                                        
                                if os.path.exists(os.path.join(tmp_dir, "output.txt")):
                                    with open(os.path.join(tmp_dir, "output.txt"), "rb") as f:
                                        generated_files[f"RDG_Scatter_Data_{basename}.dat"] = f.read()

                            # ==========================================
                            # NCI 3D SURFACE LOGIC
                            # ==========================================
                            if do_nci:
                                # 1. Generate PNG for Streamlit Preview
                                update_multiwfn_settings(tmp_dir, "png")
                                subprocess.run(["./Multiwfn", w_file.name], input=cmd_3d, capture_output=True, text=True, cwd=tmp_dir)
                                if os.path.exists(os.path.join(tmp_dir, "isosurface.png")):
                                    with open(os.path.join(tmp_dir, "isosurface.png"), "rb") as img:
                                        st.session_state.nci_3d_img = img.read()
                                    
                                # 2. Generate PS file for Download
                                update_multiwfn_settings(tmp_dir, "ps")
                                subprocess.run(["./Multiwfn", w_file.name], input=cmd_3d, capture_output=True, text=True, cwd=tmp_dir)
                                
                                if os.path.exists(os.path.join(tmp_dir, "isosurface.ps")):
                                    with open(os.path.join(tmp_dir, "isosurface.ps"), "rb") as f:
                                        generated_files[f"NCI_3D_Surface_{basename}.ps"] = f.read()
                            
                            if not generated_files:
                                st.error("Multiwfn finished, but no files were generated.")
                            else:
                                st.session_state.nci_files = generated_files
                                st.success(f"Plots rendered successfully!")
                                
                        except subprocess.CalledProcessError as e:
                            st.error(f"Multiwfn crashed: {e.stderr}")
                        finally:
                            shutil.rmtree(tmp_dir, ignore_errors=True)
                            st.rerun()

        else:
            # --- DISPLAY THE IMAGES ON SCREEN ---
            img_col1, img_col2 = st.columns(2)
            
            if st.session_state.nci_scatter_img:
                with img_col1:
                    st.markdown('<p class="section-header" style="text-align: center;">📊 RDG Scatter Plot</p>', unsafe_allow_html=True)
                    st.image(st.session_state.nci_scatter_img, use_container_width=True)
                    
            if st.session_state.nci_3d_img:
                with img_col2 if st.session_state.nci_scatter_img else img_col1:
                    st.markdown('<p class="section-header" style="text-align: center;">🧊 3D NCI Surface</p>', unsafe_allow_html=True)
                    st.image(st.session_state.nci_3d_img, use_container_width=True)

            st.write("")
            st.divider()
            
            # --- DYNAMIC ROW OF INDIVIDUAL DOWNLOAD BUTTONS ---
            st.markdown('<p class="section-header">Download Output Files</p>', unsafe_allow_html=True)
            
            # Create exactly as many columns as there are files + 1 for the Reset button
            cols = st.columns(len(st.session_state.nci_files) + 1)
            
            for i, (filename, file_data) in enumerate(st.session_state.nci_files.items()):
                with cols[i]:
                    ext = filename.split('.')[-1].upper()
                    st.download_button(
                        label=f"⬇️ Download {ext} ({'Scatter' if 'Scatter' in filename else 'Surface'})",
                        data=file_data,
                        file_name=filename,
                        use_container_width=True,
                        type="secondary"
                    )
            
            with cols[-1]:
                if st.button("🔄 Reset / New Plot", type="primary", use_container_width=True):
                    st.session_state.nci_files = None
                    st.session_state.nci_scatter_img = None
                    st.session_state.nci_3d_img = None
                    st.rerun()
