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
    
    # Initialize session states
    if 'calc_done_nbo' not in st.session_state:
        st.session_state.calc_done_nbo = False
        st.session_state.excel_data_nbo = None
        st.session_state.all_top_n = []
        st.session_state.file_data_dict = {}
        st.session_state.warnings_nbo = []
        st.session_state.file_errors_nbo = [] # New list to hold critical file errors

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
            st.session_state.file_errors_nbo = [] # Reset errors on new run
            
            file_data_dict = {}
            all_top_n_data = []
            
            for uploaded_file in nbo_files:
                uploaded_file.seek(0)
                
                # --- NEW TRY/EXCEPT BLOCK FOR ERROR CATCHING ---
                try:
                    lines = uploaded_file.read().decode('utf-8').splitlines()
                except UnicodeDecodeError as e:
                    # Catch the exact file and error, store it to show the user
                    error_msg = f"Encoding Error in **{uploaded_file.name}**: {e}. (Falling back to 'ignore' mode to salvage readable data)"
                    st.session_state.file_errors_nbo.append(error_msg)
                    
                    # Fall back to ignoring bad characters so it doesn't crash
                    uploaded_file.seek(0)
                    lines = uploaded_file.read().decode('utf-8', errors='ignore').splitlines()
                except Exception as e:
                    # Catch any other weird file reading errors completely
                    st.session_state.file_errors_nbo.append(f"Unexpected error reading **{uploaded_file.name}**: {e}")
                    continue # Skip this file completely if it's utterly broken
                # -----------------------------------------------

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
            
            # --- Format Declarations ---
            header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
            center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
            left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
            section_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
            
            # --- 1. Write the Top N Summary Sheet ---
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
            
            # --- 2. Write Individual Sheets for EVERY File ---
            indiv_columns = ["Donor NBO (i)", "Acceptor NBO (j)", "E(2) kcal/mol", "E(j)-E(i) a.u.", "F(i,j) a.u."]
            
            for filename, all_file_data in file_data_dict.items():
                safe_sheet_name = str(filename)[:31]
                ws_file = workbook.add_worksheet(safe_sheet_name)
                ws_file.set_row(0, 20)
                
                for col_num, header in enumerate(indiv_columns): 
                    ws_file.write(0, col_num, header, header_format)
                ws_file.set_column('A:B', 35); ws_file.set_column('C:E', 15)
                
                current_excel_row = 1
                last_section = None
                
                for row_data in all_file_data:
                    current_section = row_data[1]
                    
                    if current_section != last_section:
                        ws_file.set_row(current_excel_row, 20)
                        ws_file.write(current_excel_row, 0, current_section, section_format)
                        current_excel_row += 1
                        last_section = current_section
                    
                    ws_file.set_row(current_excel_row, 20)
                    ws_file.write(current_excel_row, 0, row_data[2], left_format) 
                    ws_file.write(current_excel_row, 1, row_data[3], left_format) 
                    ws_file.write_number(current_excel_row, 2, row_data[4], center_format)
                    ws_file.write_number(current_excel_row, 3, row_data[5], center_format)
                    ws_file.write_number(current_excel_row, 4, row_data[6], center_format)
                    current_excel_row += 1
                    
            workbook.close()
            
            st.session_state.all_top_n = all_top_n_data
            st.session_state.excel_data_nbo = output.getvalue()
            st.session_state.calc_done_nbo = True
            st.rerun()
            
    if st.session_state.calc_done_nbo:
        st.write("") 
        
        # Display the critical file errors clearly in red
        for err in st.session_state.file_errors_nbo:
            st.error(err)
            
        # Display the standard warnings in yellow
        for w in st.session_state.warnings_nbo:
            st.warning(w)
            
        if st.session_state.all_top_n:
            st.markdown('**Summary: Top Interactions Across All Files** *(Download Excel for full data per file)*')
            st.dataframe(pd.DataFrame(st.session_state.all_top_n, columns=["System", "Interaction Section", "Donor (i)", "Acceptor (j)", "E(2) kcal/mol", "E(j)-E(i) a.u.", "F(i,j) a.u."]), use_container_width=True)
