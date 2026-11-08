import streamlit as st
import os
import io
import re
import xlsxwriter
import pandas as pd

# Import from utils
from utils import format_nbo

def render():
    st.markdown('<div class="home-btn-container">', unsafe_allow_html=True)
    col_home, _ = st.columns([1, 6])
    with col_home:
        if st.button("🏠 Back to Home", type="secondary", key="home_nbo"): 
            st.session_state.app_mode = "Home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="main-header-container"><div class="main-title">⚛️ NBO E(2) Extractor</div><div class="sub-title">Parse and tabulate Natural Bond Orbital donor-acceptor interactions from log files.</div></div>', unsafe_allow_html=True)
    with st.container(border=True):
        col1, col2 = st.columns([1, 2])
        with col1: top_n = st.number_input("How many highest E(2) values needed per file?", min_value=1, max_value=50, value=1)
        with col2: allowed_sections = st.multiselect("Interaction types to consider (for highest values):", ["within unit 1", "from unit 1 to unit 2", "from unit 2 to unit 1", "within unit 2"], default=["from unit 1 to unit 2", "from unit 2 to unit 1"])
        nbo_files = st.file_uploader("Upload NBO log files (.log, .out)", accept_multiple_files=True)
    st.divider()
    if 'calc_done_nbo' not in st.session_state:
        st.session_state.calc_done_nbo = False
        st.session_state.excel_data_nbo = None
        st.session_state.all_top_n = []
        st.session_state.file_data_dict = {}
        st.session_state.warnings_nbo = []

    btn_placeholder = st.empty()
    do_nbo_run = False
    with btn_placeholder.container():
        if not st.session_state.calc_done_nbo:
            col_s1, col_btn, col_s2 = st.columns([1, 1, 1])
            with col_btn:
                if st.button("Extract NBO Data", type="primary", use_container_width=True): do_nbo_run = True
        else:
            col_s1, col_calc, col_down, col_s2 = st.columns([2, 3, 3, 2])
            with col_calc:
                if st.button("Extract NBO Data", type="primary", use_container_width=True): do_nbo_run = True
            with col_down:
                st.download_button("Download NBO Report (.xlsx)", data=st.session_state.excel_data_nbo, file_name="NBO_Batch_Results.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="secondary")

    if do_nbo_run:
        if not nbo_files:
            st.error("Please upload NBO files.")
        else:
            st.session_state.warnings_nbo = [] 
            
            file_data_dict = {}
            all_top_n_data = []
            for uploaded_file in nbo_files:
                uploaded_file.seek(0)
                lines = uploaded_file.read().decode('utf-8').splitlines()
                basename = os.path.splitext(uploaded_file.name)[0]
                file_extracted_data = []
                in_target_section = False
                found_perturbation = False
                
                for line in lines:
                    if "Second Order Perturbation Theory Analysis of Fock Matrix in NBO Basis" in line:
                        in_target_section = True
                        found_perturbation = True
                        continue
                    if in_target_section:
                        if "Natural Bond Orbitals (Summary):" in line: break
                        line_stripped = line.strip()
                        if line_stripped.startswith("within unit") or line_stripped.startswith("from unit"):
                            current_section = re.sub(r'\s+', ' ', line_stripped); continue
                        if '/' in line:
                            parts = line.split('/')
                            donor_raw = parts[0].strip()
                            right_tokens = parts[1].strip().split()
                            if len(right_tokens) >= 4:
                                donor_fmt = format_nbo(donor_raw)
                                acceptor_fmt = format_nbo(" ".join(right_tokens[1:-3]))
                                if not any(term in donor_fmt for term in ["RY*", "CR"]) and not any(term in acceptor_fmt for term in ["RY*", "CR"]):
                                    file_extracted_data.append([basename, current_section, donor_fmt, acceptor_fmt, float(right_tokens[-3]), float(right_tokens[-2]), float(right_tokens[-1])])
                
                if not found_perturbation:
                    st.session_state.warnings_nbo.append(f"Perturbation table is not found in {uploaded_file.name}.")
                elif not file_extracted_data:
                    st.session_state.warnings_nbo.append(f"No valid donor-acceptor interactions extracted from {uploaded_file.name}.")
                else:
                    file_data_dict[basename] = file_extracted_data
                    filtered = [r for r in file_extracted_data if r[1] in allowed_sections]
                    all_top_n_data.extend(sorted(filtered, key=lambda r: r[4], reverse=True)[:top_n])
                    
            if not all_top_n_data:
                st.error("NBO extraction failed. No valid data found in the provided files.")
                st.stop()
                
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
            center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
            left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
            if all_top_n_data:
                ws_top = workbook.add_worksheet(f'Top {top_n} Interactions')
                top_n_columns = ["System", "Interaction Section", "Donor NBO (i)", "Acceptor NBO (j)", "E(2) kcal/mol", "E(j)-E(i) a.u.", "F(i,j) a.u."]
                ws_top.set_row(0, 20)
                for col_num, header in enumerate(top_n_columns): ws_top.write(0, col_num, header, header_format)
                ws_top.set_column('A:A', 20); ws_top.set_column('B:B', 30); ws_top.set_column('C:D', 35); ws_top.set_column('E:G', 15)
                for row_num, row_data in enumerate(all_top_n_data, start=1):
                    ws_top.set_row(row_num, 20)
                    for col_num in range(4): ws_top.write(row_num, col_num, row_data[col_num], left_format)
                    for col_num in range(4, 7): ws_top.write_number(row_num, col_num, row_data[col_num], center_format)
            workbook.close()
            st.session_state.all_top_n = all_top_n_data
            st.session_state.excel_data_nbo = output.getvalue()
            st.session_state.calc_done_nbo = True
            st.rerun()
            
    if st.session_state.calc_done_nbo:
        st.write("") 
        for w in st.session_state.warnings_nbo:
            st.warning(w)
            
        if st.session_state.all_top_n:
            st.dataframe(pd.DataFrame(st.session_state.all_top_n, columns=["System", "Interaction Section", "Donor (i)", "Acceptor (j)", "E(2) kcal/mol", "E(j)-E(i) a.u.", "F(i,j) a.u."]), use_container_width=True)
