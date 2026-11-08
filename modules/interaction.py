import streamlit as st
import io
import xlsxwriter
import pandas as pd
from decimal import Decimal

# Import from your utils file
from utils import extract_energy, HARTREE_TO_KCAL

def render():
    st.markdown('<div class="home-btn-container">', unsafe_allow_html=True)
    col_home, _ = st.columns([1, 6])
    with col_home:
        if st.button("🏠 Back to Home", type="secondary", key="home_ie"): 
            st.session_state.app_mode = "Home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="main-header-container"><div class="main-title">🔬 Interaction Energy Extractor</div><div class="sub-title">Automated extraction and computation of ΔE from Gaussian log files.</div></div>', unsafe_allow_html=True)

    col_left, col_right = st.columns(2)
    with col_left:
        with st.container(border=True):
            st.markdown('<p class="section-header">1. Primary Reference System</p>', unsafe_allow_html=True)
            m1_file = st.file_uploader("Upload Monomer 1 (e.g., Amino Acid)", type=["log", "out"])
    with col_right:
        with st.container(border=True):
            st.markdown('<p class="section-header">2. Secondary Systems</p>', unsafe_allow_html=True)
            num_systems = st.number_input("Number of secondary systems:", min_value=1, max_value=20, value=1)
            bsse_choice = st.radio("BSSE Calculated?", ["No", "Yes"], horizontal=True)
            is_bsse = (bsse_choice == "Yes")

    st.write("") 
    systems_data = []
    for i in range(num_systems):
        with st.container(border=True):
            st.markdown(f"**System Type {i+1}**")
            col1, col2, col3 = st.columns([2, 1, 3])
            with col1: m2 = st.file_uploader(f"Upload Monomer 2", type=["log", "out"], key=f"ie_m2_{i}")
            with col2: n_m2 = st.number_input(f"Quantity (n)", min_value=1, max_value=50, value=1, key=f"ie_qty_{i}")
            with col3: comps = st.file_uploader(f"Upload corresponding Complexes", type=["log", "out"], accept_multiple_files=True, key=f"ie_comps_{i}")
            systems_data.append({"m2": m2, "multiplier": Decimal(n_m2), "complexes": comps})

    st.divider()

    if 'calc_done_ie' not in st.session_state:
        st.session_state.calc_done_ie = False
        st.session_state.results_ie = []
        st.session_state.excel_data_ie = None
        st.session_state.download_name_ie = ""
        st.session_state.warnings_ie = []

    btn_placeholder = st.empty()
    do_calc = False

    with btn_placeholder.container():
        if not st.session_state.calc_done_ie:
            col_s1, col_btn, col_s2 = st.columns([1, 1, 1])
            with col_btn:
                if st.button("Extract Data & Tabulate", type="primary", use_container_width=True): do_calc = True
        else:
            col_s1, col_calc, col_down, col_s2 = st.columns([2, 3, 3, 2])
            with col_calc:
                if st.button("Extract Data & Tabulate", type="primary", use_container_width=True): do_calc = True
            with col_down:
                st.download_button("Download Data (.xlsx)", data=st.session_state.excel_data_ie, file_name=st.session_state.download_name_ie, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="secondary")

    if do_calc:
        if not m1_file:
            st.error("Please upload Monomer 1.")
        else:
            with st.spinner("Processing..."):
                st.session_state.warnings_ie = [] 
                
                e_m1 = extract_energy(m1_file, is_bsse=False)
                if e_m1 is None: 
                    st.error(f"HF= energy is not found in {m1_file.name}.")
                    st.stop()
                    
                results = []
                is_first_in_sheet = True
                
                for idx, sys in enumerate(systems_data):
                    if not sys["m2"] or not sys["complexes"]: continue
                    
                    e_m2_single = extract_energy(sys["m2"], is_bsse=False) 
                    if e_m2_single is None: 
                        st.error(f"HF= energy is not found in {sys['m2'].name}. Skipping system.")
                        continue
                        
                    e_m2_total = e_m2_single * sys["multiplier"]
                    group_results = []
                    
                    for d_file in sys["complexes"]:
                        e_dimer = extract_energy(d_file, is_bsse=is_bsse)
                        if e_dimer is not None:
                            delta_au = e_dimer - (e_m1 + e_m2_total)
                            group_results.append({
                                "Complex File": d_file.name, "E Complex (a.u.)": e_dimer, "Monomer 1 File": m1_file.name,
                                "E Monomer 1 (a.u.)": e_m1, "Monomer 2 File": sys["m2"].name, "Qty": int(sys["multiplier"]),
                                "E Monomer 2 (single a.u.)": e_m2_single, "ΔE (a.u.)": delta_au, "ΔE (kcal/mol)": delta_au * HARTREE_TO_KCAL
                            })
                        else:
                            if is_bsse:
                                st.session_state.warnings_ie.append(f"Counterpoise corrected energy is not found in {d_file.name}.")
                            else:
                                st.session_state.warnings_ie.append(f"HF= energy is not found in {d_file.name}.")
                            
                    if group_results:
                        min_kcal = min(r["ΔE (kcal/mol)"] for r in group_results)
                        for i, r in enumerate(group_results):
                            r["Is_Best"] = (r["ΔE (kcal/mol)"] == min_kcal)
                            r["Is_First_In_Group"] = (i == 0)
                            r["Is_First_In_Sheet"] = is_first_in_sheet
                            results.append(r)
                            is_first_in_sheet = False

                if not results:
                    st.error("Calculations aborted. No valid interaction energies could be extracted from the uploaded files.")
                    st.stop()

                output = io.BytesIO()
                workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                worksheet = workbook.add_worksheet("Interaction Energies")
                header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
                center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
                left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
                highlight_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FFFF00', 'font_name': 'Times New Roman', 'font_size': 12})
                
                columns = ["Complex File", "E Complex (a.u.)", "Monomer 1 File", "E Monomer 1 (a.u.)", "Monomer 2 File", "Qty", "E Monomer 2 (single a.u.)", "ΔE (a.u.)", "ΔE (kcal/mol)"]
                worksheet.set_row(0, 24)
                for col_num, header in enumerate(columns): worksheet.write(0, col_num, header, header_format)
                worksheet.set_column('A:B', 22); worksheet.set_column('C:D', 22); worksheet.set_column('E:E', 20); worksheet.set_column('F:F', 8); worksheet.set_column('G:G', 25); worksheet.set_column('H:I', 18)
                
                for row_num, row_data in enumerate(results, start=1):
                    worksheet.set_row(row_num, 20)
                    worksheet.write(row_num, 0, row_data["Complex File"], left_format)
                    worksheet.write_number(row_num, 1, float(row_data["E Complex (a.u.)"]), center_format)
                    if row_data["Is_First_In_Sheet"]:
                        worksheet.write(row_num, 2, row_data["Monomer 1 File"], left_format)
                        worksheet.write_number(row_num, 3, float(row_data["E Monomer 1 (a.u.)"]), center_format)
                    else:
                        worksheet.write(row_num, 2, "", left_format); worksheet.write(row_num, 3, "", center_format)
                    if row_data["Is_First_In_Group"]:
                        worksheet.write(row_num, 4, row_data["Monomer 2 File"], left_format)
                        worksheet.write_number(row_num, 5, row_data["Qty"], center_format)
                        worksheet.write_number(row_num, 6, float(row_data["E Monomer 2 (single a.u.)"]), center_format)
                    else:
                        worksheet.write(row_num, 4, "", left_format); worksheet.write(row_num, 5, "", center_format); worksheet.write(row_num, 6, "", center_format)
                    worksheet.write_number(row_num, 7, float(row_data["ΔE (a.u.)"]), center_format)
                    fmt = highlight_format if row_data["Is_Best"] else center_format
                    worksheet.write_number(row_num, 8, float(row_data["ΔE (kcal/mol)"]), fmt)
                            
                workbook.close()
                st.session_state.results_ie = results
                st.session_state.excel_data_ie = output.getvalue()
                st.session_state.download_name_ie = f"{m1_file.name.split('.')[0]}_Energies.xlsx"
                st.session_state.calc_done_ie = True
                st.rerun()

    if st.session_state.calc_done_ie:
        for w in st.session_state.warnings_ie:
            st.warning(w)
            
        st.markdown('<p class="section-header" style="text-align: center; border: none;">Tabulated Results</p>', unsafe_allow_html=True)
        
        display_df = pd.DataFrame(st.session_state.results_ie).drop(columns=["Is_Best", "Is_First_In_Sheet", "Is_First_In_Group"])
        cols_to_float = ["E Complex (a.u.)", "E Monomer 1 (a.u.)", "E Monomer 2 (single a.u.)", "ΔE (a.u.)", "ΔE (kcal/mol)"]
        for col in cols_to_float:
            if col in display_df.columns:
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce')
                
        def highlight_best(row):
            if st.session_state.results_ie[row.name]["Is_Best"]: return ['background-color: #FEF08A; color: #1F2937; font-weight: bold'] * len(row)
            return [''] * len(row)
            
        styled_df = display_df.style.apply(highlight_best, axis=1).format(precision=6)
        st.dataframe(styled_df, use_container_width=True)
