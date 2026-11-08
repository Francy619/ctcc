import streamlit as st
import os
import subprocess
import shutil
import pandas as pd
import matplotlib.pyplot as plt

def render():
    st.markdown('<div class="home-btn-container">', unsafe_allow_html=True)
    col_home, _ = st.columns([1, 6])
    with col_home:
        if st.button("🏠 Back to Home", type="secondary", key="home_nci"): 
            st.session_state.app_mode = "Home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="main-header-container"><div class="main-title">🌌 NCI & RDG Generator</div><div class="sub-title">Python-powered Scatter Plots (.ps) and VMD Grid Generation.</div></div>', unsafe_allow_html=True)
    
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
        st.session_state.nci_files = None
        st.session_state.nci_scatter_img = None
        
    btn_placeholder = st.empty()
    
    with btn_placeholder.container():
        if st.session_state.nci_files is None:
            if st.button("Run NCI Analysis", type="primary", use_container_width=True):
                if not w_file:
                    st.error("Please upload a wavefunction file first.")
                else:
                    with st.spinner(f"Running Multiwfn... Generating data and plots..."):
                        
                        tmp_dir = "temp_nci_dir"
                        os.makedirs(tmp_dir, exist_ok=True)
                        
                        file_path = os.path.join(tmp_dir, w_file.name)
                        with open(file_path, "wb") as f:
                            f.write(w_file.getbuffer())
                            
                        do_scatter = plot_choice in ["Scatter Plot", "Both"]
                        do_nci = plot_choice in ["NCI 3D Grids", "Both"]
                        
                        # Dynamically build the command sequence
                        cmd = "20\n"
                        if do_scatter:
                            cmd += f"1\n{quality[0]}\n2\n0\n"
                        if do_nci:
                            cmd += f"2\n{quality[0]}\n0\n"
                        cmd += "q\n"
                        
                        generated_files = {}
                        
                        try:
                            shutil.copy("Multiwfn", os.path.join(tmp_dir, "Multiwfn"))
                            if os.path.exists("settings.ini"):
                                shutil.copy("settings.ini", os.path.join(tmp_dir, "settings.ini"))
                            
                            basename = os.path.splitext(w_file.name)[0]
                            
                            # Execute Multiwfn
                            subprocess.run(["./Multiwfn", w_file.name], input=cmd, capture_output=True, text=True, cwd=tmp_dir, check=True)
                            
                            # Process Scatter Plot Data
                            output_txt = os.path.join(tmp_dir, "output.txt")
                            if do_scatter and os.path.exists(output_txt):
                                with open(output_txt, "rb") as f:
                                    generated_files[f"RDG_Scatter_Data_{basename}.dat"] = f.read()
                                    
                                # Draw the plot with Matplotlib
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

                            # Process NCI 3D Grids
                            if do_nci:
                                import glob
                                for ext in ["vmd", "cub"]:
                                    for f_path in glob.glob(os.path.join(tmp_dir, f"*.{ext}")):
                                        f_name = os.path.basename(f_path)
                                        with open(f_path, "rb") as f:
                                            generated_files[f"{basename}_{f_name}"] = f.read()
                            
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
            
            # Create a clean grid for the download buttons
            cols = st.columns(3)
            
            sorted_files = sorted(st.session_state.nci_files.items(), key=lambda x: x[0])
            
            for i, (filename, file_data) in enumerate(sorted_files):
                with cols[i % 3]:
                    ext = filename.split('.')[-1].lower()
                    
                    if "scatter_data" in filename.lower(): label = "⬇️ Scatter Data (.dat)"
                    elif "scatter_plot" in filename.lower(): label = "⬇️ Scatter Plot (.ps)"
                    else: label = f"⬇️ 3D NCI Data (.{ext})"
                        
                    st.download_button(
                        label=label,
                        data=file_data,
                        file_name=filename,
                        use_container_width=True,
                        type="secondary"
                    )
            
            st.write("")
            if st.button("🔄 Reset / New Plot", type="primary"):
                st.session_state.nci_files = None
                st.session_state.nci_scatter_img = None
                st.rerun()
