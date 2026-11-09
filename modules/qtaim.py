import streamlit as st
import os
import io
import re
import xlsxwriter
import pandas as pd

def render():
    st.markdown('<div class="home-btn-container">', unsafe_allow_html=True)
    col_home, _ = st.columns([1, 6])
    with col_home:
        if st.button("🏠 Back to Home", type="secondary", key="home_qtaim"): 
            st.session_state.app_mode = "Home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="main-header-container"><div class="main-title">⭕ QTAIM Properties Tabulator</div><div class="sub-title">Parse Multiwfn CPprop.txt files to extract density properties at Bond Critical Points.</div></div>', unsafe_allow_html=True)
    with st.container(border=True):
        num_qtaim_files = st.number_input("How many CPprop output files are you analyzing?", min_value=1, max_value=20, value=1)
    st.write("")
    qtaim_inputs = []
    for i in range(num_qtaim_files):
        with st.container(border=True):
            col1, col2 = st.columns([1, 2])
            with col1: q_file = st.file_uploader(f"Upload CPprop.txt {i+1}", type=["txt"], key=f"q_file_{i}")
            with col2: cp_string = st.text_input("Target Critical Points (comma-separated, e.g. 15, 23)", key=f"q_cps_{i}")
            qtaim_inputs.append({"file": q_file, "cp_str": cp_string})
    st.divider()
    if 'calc_done_qtaim' not in st.session_state:
        st.session_state.calc_done_qtaim = False
        st.session_state.qtaim_results = []
        st.session_state.excel_data_qtaim = None
        st.session_state.warnings_qtaim = []

    btn_placeholder = st.empty()
    do_qtaim_run = False
    with btn_placeholder.container():
        if not st.session_state.calc_done_qtaim:
            col_s1, col_btn, col_s2 = st.columns([1, 1, 1])
            with col_btn:
                if st.button("Parse QTAIM Data", type="primary", use_container_width=True): do_qtaim_run = True
        else:
            col_s1, col_calc, col_down, col_s2 = st.columns([2, 3, 3, 2])
            with col_calc:
                if st.button("Parse QTAIM Data", type="primary", use_container_width=True): do_qtaim_run = True
            with col_down:
                st.download_button("Download QTAIM Report (.xlsx)", data=st.session_state.excel_data_qtaim, file_name="QTAIM_Results.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="secondary")

    if do_qtaim_run:
        st.session_state.warnings_qtaim = [] 
        
        search_terms = {"Density of all electrons": "Density of all electrons:", "Laplacian of electron density": "Laplacian of electron density:", "Potential energy density V(r)": "Potential energy density V(r):", "Lagrangian kinetic energy G(r)": "Lagrangian kinetic energy G(r):", "Energy density E(r) or H(r)": "Energy density E(r) or H(r):"}
        all_extracted_data = []
        for item in qtaim_inputs:
            uploaded_file = item["file"]
            if not uploaded_file: continue
            try: target_cps = [int(x.strip()) for x in item["cp_str"].split(',') if x.strip().isdigit()]
            except: continue
            if not target_cps: continue
            
            uploaded_file.seek(0)
            lines = uploaded_file.read().decode('utf-8').splitlines()
            basename = os.path.splitext(uploaded_file.name)[0]
            system_name = re.sub(r'^[cC][pP][pP][rR][oO][pP]', '', basename)
            system_name = re.sub(r'[\d,\s]+$', '', system_name).strip()
            if not system_name: system_name = basename
            
            extracted_data = []
            current_cp = None
            cp_data = {}
            for line in lines:
                if "----------------   CP" in line:
                    if current_cp in target_cps and cp_data: extracted_data.append(cp_data)
                    match = re.search(r'CP\s+(\d+)', line)
                    if match:
                        current_cp = int(match.group(1))
                        cp_data = {"System": system_name, "CP Number": current_cp}
                    else: current_cp = None
                    continue
                if current_cp in target_cps:
                    for key, term in search_terms.items():
                        if line.lstrip().startswith(term):
                            try: cp_data[key] = float(line.split(term)[1].strip())
                            except: cp_data[key] = None
            if current_cp in target_cps and cp_data: extracted_data.append(cp_data)
            
            if not extracted_data:
                st.session_state.warnings_qtaim.append(f"Target Critical Points ({item['cp_str']}) and their properties are not found in {uploaded_file.name}.")
            else:
                for data in extracted_data:
                    density = data.get("Density of all electrons")
                    data["Binding Energy"] = (-223.08 * density) + 0.7423 if density is not None else None
                extracted_data.sort(key=lambda x: x["CP Number"])
                all_extracted_data.extend(extracted_data)

        if not all_extracted_data:
            st.error("QTAIM extraction failed. Check warnings above for missing data.")
            st.stop()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("QTAIM Data")
        header_base = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
        left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
        center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
        prop_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'num_format': '0.0000'})
        be_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'num_format': '0.00'})
        sup = workbook.add_format({'bold': True, 'font_script': 1, 'font_name': 'Times New Roman', 'font_size': 12})
        sub = workbook.add_format({'bold': True, 'font_script': 2, 'font_name': 'Times New Roman', 'font_size': 12})
        bold_fmt = workbook.add_format({'bold': True, 'font_name': 'Times New Roman', 'font_size': 12})
        worksheet.set_row(0, 20)
        worksheet.write(0, 0, "System", header_format); worksheet.write(0, 1, "CP", header_format); worksheet.write(0, 2, "ρ(r)", header_format)
        worksheet.write_rich_string(0, 3, bold_fmt, "Δ", sup, "2", bold_fmt, "ρ", header_base)
        worksheet.write_rich_string(0, 4, bold_fmt, "V(r", sub, "bcp", bold_fmt, ")", header_base)
        worksheet.write(0, 5, "G(rcp)", header_format); worksheet.write(0, 6, "H(r)", header_format); worksheet.write(0, 7, "B. E (kcal/Mol)", header_format)
        worksheet.set_column('A:A', 22); worksheet.set_column('B:B', 8); worksheet.set_column('C:G', 14); worksheet.set_column('H:H', 18)
        
        if all_extracted_data:
            keys_in_order = ["Density of all electrons", "Laplacian of electron density", "Potential energy density V(r)", "Lagrangian kinetic energy G(r)", "Energy density E(r) or H(r)"]
            start_row = 1; current_system = all_extracted_data[0]["System"]
            for row_num, data in enumerate(all_extracted_data, start=1):
                worksheet.set_row(row_num, 20)
                if data["System"] != current_system:
                    if row_num - 1 > start_row: worksheet.merge_range(start_row, 0, row_num - 1, 0, current_system, left_format)
                    else: worksheet.write(start_row, 0, current_system, left_format)
                    start_row = row_num; current_system = data["System"]
                worksheet.write_number(row_num, 1, data["CP Number"], center_format)
                for col_offset, key in enumerate(keys_in_order):
                    val = data.get(key)
                    if val is not None: worksheet.write_number(row_num, 2 + col_offset, val, prop_format)
                    else: worksheet.write(row_num, 2 + col_offset, "N/A", center_format)
                be = data.get("Binding Energy")
                if be is not None: worksheet.write_number(row_num, 7, be, be_format)
                else: worksheet.write(row_num, 7, "N/A", be_format)
            last_row = len(all_extracted_data)
            if last_row > start_row: worksheet.merge_range(start_row, 0, last_row, 0, current_system, left_format)
            else: worksheet.write(start_row, 0, current_system, left_format)
        
        workbook.close()
        st.session_state.qtaim_results = all_extracted_data
        st.session_state.excel_data_qtaim = output.getvalue()
        st.session_state.calc_done_qtaim = True
        st.rerun()

    if st.session_state.calc_done_qtaim:
        st.write("")
        for w in st.session_state.warnings_qtaim:
            st.warning(w)
            
        if st.session_state.qtaim_results:
            st.markdown('**Summary: Extracted QTAIM Properties** *(Download Excel for formatted report)*')
            
            # Convert dictionary list to pandas DataFrame
            df = pd.DataFrame(st.session_state.qtaim_results)
            
            # Map the backend keys to nice UI column headers
            rename_map = {
                "System": "System",
                "CP Number": "CP",
                "Density of all electrons": "ρ(r)",
                "Laplacian of electron density": "∇²ρ",
                "Potential energy density V(r)": "V(r_bcp)",
                "Lagrangian kinetic energy G(r)": "G(rcp)",
                "Energy density E(r) or H(r)": "H(r)",
                "Binding Energy": "B.E. (kcal/mol)"
            }
            df = df.rename(columns=rename_map)
            
            # Ensure the columns display in the exact same order as the Excel sheet
            cols_order = ["System", "CP", "ρ(r)", "∇²ρ", "V(r_bcp)", "G(rcp)", "H(r)", "B.E. (kcal/mol)"]
            df = df[[c for c in cols_order if c in df.columns]]
            
            st.dataframe(df, use_container_width=True, hide_index=True)
