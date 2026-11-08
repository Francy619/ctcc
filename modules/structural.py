import streamlit as st
import os
import io
import re
import math
import xlsxwriter
import pandas as pd

# Import from utils
from utils import HAS_3D, show_3d_molecule, calculate_distance

# Module-specific helpers
def get_optimized_coords(content):
    coords = {}
    lines = content.splitlines()
    for i in range(len(lines)-1, -1, -1):
        if "Standard orientation:" in lines[i] or "Input orientation:" in lines[i]:
            start_idx = i + 5
            for j in range(start_idx, len(lines)):
                if "---------------------------------------------------------------------" in lines[j]: break
                parts = lines[j].split()
                if len(parts) == 6: coords[int(parts[0])] = (float(parts[3]), float(parts[4]), float(parts[5]))
            break
    return coords

def find_stretching_frequency(content, atomA, atomB, coords):
    if not coords or atomA not in coords or atomB not in coords: return None
    cA, cB = coords[atomA], coords[atomB]
    dist = calculate_distance(cA, cB)
    bond_vector = [(cB[0]-cA[0])/dist, (cB[1]-cA[1])/dist, (cB[2]-cA[2])/dist]
    max_stretch, best_freq = -1.0, None
    current_freqs = []
    current_disps = {}
    lines = content.splitlines()
    for line in lines:
        if "Frequencies --" in line:
            current_freqs = [float(x) for x in line.split()[2:]]
            current_disps = {} 
        elif current_freqs and len(line.split()) >= 11 and "Atom" not in line:
            parts = line.split()
            if not parts[0].isdigit(): continue
            try:
                atom_idx = int(parts[0])
                if atom_idx in (atomA, atomB):
                    current_disps[atom_idx] = [(float(parts[2+m*3]), float(parts[3+m*3]), float(parts[4+m*3])) for m in range(len(current_freqs))]
                    if atomA in current_disps and atomB in current_disps:
                        disp_A, disp_B = current_disps[atomA], current_disps[atomB]
                        for m in range(len(current_freqs)):
                            rel = (disp_B[m][0]-disp_A[m][0], disp_B[m][1]-disp_A[m][1], disp_B[m][2]-disp_A[m][2])
                            stretch = abs(rel[0]*bond_vector[0] + rel[1]*bond_vector[1] + rel[2]*bond_vector[2])
                            if stretch > max_stretch:
                                max_stretch, best_freq = stretch, current_freqs[m]
            except ValueError: continue
    return best_freq

def render():
    st.markdown('<div class="home-btn-container">', unsafe_allow_html=True)
    col_home, _ = st.columns([1, 6])
    with col_home:
        if st.button("🏠 Back to Home", type="secondary", key="home_struct"): 
            st.session_state.app_mode = "Home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="main-header-container"><div class="main-title">📏 Structural & Vibrational Data Analysis</div><div class="sub-title">Track bond lengths and stretching frequencies from Gaussian log files.</div></div>', unsafe_allow_html=True)
    
    st.markdown('<p class="section-header">⚙️ General Settings</p>', unsafe_allow_html=True)
    with st.container(border=True):
        col_scale1, col_scale2 = st.columns(2)
        with col_scale1:
            need_scaling = st.radio("Apply Frequency Scaling?", ["No", "Yes"], index=1, horizontal=True)
        with col_scale2:
            scaling_factor = None
            if need_scaling == "Yes":
                scaling_factor = st.number_input("Enter Scaling Factor:", value=0.9594, format="%.4f")
    
    st.write("")
    st.markdown('<p class="section-header">1. Primary System (Monomer 1)</p>', unsafe_allow_html=True)
    with st.container(border=True):
        col_m1_inputs, col_m1_view = st.columns([1, 1])
        with col_m1_inputs:
            m1_file = st.file_uploader("Upload Monomer 1 .log file (e.g., Amino Acid)", type=["log", "out"], key="str_m1")
            m1_bonds = st.number_input("Number of target bonds in Monomer 1:", min_value=0, max_value=5, value=2)
            m1_bond_data = []
            for b in range(m1_bonds):
                c_name, c_atoms = st.columns([2, 2])
                with c_name: b_name = st.text_input(f"Bond {b+1} Name (e.g., O-H, C=O)", key=f"m1_bname_{b}")
                with c_atoms: b_atoms = st.text_input(f"Atom Numbers (e.g., 1, 17)", key=f"m1_batoms_{b}")
                m1_bond_data.append({"name": b_name, "atoms_str": b_atoms})
                
        with col_m1_view:
            if m1_file:
                if HAS_3D:
                    st.markdown("**👁️ Monomer 1 Structure & Atoms**")
                    show_3d_molecule(m1_file.getvalue().decode('utf-8'), m1_file.name)
                else:
                    st.error("🚨 Missing Required Packages! To see the 3D molecule viewer, you must add `stmol` and `py3Dmol` to your `requirements.txt` file (if on Streamlit Cloud) or run `pip install stmol py3Dmol` on your computer.")

    st.write("")
    st.markdown('<p class="section-header">2. Secondary Systems & Complexes</p>', unsafe_allow_html=True)
    num_complexes = st.number_input("Number of secondary systems (e.g., different solvents):", min_value=1, max_value=20, value=1)
    
    systems_input = []
    for i in range(num_complexes):
        with st.container(border=True):
            st.markdown(f"**System {i+1}**")
            c_m2, c_comp = st.columns([1, 1])
            with c_m2:
                m2_file = st.file_uploader(f"Upload Monomer 2 .log file (Solvent {i+1})", type=["log", "out"], key=f"str_m2_{i}")
                
                if m2_file:
                    if HAS_3D:
                        with st.expander(f"👁️ View Monomer 2 Structure & Atoms", expanded=True):
                            show_3d_molecule(m2_file.getvalue().decode('utf-8'), m2_file.name)

                m2_bonds = st.number_input(f"Number of target bonds in Monomer 2 (System {i+1}):", min_value=0, max_value=5, value=1, key=f"m2_b_cnt_{i}")
                m2_bond_data = []
                for b in range(m2_bonds):
                    c_n, c_a = st.columns([2, 2])
                    with c_n: bn = st.text_input(f"Bond {b+1} Name", key=f"m2_n_{i}_{b}")
                    with c_a: ba = st.text_input(f"Atom Numbers", key=f"m2_a_{i}_{b}")
                    m2_bond_data.append({"name": bn, "atoms_str": ba})
                    
            with c_comp:
                c_file = st.file_uploader(f"Upload Complex .log file (M1 + Solvent {i+1})", type=["log", "out"], key=f"str_c_{i}")
                
                if c_file:
                    if HAS_3D:
                        with st.expander(f"👁️ View Complex Structure & Atoms", expanded=True):
                            show_3d_molecule(c_file.getvalue().decode('utf-8'), c_file.name)
                            
                st.markdown("**Atoms in Complex:**")
                
                m1_d_atoms = []
                if m1_bond_data:
                    st.caption("Monomer 1 Bonds:")
                    for b, bdata in enumerate(m1_bond_data):
                        if bdata["name"]: 
                            d_atm = st.text_input(f"{bdata['name']} atoms:", value=bdata["atoms_str"], key=f"c{i}_m1b_{b}")
                            m1_d_atoms.append({"name": bdata["name"], "atoms_str": d_atm})
                            
                m2_d_atoms = []
                if m2_bond_data:
                    st.caption("Monomer 2 Bonds:")
                    for b, bdata in enumerate(m2_bond_data):
                        if bdata["name"]: 
                            d_atm = st.text_input(f"{bdata['name']} atoms:", value=bdata["atoms_str"], key=f"c{i}_m2b_{b}")
                            m2_d_atoms.append({"name": bdata["name"], "atoms_str": d_atm})
                            
            systems_input.append({"m2_file": m2_file, "m2_bonds": m2_bond_data, "c_file": c_file, "c_m1_bonds": m1_d_atoms, "c_m2_bonds": m2_d_atoms})

    if 'calc_done_struct' not in st.session_state:
        st.session_state.calc_done_struct = False
        st.session_state.excel_data_struct = None
        st.session_state.warnings_struct = []
        st.session_state.extracted_rows_struct = []
        st.session_state.bond_names_struct = []
        
    btn_placeholder = st.empty()
    do_struct_run = False
    with btn_placeholder.container():
        if not st.session_state.calc_done_struct:
            col_s1, col_btn, col_s2 = st.columns([1, 1, 1])
            with col_btn:
                if st.button("Run Vibrational Analysis", type="primary", use_container_width=True): do_struct_run = True
        else:
            col_s1, col_calc, col_down, col_s2 = st.columns([2, 3, 3, 2])
            with col_calc:
                if st.button("Run Vibrational Analysis", type="primary", use_container_width=True): do_struct_run = True
            with col_down:
                st.download_button("Download Analysis (.xlsx)", data=st.session_state.excel_data_struct, file_name="Vibrational_Analysis.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="secondary")

    if do_struct_run:
        st.session_state.warnings_struct = [] 
        extracted_rows = []
        
        all_bond_names = []
        for bd in m1_bond_data:
            if bd["name"] and bd["name"] not in all_bond_names: all_bond_names.append(bd["name"])
        for sys in systems_input:
            for bd in sys["m2_bonds"]:
                if bd["name"] and bd["name"] not in all_bond_names: all_bond_names.append(bd["name"])
            
        def process_bond(content, name, atom_str, file_name):
            try: atoms = tuple([int(x.strip()) for x in atom_str.split(",")])
            except: return None, None
            if len(atoms) != 2: return None, None
            coords = get_optimized_coords(content)
            if not coords:
                st.session_state.warnings_struct.append(f"Standard/Input orientation not found in {file_name}.")
                return None, None
            if atoms[0] not in coords or atoms[1] not in coords:
                st.session_state.warnings_struct.append(f"Atoms {atoms} for bond '{name}' not found in coordinates of {file_name}.")
                return None, None
            dist = calculate_distance(coords[atoms[0]], coords[atoms[1]])
            freq = find_stretching_frequency(content, atoms[0], atoms[1], coords)
            if freq is None: st.session_state.warnings_struct.append(f"Stretching frequency for '{name}' not found in {file_name}.")
            return dist, freq

        m1_name = "Monomer_1"
        if m1_file:
            m1_file.seek(0)
            m1_content = m1_file.read().decode('utf-8')
            m1_name = os.path.splitext(m1_file.name)[0]
            row_data = {"System": m1_name}
            for bd in m1_bond_data:
                if bd["name"] and bd["atoms_str"]:
                    dist, freq = process_bond(m1_content, bd["name"], bd["atoms_str"], m1_file.name)
                    row_data[bd["name"]] = {"dist": dist, "freq": freq}
            extracted_rows.append(row_data)

        base_m1 = re.split(r'[_ -]|site', m1_name, flags=re.IGNORECASE)[0]
        
        for idx, comp in enumerate(systems_input):
            c_file = comp["c_file"]
            m2_file = comp["m2_file"]
            
            c_name = os.path.splitext(c_file.name)[0] if c_file else f"Complex_{idx+1}"
            m2_name = os.path.splitext(m2_file.name)[0] if m2_file else f"M2_{idx+1}"
            
            if c_file:
                c_file.seek(0)
                c_content = c_file.read().decode('utf-8')
                c_system_name = f"{base_m1} ({c_name})"
                row_data_comp = {"System": c_system_name}
                for bd in comp["c_m1_bonds"]:
                    if bd["name"] and bd["atoms_str"]:
                        dist, freq = process_bond(c_content, bd["name"], bd["atoms_str"], c_file.name)
                        row_data_comp[bd["name"]] = {"dist": dist, "freq": freq}
                extracted_rows.append(row_data_comp)
            
            if m2_file:
                m2_file.seek(0)
                m2_content = m2_file.read().decode('utf-8')
                row_data_m2 = {"System": m2_name}
                for bd in comp["m2_bonds"]:
                    if bd["name"] and bd["atoms_str"]:
                        dist, freq = process_bond(m2_content, bd["name"], bd["atoms_str"], m2_file.name)
                        row_data_m2[bd["name"]] = {"dist": dist, "freq": freq}
                extracted_rows.append(row_data_m2)
                
            if c_file and comp["c_m2_bonds"]:
                row_data_c_solv = {"System": f"{m2_name} ({c_name})"}
                has_m2_bonds = False
                for bd in comp["c_m2_bonds"]:
                    if bd["name"] and bd["atoms_str"]:
                        has_m2_bonds = True
                        dist, freq = process_bond(c_content, bd["name"], bd["atoms_str"], c_file.name)
                        row_data_c_solv[bd["name"]] = {"dist": dist, "freq": freq}
                if has_m2_bonds: extracted_rows.append(row_data_c_solv)

        if not extracted_rows:
            st.error("No valid data could be extracted.")
            st.stop()
            
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Frequencies')
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
        center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
        left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
        
        columns = ["System"]
        for b_name in all_bond_names:
            columns.extend([f"Bond Length (A) {b_name}", f"{b_name} Freq"])
            if scaling_factor is not None:
                columns.append(f"Scaled {b_name}")
            
        worksheet.set_row(0, 20)
        for col_num, header in enumerate(columns): worksheet.write(0, col_num, header, header_format)
        worksheet.set_column('A:A', 30, left_format)
        if len(columns) > 1: worksheet.set_column(1, len(columns)-1, 20, center_format)
        
        for row_num, row_dict in enumerate(extracted_rows, start=1):
            worksheet.set_row(row_num, 20)
            worksheet.write(row_num, 0, row_dict.get("System", ""), left_format)
            
            col_idx = 1
            for b_name in all_bond_names:
                b_data = row_dict.get(b_name, {})
                dist = b_data.get("dist")
                freq = b_data.get("freq")
                
                worksheet.write(row_num, col_idx, float(dist) if dist else "", center_format)
                worksheet.write(row_num, col_idx+1, float(freq) if freq else "", center_format)
                
                if scaling_factor is not None:
                    worksheet.write(row_num, col_idx+2, float(freq * scaling_factor) if freq else "", center_format)
                    col_idx += 3
                else:
                    col_idx += 2
                
        workbook.close()
        
        st.session_state.extracted_rows_struct = extracted_rows
        st.session_state.bond_names_struct = all_bond_names
        st.session_state.excel_data_struct = output.getvalue()
        st.session_state.applied_scaling_factor = scaling_factor 
        st.session_state.calc_done_struct = True
        st.rerun()

    if st.session_state.calc_done_struct:
        for w in st.session_state.warnings_struct: st.warning(w)
        st.markdown('<p class="section-header" style="text-align: center; border: none;">Tabulated Results</p>', unsafe_allow_html=True)
        
        df_data = []
        for row in st.session_state.extracted_rows_struct:
            flat_row = {"System": row["System"]}
            for b_name in st.session_state.bond_names_struct:
                b_data = row.get(b_name, {})
                flat_row[f"Bond Length (A) {b_name}"] = b_data.get("dist")
                flat_row[f"{b_name} Freq"] = b_data.get("freq")
                if st.session_state.applied_scaling_factor is not None:
                    flat_row[f"Scaled {b_name}"] = b_data.get("freq") * st.session_state.applied_scaling_factor if b_data.get("freq") else None
            df_data.append(flat_row)
            
        display_df = pd.DataFrame(df_data)
        st.dataframe(display_df.style.format(precision=4), use_container_width=True)
