import streamlit as st
import os
import re
import io
import subprocess
import pandas as pd
import xlsxwriter
import shutil
import py3Dmol
from stmol import showmol

def get_xyz_from_multiwfn(w_file_bytes, filename):
    """Uses Multiwfn silently to export an .xyz coordinate file for perfect 3D rendering"""
    tmp_dir = f"temp_cvb_xyz_{filename.replace('.', '_')}"
    os.makedirs(tmp_dir, exist_ok=True)
    xyz_data = None
    
    try:
        if os.path.exists("Multiwfn"):
            shutil.copy("Multiwfn", os.path.join(tmp_dir, "Multiwfn"))
            
        file_path = os.path.join(tmp_dir, filename)
        with open(file_path, "wb") as f:
            f.write(w_file_bytes)
            
        # Command: 100 (Other functions) -> 2 (Export geometry) -> 2 (Export to XYZ) -> preview.xyz -> 0 -> q
        cmd = "100\n2\n2\npreview.xyz\n0\nq\n"
        subprocess.run(["./Multiwfn", filename], input=cmd, capture_output=True, text=True, cwd=tmp_dir)
        
        xyz_path = os.path.join(tmp_dir, "preview.xyz")
        if os.path.exists(xyz_path):
            with open(xyz_path, "r") as f:
                xyz_data = f.read()
                
    except Exception as e:
        pass
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        
    return xyz_data

def render():
    st.markdown('<div class="home-btn-container">', unsafe_allow_html=True)
    col_home, _ = st.columns([1, 6])
    with col_home:
        if st.button("🏠 Back to Home", type="secondary", key="home_cvb"): 
            st.session_state.app_mode = "Home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="main-header-container"><div class="main-title">📈 Core Valence Bifurcation (CVB) Index</div><div class="sub-title">Automate Multiwfn to calculate CVB metrics directly from .wfn/.wfx files.</div></div>', unsafe_allow_html=True)
    
    if not os.path.exists("Multiwfn"):
        st.error("🚨 **Multiwfn Binary Missing:** The 'Multiwfn' executable was not found on the server. Please ensure Multiwfn.zip is uploaded to the root of your GitHub repository.")
        st.stop()
        
    num_cvb_systems = st.number_input("How many Wavefunction files to evaluate?", min_value=1, max_value=20, value=1)
    
    cvb_inputs = []
    for i in range(num_cvb_systems):
        with st.container(border=True):
            col_cvb_inputs, col_cvb_view = st.columns([1, 1])
            with col_cvb_inputs:
                w_file = st.file_uploader(f"Upload .wfn or .wfx File {i+1}", type=["wfn", "wfx"], key=f"cvb_wfn_{i}")
                w_atoms = st.text_input("Target Atoms (e.g., 1,3,4)", key=f"cvb_atoms_{i}")
                
            with col_cvb_view:
                if w_file:
                    st.markdown("**👁️ Interactive Molecule Viewer (Atom Indices)**")
                    
                    preview_key = f"cvb_xyz_{w_file.name}_{w_file.size}"
                    
                    if preview_key not in st.session_state:
                        with st.spinner("Extracting 3D Coordinates..."):
                            st.session_state[preview_key] = get_xyz_from_multiwfn(w_file.getvalue(), w_file.name)
                            
                    xyz_data = st.session_state[preview_key]
                    
                    if xyz_data:
                        # Render the 3D molecule interactively
                        view = py3Dmol.view(width=400, height=350)
                        view.addModel(xyz_data, "xyz")
                        view.setStyle({'stick': {'radius': 0.15}, 'sphere': {'scale': 0.25}})
                        
                        # Manually stamp the Atom Name + Index on every atom based on XYZ line numbers
                        lines = [line.strip() for line in xyz_data.strip().split('\n') if line.strip()]
                        if len(lines) > 2:
                            try:
                                num_atoms = int(lines[0])
                                for idx in range(num_atoms):
                                    parts = lines[idx + 2].split()
                                    if len(parts) >= 4:
                                        elem = parts[0]
                                        x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                                        
                                        view.addLabel(f"{elem}{idx + 1}", 
                                                      {"position": {"x": x, "y": y, "z": z}, 
                                                       "fontColor": "black", 
                                                       "backgroundColor": "white", 
                                                       "backgroundOpacity": 0.8, 
                                                       "fontsize": 13})
                            except Exception as e:
                                pass
                                    
                        view.zoomTo()
                        showmol(view, height=350, width=400)
                    else:
                        st.warning("⚠️ Could not extract 3D coordinates for preview. (You can still run the calculation).")
            
            cvb_inputs.append({"file": w_file, "atoms": w_atoms})
            
    st.divider()
    
    if 'calc_done_cvb' not in st.session_state:
        st.session_state.calc_done_cvb = False
        st.session_state.excel_data_cvb = None
        st.session_state.cvb_results = []
        
    btn_placeholder = st.empty()
    do_cvb_run = False
    
    with btn_placeholder.container():
        if not st.session_state.calc_done_cvb:
            col_s1, col_btn, col_s2 = st.columns([1, 1, 1])
            with col_btn:
                if st.button("Run Multiwfn & Extract CVB", type="primary", use_container_width=True): do_cvb_run = True
        else:
            col_s1, col_calc, col_down, col_s2 = st.columns([2, 3, 3, 2])
            with col_calc:
                if st.button("Run Multiwfn & Extract CVB", type="primary", use_container_width=True): do_cvb_run = True
            with col_down:
                st.download_button("Download CVB Report (.xlsx)", data=st.session_state.excel_data_cvb, file_name="CVB_Index_Results.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="secondary")

    if do_cvb_run:
        all_extracted_data = []
        tmp_dir = "temp_multiwfn_cvb_calc"
        os.makedirs(tmp_dir, exist_ok=True)
        
        with st.spinner("Running Multiwfn silently in the background... This may take a moment."):
            for item in cvb_inputs:
                w_file = item["file"]
                atoms = item["atoms"].strip()
                
                if not w_file or not atoms: continue
                
                file_path = os.path.join(tmp_dir, w_file.name)
                with open(file_path, "wb") as f:
                    f.write(w_file.getbuffer())
                    
                basename = os.path.splitext(w_file.name)[0]
                system_name = basename.replace('_', ' - ')
                
                command_sequence = f"200\n1\n{atoms}\n0\nq\n"
                
                try:
                    process = subprocess.run(
                        ["./Multiwfn", file_path],
                        input=command_sequence,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    output_text = process.stdout
                    
                    match_cv_d = re.search(r'donor.*?([-+]?\d*\.\d+)', output_text, re.IGNORECASE) or re.search(r'ELF\(C-V,\s*D\).*?([-+]?\d*\.\d+)', output_text, re.IGNORECASE)
                    match_cv_a = re.search(r'acceptor.*?([-+]?\d*\.\d+)', output_text, re.IGNORECASE) or re.search(r'ELF\(C-V,\s*A\).*?([-+]?\d*\.\d+)', output_text, re.IGNORECASE)
                    match_dh_a = re.search(r'between D-H and A.*?([-+]?\d*\.\d+)', output_text, re.IGNORECASE) or re.search(r'ELF\(DH-A\).*?([-+]?\d*\.\d+)', output_text, re.IGNORECASE) or re.search(r'DH-A.*?([-+]?\d*\.\d+)', output_text, re.IGNORECASE) or re.search(r'minimum.*?([-+]?\d*\.\d+)', output_text, re.IGNORECASE)
                    match_cvb = re.search(r'CVB index.*?([-+]?\d*\.\d+)', output_text, re.IGNORECASE) or re.search(r'CVB.*?([-+]?\d*\.\d+)', output_text, re.IGNORECASE)

                    all_extracted_data.append({
                        "System": system_name,
                        "ELF(C-V,D)": float(match_cv_d.group(1)) if match_cv_d else None,
                        "ELF(C-V,A)": float(match_cv_a.group(1)) if match_cv_a else None,
                        "ELF(DH-A)": float(match_dh_a.group(1)) if match_dh_a else None,
                        "CVB index": float(match_cvb.group(1)) if match_cvb else None
                    })
                    
                except subprocess.CalledProcessError as e:
                    st.error(f"Multiwfn crashed processing {w_file.name}: {e.stderr}")
                finally:
                    if os.path.exists(file_path):
                        os.remove(file_path)
            
            if os.path.exists(tmp_dir):
                os.rmdir(tmp_dir)

        if not all_extracted_data:
            st.error("No valid CVB data was extracted. Ensure your Target Atoms are correct.")
            st.stop()
            
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("CVB Data")
        
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
        center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'num_format': '0.0000'})
        left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
        
        headers = ["System", "ELF(C-V,D)", "ELF(C-V,A)", "ELF(DH-A)", "CVB index"]
        worksheet.set_row(0, 24)
        for col_num, header in enumerate(headers): worksheet.write(0, col_num, header, header_format)
        worksheet.set_column('A:A', 35, left_format)
        worksheet.set_column('B:E', 20, center_format)
        
        for row_num, row_data in enumerate(all_extracted_data, start=1):
            worksheet.set_row(row_num, 20)
            worksheet.write(row_num, 0, row_data["System"], left_format)
            
            for col_idx, key in enumerate(headers[1:], start=1):
                val = row_data.get(key)
                if val is not None: worksheet.write_number(row_num, col_idx, val, center_format)
                else: worksheet.write(row_num, col_idx, "N/A", center_format)
                
        workbook.close()
        
        st.session_state.cvb_results = all_extracted_data
        st.session_state.excel_data_cvb = output.getvalue()
        st.session_state.calc_done_cvb = True
        st.rerun()

    if st.session_state.calc_done_cvb:
        st.markdown('<p class="section-header" style="text-align: center; border: none;">Tabulated CVB Results</p>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(st.session_state.cvb_results).style.format(precision=4), use_container_width=True)
