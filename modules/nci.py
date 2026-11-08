import streamlit as st
import os
import subprocess
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import zipfile
import io
import glob

def render():
    st.markdown('<div class="home-btn-container">', unsafe_allow_html=True)
    col_home, _ = st.columns([1, 6])
    with col_home:
        if st.button("🏠 Back to Home", type="secondary", key="home_nci"): 
            st.session_state.app_mode = "Home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="main-header-container"><div class="main-title">🌌 NCI & RDG Generator</div><div class="sub-title">Generates output.txt for Gnuplot, VMD Grids, and instant .ps Scatter Plots.</div></div>', unsafe_allow_html=True)
    
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
            plot_choice = st.radio("What to generate?", ["Scatter Plot", "NCI 3D Grids", "Both"])

    st.divider()
    
    if 'nci_files' not in st.session_state:
        st.session_state.nci_files = {}
        st.session_state.nci_scatter_img = None
        
    btn_placeholder = st.empty()
    
    with btn_placeholder.container():
        if not st.session_state.nci_files:
            if st.button("Run NCI Analysis", type="primary", use_container_width=True):
                if not w_file:
                    st.error("Please upload a wavefunction file first.")
                else:
                    with st.spinner(f"Running Multiwfn... Generating output.txt and VMD .cub grids..."):
                        
                        tmp_dir = "temp_nci_dir"
                        os.makedirs(tmp_dir, exist_ok=True)
                        
                        file_path = os.path.join(tmp_dir, w_file.name)
                        with open(file_path, "wb") as f:
                            f.write(w_file.getbuffer())
                            
                        do_scatter = plot_choice in ["Scatter Plot", "Both"]
                        do_nci = plot_choice in ["NCI 3D Grids", "Both"]
                        
                        generated_files = {}
                        
                        try:
                            shutil.copy("Multiwfn", os.path.join(tmp_dir, "Multiwfn"))
                            if os.path.exists("settings.ini"):
                                shutil.copy("settings.ini", os.path.join(tmp_dir, "settings.ini"))
                            
                            basename = os.path.splitext(w_file.name)[0]
                            
                            # ==========================================
                            # 1. SCATTER PLOT & GNUPLOT DATA
                            # ==========================================
                            if do_scatter:
                                # Command: 20 (NCI) -> 1 (Scatter) -> {quality} -> 2 (Export data to output.txt) -> 0 -> q
                                cmd_scatter = f"20\n1\n{quality[0]}\n2\n0\nq\n"
                                subprocess.run(["./Multiwfn", w_file.name], input=cmd_scatter, capture_output=True, text=True, cwd=tmp_dir)
                                
                                output_txt = os.path.join(tmp_dir, "output.txt")
                                if os.path.exists(output_txt):
                                    # Save the exact output.txt for the user's local Gnuplot workflow
                                    with open(output_txt, "rb") as f:
                                        generated_files["output.txt"] = f.read()
                                        
                                    # Draw the instant .ps plot with Python so they can skip Gnuplot if they want
                                    try:
                                        df = pd.read_csv(output_txt, sep=r'\s+', header=None, comment='#')
                                        df = df.apply(pd.to_numeric, errors='coerce').dropna()
                                        
                                        if not df.empty:
                                            x = df.iloc[:, 0]
                                            y = df.iloc[:, 1]
                                            
                                            fig, ax = plt.subplots(figsize=(8, 6))
                                            sc = ax.scatter(x, y, s=4, c=x, cmap='jet')
                                            ax.set_xlabel(r'sign($\lambda_2$)$\rho$ (a.u.)', fontsize=12)
                                            ax.set_ylabel('RDG (a.u.)', fontsize=12)
                                            ax.set_title(f'NCI Scatter Plot - {basename}', fontsize=14)
                                            ax.grid(True, linestyle='--', alpha=0.5)
                                            
                                            # Save PNG for preview
                                            png_path = os.path.join(tmp_dir, "scatter_preview.png")
                                            plt.savefig(png_path, format='png', dpi=150, bbox_inches='tight')
                                            with open(png_path, "rb") as img:
                                                st.session_state.nci_scatter_img = img.read()
                                                
                                            # Save PS for download
                                            ps_path = os.path.join(tmp_dir, "scatter.ps")
                                            plt.savefig(ps_path, format='ps', bbox_inches='tight')
                                            with open(ps_path, "rb") as ps_f:
                                                generated_files[f"RDG_Scatter_Plot_{basename}.ps"] = ps_f.read()
                                                
                                            plt.close(fig)
                                    except Exception as e:
                                        st.error(f"Python graphing failed: {e}")

                            # ==========================================
                            # 2. VMD GRIDS (.cub files)
                            # ==========================================
                            if do_nci:
                                # Command: 20 (NCI) -> 2 (VMD Grids) -> {quality} -> 0 -> q
                                cmd_vmd = f"20\n2\n{quality[0]}\n0\nq\n"
                                subprocess.run(["./Multiwfn", w_file.name], input=cmd_vmd, capture_output=True, text=True, cwd=tmp_dir)
                                
                                # Gather RDG.cub, signlam2rho.cub, and NCIplot.vmd into a single zip
                                zip_buffer = io.BytesIO()
                                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                                    vmd_files_found = False
                                    for ext in ["vmd", "cub"]:
                                        for f_path in glob.glob(os.path.join(tmp_dir, f"*.{ext}")):
                                            f_name = os.path.basename(f_path)
                                            zip_file.write(f_path, f_name)
                                            vmd_files_found = True
                                            
                                if vmd_files_found:
                                    generated_files[f"VMD_NCI_Files_{basename}.zip"] = zip_buffer.getvalue()
                            
                            if not generated_files:
                                st.error("Calculation finished, but no files were generated. Check your file format.")
                            else:
                                st.session_state.nci_files = generated_files
                                st.success("Calculations completed successfully!")
                                
                        except subprocess.CalledProcessError as e:
                            st.error(f"Multiwfn crashed: {e.stderr}")
                        finally:
                            shutil.rmtree(tmp_dir, ignore_errors=True)
                            st.rerun()

        else:
            # --- DISPLAY THE PREVIEW ---
            if st.session_state.nci_scatter_img:
                col_img, _ = st.columns([1, 1])
                with col_img:
                    st.markdown('<p class="section-header" style="text-align: center;">📊 Scatter Plot Preview</p>', unsafe_allow_html=True)
                    st.image(st.session_state.nci_scatter_img, use_container_width=True)

            st.write("")
            st.divider()
            
            # --- DYNAMIC DOWNLOAD BUTTONS ---
            st.markdown('<p class="section-header">Download Output Files</p>', unsafe_allow_html=True)
            
            # Count how many buttons we need
            num_buttons = len(st.session_state.nci_files)
            cols = st.columns(num_buttons) if num_buttons > 0 else st.columns(1)
            
            # Ensure predictable order: output.txt -> .ps -> .zip
            sorted_keys = sorted(st.session_state.nci_files.keys(), key=lambda x: (
                0 if x == "output.txt" else (1 if x.endswith('.ps') else 2)
            ))
            
            for i, filename in enumerate(sorted_keys):
                with cols[i]:
                    file_data = st.session_state.nci_files[filename]
                    
                    if filename == "output.txt":
                        label = "⬇️ Download output.txt (For Gnuplot)"
                    elif filename.endswith(".ps"):
                        label = "⬇️ Download Scatter Plot (.ps)"
                    else:
                        label = "⬇️ Download VMD Files (.zip)"
                        
                    st.download_button(
                        label=label,
                        data=file_data,
                        file_name=filename,
                        use_container_width=True,
                        type="secondary"
                    )
            
            st.write("")
            if st.button("🔄 Reset / New Plot", type="primary"):
                st.session_state.nci_files = {}
                st.session_state.nci_scatter_img = None
                st.rerun()
