import streamlit as st
import os
import io
import xlsxwriter
from decimal import Decimal

# Import from utils
from utils import extract_led_values, HARTREE_TO_KCAL

def render():
    st.markdown('<div class="home-btn-container">', unsafe_allow_html=True)
    col_home, _ = st.columns([1, 6])
    with col_home:
        if st.button("🏠 Back to Home", type="secondary", key="home_led"): 
            st.session_state.app_mode = "Home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
            
    st.markdown('<div class="main-header-container"><div class="main-title">📊 Local Energy Decomposition (LED) Parser</div><div class="sub-title">Parse Orca DLPNO-CCSD(T) output to decompose interaction energies.</div></div>', unsafe_allow_html=True)
    
    num_led_systems = st.number_input("How many systems to evaluate?", min_value=1, max_value=10, value=1)
    
    led_inputs = []
    global_m1 = None
    
    for i in range(num_led_systems):
        with st.container(border=True):
            header_placeholder = st.empty()
            d_file = st.file_uploader(f"Upload Dimer/Complex File", type=["log", "out"], key=f"led_dimer_{i}")
            
            if d_file:
                sys_name = os.path.splitext(d_file.name)[0]
                header_placeholder.markdown(f'<p class="section-header">System {i+1} Configuration: <span style="color:#2563EB;">{sys_name}</span></p>', unsafe_allow_html=True)
            else:
                sys_name = f"System_{i+1}"
                header_placeholder.markdown(f'<p class="section-header">System {i+1} Configuration</p>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if i == 0:
                    m1_file = st.file_uploader(f"Upload Monomer 1", type=["log", "out"], key=f"led_m1_{i}")
                    global_m1 = m1_file
                else:
                    use_global_m1 = st.checkbox(f"Use same Monomer 1 as System 1", value=True, key=f"led_use_m1_{i}")
                    if use_global_m1:
                        m1_file = global_m1
                        st.info("Using Monomer 1 from System 1")
                    else:
                        m1_file = st.file_uploader(f"Upload Monomer 1 for this system", type=["log", "out"], key=f"led_m1_{i}")
                
                f1_file = st.file_uploader(f"Upload Fragment 1 (Dimer geometry)", type=["log", "out"], key=f"led_f1_{i}")
                
            with col2:
                m2_file = st.file_uploader(f"Upload Monomer 2", type=["log", "out"], key=f"led_m2_{i}")
                f2_file = st.file_uploader(f"Upload Fragment 2 (Dimer geometry)", type=["log", "out"], key=f"led_f2_{i}")
            
            led_inputs.append({"System_Name": sys_name, "m1": m1_file, "m2": m2_file, "f1": f1_file, "f2": f2_file, "d": d_file})

    st.divider()
    
    if 'calc_done_led' not in st.session_state:
        st.session_state.calc_done_led = False
        st.session_state.excel_data_led = None
        st.session_state.warnings_led = []

    btn_placeholder = st.empty()
    do_led_calc = False

    with btn_placeholder.container():
        if not st.session_state.calc_done_led:
            col_s1, col_btn, col_s2 = st.columns([1, 1, 1])
            with col_btn:
                if st.button("Parse LED Data", type="primary", use_container_width=True): do_led_calc = True
        else:
            col_s1, col_calc, col_down, col_s2 = st.columns([2, 3, 3, 2])
            with col_calc:
                if st.button("Parse LED Data", type="primary", use_container_width=True): do_led_calc = True
            with col_down:
                st.download_button("Download LED Report (.xlsx)", data=st.session_state.excel_data_led, file_name="LED_Batch_Results.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="secondary")

    if do_led_calc:
        with st.spinner("Parsing Orca outputs..."):
            st.session_state.warnings_led = []
            
            base_energy = ["FINAL SINGLE POINT ENERGY"]
            triples_term = ["Triples Correction (T)"] 
            fragment_terms = ["E(CORR)(corrected)"] 
            monomer_terms = ["E(0)"] 
            dimer_terms = [
                "Intra REF. energy", "Electrostatics (REF.)", "Exchange (REF.)",
                "Non dispersion (strong pairs)", "Non dispersion (weak pairs)",
                "Dispersion (strong pairs)", "Dispersion (weak pairs)"
            ]
            
            unique_extracted_data = {}
            all_calculations = []
            
            for sys in led_inputs:
                d_file = sys["d"]
                f1_file = sys["f1"]
                f2_file = sys["f2"]
                m1_file = sys["m1"]
                m2_file = sys["m2"]
                
                if not all([d_file, f1_file, f2_file, m1_file, m2_file]):
                    st.error(f"Missing files for System '{sys['System_Name']}'. Skipping.")
                    continue
                
                file_mapping = [
                    (d_file, "Dimer", base_energy + triples_term + dimer_terms),
                    (f1_file, "Fragment 1", base_energy + fragment_terms),
                    (f2_file, "Fragment 2", base_energy + fragment_terms),
                    (m1_file, "True Monomer 1", base_energy + triples_term + monomer_terms),
                    (m2_file, "True Monomer 2", base_energy + triples_term + monomer_terms)
                ]
                
                sys_dict_refs = {}
                for fileobj, ftype, terms in file_mapping:
                    if fileobj.name not in unique_extracted_data:
                        data = {"Filename": fileobj.name, "Type": ftype}
                        extracted = extract_led_values(fileobj, terms)
                        
                        for term in terms:
                            if term == "Intra REF. energy":
                                if "Intra REF. energy of Fragment 1" not in extracted or "Intra REF. energy of Fragment 2" not in extracted:
                                    st.session_state.warnings_led.append(f"'{term}' is missing or incomplete in {fileobj.name}.")
                            else:
                                if term not in extracted:
                                    st.session_state.warnings_led.append(f"'{term}' is not found in {fileobj.name}.")
                                    
                        data.update(extracted)
                        unique_extracted_data[fileobj.name] = data
                    sys_dict_refs[ftype] = unique_extracted_data[fileobj.name]
                
                calc = {"System": sys["System_Name"]}
                res_d = sys_dict_refs["Dimer"]
                res_f1 = sys_dict_refs["Fragment 1"]
                res_f2 = sys_dict_refs["Fragment 2"]
                res_m1 = sys_dict_refs["True Monomer 1"]
                res_m2 = sys_dict_refs["True Monomer 2"]

                prep_energy = el_prep = electrostatics = exchange = delta_e_no_disp = e_disp = delta_t_int = Decimal('0.0')

                try:
                    prep_energy = (res_f1["FINAL SINGLE POINT ENERGY"] + res_f2["FINAL SINGLE POINT ENERGY"]) - (res_m1["FINAL SINGLE POINT ENERGY"] + res_m2["FINAL SINGLE POINT ENERGY"])
                    calc["Delta E geo-prep"] = prep_energy * HARTREE_TO_KCAL
                except KeyError: pass
                try:
                    delta_t_int = res_d["Triples Correction (T)"] - res_m1["Triples Correction (T)"] - res_m2["Triples Correction (T)"]
                    calc["Delta E C-(T) int"] = delta_t_int * HARTREE_TO_KCAL
                except KeyError: pass
                try:
                    el_prep = (res_d["Intra REF. energy of Fragment 1"] - res_m1["E(0)"]) + (res_d["Intra REF. energy of Fragment 2"] - res_m2["E(0)"])
                    calc["Delta E ref el-prep"] = el_prep * HARTREE_TO_KCAL
                except KeyError: pass
                try:
                    electrostatics = res_d["Electrostatics (REF.)"]
                    calc["Electrostatics (REF.)"] = electrostatics * HARTREE_TO_KCAL
                except KeyError: pass
                try:
                    exchange = res_d["Exchange (REF.)"]
                    calc["Exchange (REF.)"] = exchange * HARTREE_TO_KCAL
                except KeyError: pass
                try:
                    delta_e_no_disp = (res_d["Non dispersion (strong pairs)"] + res_d["Non dispersion (weak pairs)"]) - res_f1["E(CORR)(corrected)"] - res_f2["E(CORR)(corrected)"]
                    calc["Delta E C-CCSD no-disp"] = delta_e_no_disp * HARTREE_TO_KCAL
                except KeyError: pass
                try:
                    e_disp = res_d["Dispersion (strong pairs)"] + res_d["Dispersion (weak pairs)"]
                    calc["E C-CCSD disp"] = e_disp * HARTREE_TO_KCAL
                except KeyError: pass
                
                calc["Total Delta E"] = (prep_energy + el_prep + electrostatics + exchange + delta_e_no_disp + e_disp + delta_t_int) * HARTREE_TO_KCAL
                all_calculations.append(calc)

            if not all_calculations:
                st.error("No valid LED data could be parsed. Check warnings above.")
                st.session_state.calc_done_led = False
                st.stop()

            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
            center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
            left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 12})
            
            # RAW VALUES TAB
            ws_values = workbook.add_worksheet('Extracted Values')
            all_val_keys = set()
            for data in unique_extracted_data.values(): all_val_keys.update(data.keys())
            val_columns = ["Filename", "Type"] + sorted([k for k in all_val_keys if k not in ["Filename", "Type"]])
            ws_values.set_row(0, 20)
            for col_num, header in enumerate(val_columns): ws_values.write(0, col_num, header, header_format)
            ws_values.set_column('A:B', 25)
            ws_values.set_column(2, len(val_columns)-1, 20)
            for row_num, data in enumerate(unique_extracted_data.values(), start=1):
                ws_values.set_row(row_num, 20)
                for col_num, col_name in enumerate(val_columns):
                    val = data.get(col_name, "")
                    cell_fmt = left_format if col_num < 2 else center_format
                    if isinstance(val, Decimal): ws_values.write_number(row_num, col_num, float(val), cell_fmt)
                    else: ws_values.write(row_num, col_num, str(val), cell_fmt)

            # CALCULATIONS TAB
            ws_calcs = workbook.add_worksheet('Tabulated Data (kcal per mol)')
            calc_columns = list(all_calculations[0].keys())
            sup = workbook.add_format({'bold': True, 'font_script': 1, 'font_name': 'Times New Roman', 'font_size': 12})
            sub = workbook.add_format({'bold': True, 'font_script': 2, 'font_name': 'Times New Roman', 'font_size': 12})
            bold = workbook.add_format({'bold': True, 'font_name': 'Times New Roman', 'font_size': 12})
            header_base = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
            
            rich_headers = {
                "System": [bold, "System"],
                "Delta E geo-prep": [bold, "ΔE", sub, "geo-prep"],
                "Delta E C-(T) int": [bold, "ΔE", sup, "C-(T)", sub, "int"],
                "Delta E ref el-prep": [bold, "ΔE", sup, "ref", sub, "el-prep"],
                "Electrostatics (REF.)": [bold, "E", sup, "ref", sub, "elstat"],
                "Exchange (REF.)": [bold, "E", sup, "ref", sub, "exch"],
                "Delta E C-CCSD no-disp": [bold, "ΔE", sup, "C-CCSD", sub, "no-disp"],
                "E C-CCSD disp": [bold, "E", sup, "C-CCSD", sub, "disp"],
                "Total Delta E": [bold, "ΔE"]
            }
            ws_calcs.set_row(0, 20)
            for col_num, header_key in enumerate(calc_columns):
                if header_key in rich_headers:
                    parts = rich_headers[header_key]
                    if len(parts) == 2: ws_calcs.write(0, col_num, parts[1], header_format)
                    else: ws_calcs.write_rich_string(0, col_num, *parts, header_base)
                else:
                    ws_calcs.write(0, col_num, header_key, header_format)
            ws_calcs.set_column(0, 0, 25)
            if len(calc_columns) > 1: ws_calcs.set_column(1, len(calc_columns)-1, 20)
            for row_num, calc_data in enumerate(all_calculations, start=1):
                ws_calcs.set_row(row_num, 20)
                for col_num, col_name in enumerate(calc_columns):
                    val = calc_data.get(col_name, "")
                    cell_fmt = left_format if col_num == 0 else center_format
                    if isinstance(val, Decimal): ws_calcs.write_number(row_num, col_num, float(val), cell_fmt)
                    else: ws_calcs.write(row_num, col_num, str(val), cell_fmt)

            workbook.close()
            st.session_state.excel_data_led = output.getvalue()
            st.session_state.calc_done_led = True
            st.rerun()
            
    if st.session_state.calc_done_led:
        for w in st.session_state.warnings_led:
            st.warning(w)
