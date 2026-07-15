import strstreamlit run re_toolkit/streamlit_app.pyeamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io
import uuid

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'validation'
if 'data' not in st.session_state:
    st.session_state.data = None
if 'results' not in st.session_state:
    st.session_state.results = None
if 'table_assignments' not in st.session_state:
    st.session_state.table_assignments = {}
if 'header_mappings' not in st.session_state:
    st.session_state.header_mappings = {}
if 'edited_data' not in st.session_state:
    st.session_state.edited_data = {}

# Custom CSS for professional UI
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        background-color: #003087;
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: bold;
        transition: background-color 0.2s;
    }
    .stButton>button:hover {
        background-color: #0053c1;
    }
    .stSelectbox, .stNumberInput, .stTextInput {
        background-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        padding: 5px;
    }
    .stMarkdown h1 {
        color: #003087;
        font-family: 'Arial', sans-serif;
        font-size: 2.5em;
        margin-bottom: 0.5em;
    }
    .stMarkdown h2, .stMarkdown h3 {
        color: #004a6f;
        font-family: 'Arial', sans-serif;
    }
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .stDataFrame {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

def detect_tables(sheet_df):
    sheet_df = sheet_df.fillna('')
    tables = []
    
    # Detect PVT and RelPerm tables
    for i in range(len(sheet_df)):
        row = sheet_df.iloc[i]
        headers = [str(col).lower().strip() for col in row if str(col).strip()]
        if any(h in headers for h in ['psat', 'pressure', 'po', 'p', 'bo', 'rs', 'gor', 'viso', 'vsco', 'bgdry', 'bgwet', 'sg', 'krg', 'kro', 'pcgo', 'sw', 'krw', 'pcow']):
            start_idx = i + 1
            end_idx = sheet_df[i+1:].index[sheet_df[i+1:].apply(lambda r: any('endtable' in str(c).lower() or 'table' in str(c).lower() for c in r), axis=1)]
            end_idx = end_idx[0] if end_idx.size > 0 else len(sheet_df)
            table_data = sheet_df.iloc[start_idx:end_idx]
            table_data = table_data.loc[:, table_data.columns.notnull()]
            if not table_data.empty and len(table_data.columns) >= 4:
                if any(h in headers for h in ['psat', 'bo', 'rs', 'gor', 'vsco', 'viso']):
                    guessed_type = 'satoil'
                elif any(h in headers for h in ['bgdry', 'bgwet', 'vscgdry', 'vscgwet']):
                    guessed_type = 'wetgastable'
                elif any(h in headers for h in ['sg', 'krg', 'kro', 'pcgo']):
                    guessed_type = 'sgof'
                elif any(h in headers for h in ['sw', 'krw', 'kro', 'pcow']):
                    guessed_type = 'swof'
                else:
                    guessed_type = 'unknown'
                tables.append((guessed_type, table_data, headers))
    
    return tables

def validate_data(tables, sheet_name):
    errors = []
    for table_type, df, headers in tables:
        if table_type == 'satoil':
            required = ['Pressure', 'Bo', 'Rs', 'Viscosity']
        elif table_type == 'wetgastable':
            required = ['Pressure', 'Bgdry', 'VscGdry', 'Bgwet', 'rs', 'VscGwet']
        elif table_type == 'sgof':
            required = ['Sg', 'Krg', 'Kro', 'Pcgo']
        elif table_type == 'swof':
            required = ['Sw', 'Krw', 'Kro', 'Pcow']
        else:
            continue
        mapped_headers = st.session_state.header_mappings.get(f"{sheet_name}_{table_type}", {})
        actual_headers = [mapped_headers.get(h, h) for h in headers]
        if not all(h in actual_headers for h in required):
            errors.append(f"Missing required headers in {sheet_name} {table_type} table: {required}")
        try:
            df = df.astype(float)
            if (df < 0).any().any() and table_type in ['satoil', 'wetgastable', 'sgof', 'swof']:
                errors.append(f"Negative values detected in {sheet_name} {table_type} table")
            if table_type in ['sgof', 'swof']:
                saturation_col = 'Sg' if table_type == 'sgof' else 'Sw'
                if not (df[saturation_col] >= 0).all() or not (df[saturation_col] <= 1).all():
                    errors.append(f"Saturation values ({saturation_col}) in {sheet_name} {table_type} table must be between 0 and 1")
        except:
            errors.append(f"Non-numeric data in {sheet_name} {table_type} table")
    return errors

def process_data(df, bo_factor, rs_factor, visco_factor, bgwet_factor, rs_gas_factor, krg_factor, krw_factor, kro_factor, ecl_oil_vol, mores_oil_vol, ecl_gas_vol, mores_gas_vol, rs_unit, table_assignments, header_mappings, edited_data):
    results = {}
    pvt_fig = go.Figure()
    relperm_fig = go.Figure()

    for sheet_name, sheet_df in df.items():
        tables = detect_tables(sheet_df)
        for table_type, table_data, headers in tables:
            assigned_type = table_assignments.get(f"{sheet_name}_{table_type}", table_type)
            if assigned_type == 'ignore':
                continue
            mapped_headers = header_mappings.get(f"{sheet_name}_{table_type}", {h: h for h in headers})
            table_data.columns = [mapped_headers.get(str(h), str(h)) for h in headers]
            
            # Apply edited data
            edited_key = f"{sheet_name}_{table_type}"
            if edited_key in edited_data:
                table_data = edited_data[edited_key].copy()
            
            table_data = table_data[pd.to_numeric(table_data[('Pressure' if assigned_type in ['satoil', 'wetgastable'] else 'Sg' if assigned_type == 'sgof' else 'Sw')], errors='coerce').notnull()]
            try:
                table_data = table_data.astype(float)
            except:
                st.error(f"Non-numeric data in {sheet_name} {assigned_type} table after editing.")
                return None, None, None

            if assigned_type == 'satoil':
                table_data_adjusted = table_data.copy()
                if rs_unit == "SCF/BBL":
                    table_data_adjusted['Rs'] = table_data_adjusted['Rs'] / 1_000_000
                    if (table_data_adjusted['Rs'] < 0).any():
                        st.warning(f"Negative Rs values detected in {sheet_name} satoil table after conversion.")
                table_data_adjusted['Bo_adjusted'] = table_data_adjusted['Bo'] * bo_factor
                table_data_adjusted['Rs_adjusted'] = table_data_adjusted['Rs'] * rs_factor
                table_data_adjusted['Viscosity_adjusted'] = table_data_adjusted['Viscosity'] * visco_factor

                if ecl_oil_vol and mores_oil_vol:
                    oil_vol_ref = ecl_oil_vol
                    try:
                        if abs((table_data_adjusted['Bo_adjusted'].iloc[0] * table_data_adjusted['Rs_adjusted'].iloc[0] * 1000) - oil_vol_ref) > 1e-6:
                            scale_factor = oil_vol_ref / (table_data_adjusted['Bo'].iloc[0] * table_data_adjusted['Rs'].iloc[0] * 1000)
                            table_data_adjusted['Bo_adjusted'] *= scale_factor
                            table_data_adjusted['Rs_adjusted'] *= scale_factor
                    except:
                        st.warning(f"Volume scaling failed for {sheet_name} satoil table.")

                pvt_fig.add_trace(go.Scatter(
                    x=table_data_adjusted['Pressure'], 
                    y=table_data_adjusted['Bo'], 
                    mode='lines+markers', 
                    name=f'{sheet_name} Original Bo', 
                    line=dict(color='blue', dash='dash')
                ))
                pvt_fig.add_trace(go.Scatter(
                    x=table_data_adjusted['Pressure'], 
                    y=table_data_adjusted['Bo_adjusted'], 
                    mode='lines+markers', 
                    name=f'{sheet_name} Adjusted Bo', 
                    line=dict(color='red')
                ))
                
                st.markdown(f"**Sample Adjusted Satoil ({sheet_name}):**")
                st.dataframe(table_data_adjusted[['Pressure', 'Bo_adjusted', 'Rs_adjusted', 'Viscosity_adjusted']].style.format("{:.6f}"))

                results[sheet_name + '_satoil'] = table_data_adjusted

            elif assigned_type == 'wetgastable':
                table_data_adjusted = table_data.copy()
                table_data_adjusted['Bgwet_adjusted'] = table_data_adjusted['Bgwet'] * bgwet_factor
                table_data_adjusted['rs_adjusted'] = table_data_adjusted['rs'] * rs_gas_factor

                if ecl_gas_vol and mores_gas_vol:
                    gas_vol_ref = ecl_gas_vol
                    try:
                        if abs((1 / table_data_adjusted['Bgwet_adjusted'].iloc[0] - 1 / table_data_adjusted['Bgwet'].iloc[0]) * gas_vol_ref * 1000) > 1e-6:
                            scale_factor = gas_vol_ref / (1 / table_data_adjusted['Bgwet'].iloc[0] * 1000)
                            table_data_adjusted['Bgwet_adjusted'] *= scale_factor
                            table_data_adjusted['rs_adjusted'] *= scale_factor
                    except:
                        st.warning(f"Volume scaling failed for {sheet_name} wetgastable.")

                pvt_fig.add_trace(go.Scatter(
                    x=table_data_adjusted['Pressure'], 
                    y=table_data_adjusted['Bgwet'], 
                    mode='lines+markers', 
                    name=f'{sheet_name} Original Bgwet', 
                    line=dict(color='green', dash='dash')
                ))
                pvt_fig.add_trace(go.Scatter(
                    x=table_data_adjusted['Pressure'], 
                    y=table_data_adjusted['Bgwet_adjusted'], 
                    mode='lines+markers', 
                    name=f'{sheet_name} Adjusted Bgwet', 
                    line=dict(color='orange')
                ))
                
                st.markdown(f"**Sample Adjusted Wetgastable ({sheet_name}):**")
                st.dataframe(table_data_adjusted[['Pressure', 'Bgwet_adjusted', 'rs_adjusted', 'VscGwet']].style.format("{:.6f}"))

                results[sheet_name + '_wetgastable'] = table_data_adjusted

            elif assigned_type == 'sgof':
                table_data_adjusted = table_data.copy()
                table_data_adjusted['Krg_adjusted'] = table_data_adjusted['Krg'] * krg_factor
                table_data_adjusted['Kro_adjusted'] = table_data_adjusted['Kro'] * kro_factor

                relperm_fig.add_trace(go.Scatter(
                    x=table_data_adjusted['Sg'], 
                    y=table_data_adjusted['Krg'], 
                    mode='lines+markers', 
                    name=f'{sheet_name} Original Krg', 
                    line=dict(color='purple', dash='dash')
                ))
                relperm_fig.add_trace(go.Scatter(
                    x=table_data_adjusted['Sg'], 
                    y=table_data_adjusted['Krg_adjusted'], 
                    mode='lines+markers', 
                    name=f'{sheet_name} Adjusted Krg', 
                    line=dict(color='violet')
                ))
                relperm_fig.add_trace(go.Scatter(
                    x=table_data_adjusted['Sg'], 
                    y=table_data_adjusted['Kro'], 
                    mode='lines+markers', 
                    name=f'{sheet_name} Original Kro', 
                    line=dict(color='brown', dash='dash')
                ))
                relperm_fig.add_trace(go.Scatter(
                    x=table_data_adjusted['Sg'], 
                    y=table_data_adjusted['Kro_adjusted'], 
                    mode='lines+markers', 
                    name=f'{sheet_name} Adjusted Kro', 
                    line=dict(color='orange')
                ))
                
                st.markdown(f"**Sample Adjusted SGOF ({sheet_name}):**")
                st.dataframe(table_data_adjusted[['Sg', 'Krg_adjusted', 'Kro_adjusted', 'Pcgo']].style.format("{:.6f}"))

                results[sheet_name + '_sgof'] = table_data_adjusted

            elif assigned_type == 'swof':
                table_data_adjusted = table_data.copy()
                table_data_adjusted['Krw_adjusted'] = table_data_adjusted['Krw'] * krw_factor
                table_data_adjusted['Kro_adjusted'] = table_data_adjusted['Kro'] * kro_factor

                relperm_fig.add_trace(go.Scatter(
                    x=table_data_adjusted['Sw'], 
                    y=table_data_adjusted['Krw'], 
                    mode='lines+markers', 
                    name=f'{sheet_name} Original Krw', 
                    line=dict(color='blue', dash='dash')
                ))
                relperm_fig.add_trace(go.Scatter(
                    x=table_data_adjusted['Sw'], 
                    y=table_data_adjusted['Krw_adjusted'], 
                    mode='lines+markers', 
                    name=f'{sheet_name} Adjusted Krw', 
                    line=dict(color='cyan')
                ))
                relperm_fig.add_trace(go.Scatter(
                    x=table_data_adjusted['Sw'], 
                    y=table_data_adjusted['Kro'], 
                    mode='lines+markers', 
                    name=f'{sheet_name} Original Kro', 
                    line=dict(color='brown', dash='dash')
                ))
                relperm_fig.add_trace(go.Scatter(
                    x=table_data_adjusted['Sw'], 
                    y=table_data_adjusted['Kro_adjusted'], 
                    mode='lines+markers', 
                    name=f'{sheet_name} Adjusted Kro', 
                    line=dict(color='orange')
                ))
                
                st.markdown(f"**Sample Adjusted SWOF ({sheet_name}):**")
                st.dataframe(table_data_adjusted[['Sw', 'Krw_adjusted', 'Kro_adjusted', 'Pcow']].style.format("{:.6f}"))

                results[sheet_name + '_swof'] = table_data_adjusted

    pvt_fig.update_layout(
        title="PVT Curves Across Sheets",
        xaxis_title="Pressure (PSI)",
        yaxis_title="Formation Volume Factor",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=600
    )
    relperm_fig.update_layout(
        title="Relative Permeability Curves Across Sheets",
        xaxis_title="Saturation",
        yaxis_title="Relative Permeability",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=600
    )

    return results, pvt_fig, relperm_fig

def export_data(results, simulator):
    output = io.StringIO()
    for key, df_adj in results.items():
        if 'satoil' in key:
            if simulator == "ECLIPSE":
                output.write("PVTO\n")
                output.write("-- Rs Po Bo cPo\n")
                for _, row in df_adj.iterrows():
                    output.write(f"{row['Rs_adjusted']:.6f} {row['Pressure']:.1f} {row['Bo_adjusted']:.4f} {row['Viscosity_adjusted']:.4f}\n")
                output.write("/\n\n")
            elif simulator == "CMG":
                output.write("*PVTO\n")
                output.write("*GOR PRESSURE BO VISCOSITY\n")
                for _, row in df_adj.iterrows():
                    output.write(f"{row['Rs_adjusted']:.6f} {row['Pressure']:.1f} {row['Bo_adjusted']:.4f} {row['Viscosity_adjusted']:.4f}\n")
                output.write("/\n\n")
            elif simulator == "Intersect":
                output.write("PVTO\n")
                output.write("-- Rs Po Bo cPo\n")
                for _, row in df_adj.iterrows():
                    output.write(f"{row['Rs_adjusted']:.6f} {row['Pressure']:.1f} {row['Bo_adjusted']:.4f} {row['Viscosity_adjusted']:.4f}\n")
                output.write("/\n\n")
        elif 'wetgastable' in key:
            if simulator == "ECLIPSE":
                output.write("PVTG\n")
                output.write("-- P rv Bg cPg\n")
                for _, row in df_adj.iterrows():
                    rv = row['rs_adjusted'] / 1000 if row['rs_adjusted'] > 0 else 0
                    output.write(f"{row['Pressure']:.1f} {rv:.6f} {row['Bgwet_adjusted']*1000:.6f} {row['VscGwet']:.6f}\n")
                output.write("/\n\n")
            elif simulator == "CMG":
                output.write("*PVTG\n")
                output.write("*PRESSURE RV BG VISCOSITY\n")
                for _, row in df_adj.iterrows():
                    rv = row['rs_adjusted'] / 1000 if row['rs_adjusted'] > 0 else 0
                    output.write(f"{row['Pressure']:.1f} {rv:.6f} {row['Bgwet_adjusted']*1000:.6f} {row['VscGwet']:.6f}\n")
                output.write("/\n\n")
            elif simulator == "Intersect":
                output.write("PVTG\n")
                output.write("-- P rv Bg cPg\n")
                for _, row in df_adj.iterrows():
                    rv = row['rs_adjusted'] / 1000 if row['rs_adjusted'] > 0 else 0
                    output.write(f"{row['Pressure']:.1f} {rv:.6f} {row['Bgwet_adjusted']*1000:.6f} {row['VscGwet']:.6f}\n")
                output.write("/\n\n")
        elif 'sgof' in key:
            if simulator == "ECLIPSE":
                output.write("SGOF\n")
                output.write("-- Sg Krg Kro Pcgo\n")
                for _, row in df_adj.iterrows():
                    output.write(f"{row['Sg']:.6f} {row['Krg_adjusted']:.6f} {row['Kro_adjusted']:.6f} {row['Pcgo']:.6f}\n")
                output.write("/\n\n")
            elif simulator == "CMG":
                output.write("*SGOF\n")
                output.write("*SG KRG KRO PCGO\n")
                for _, row in df_adj.iterrows():
                    output.write(f"{row['Sg']:.6f} {row['Krg_adjusted']:.6f} {row['Kro_adjusted']:.6f} {row['Pcgo']:.6f}\n")
                output.write("/\n\n")
            elif simulator == "Intersect":
                output.write("SGOF\n")
                output.write("-- Sg Krg Kro Pcgo\n")
                for _, row in df_adj.iterrows():
                    output.write(f"{row['Sg']:.6f} {row['Krg_adjusted']:.6f} {row['Kro_adjusted']:.6f} {row['Pcgo']:.6f}\n")
                output.write("/\n\n")
        elif 'swof' in key:
            if simulator == "ECLIPSE":
                output.write("SWOF\n")
                output.write("-- Sw Krw Kro Pcow\n")
                for _, row in df_adj.iterrows():
                    output.write(f"{row['Sw']:.6f} {row['Krw_adjusted']:.6f} {row['Kro_adjusted']:.6f} {row['Pcow']:.6f}\n")
                output.write("/\n\n")
            elif simulator == "CMG":
                output.write("*SWOF\n")
                output.write("*SW KRW KRO PCOW\n")
                for _, row in df_adj.iterrows():
                    output.write(f"{row['Sw']:.6f} {row['Krw_adjusted']:.6f} {row['Kro_adjusted']:.6f} {row['Pcow']:.6f}\n")
                output.write("/\n\n")
            elif simulator == "Intersect":
                output.write("SWOF\n")
                output.write("-- Sw Krw Kro Pcow\n")
                for _, row in df_adj.iterrows():
                    output.write(f"{row['Sw']:.6f} {row['Krw_adjusted']:.6f} {row['Kro_adjusted']:.6f} {row['Pcow']:.6f}\n")
                output.write("/\n\n")
    return output.getvalue()

# Streamlit UI
st.title("Renaissance Africa Energy Company Limited")
st.header("Universal PVT and RelPerm Correction Tool")
st.markdown("**Version 1.0** | Last Updated: September 2025")

# Page Navigation
if st.session_state.page == 'validation':
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Step 1: Data Validation and Editing")
    st.markdown("""
    Upload an Excel file containing PVT (satoil: Psat, Bo, Rs, VscO; wetgastable: P, Bgdry, VscGdry, Bgwet, rs, VscGwet) and/or RelPerm (SGOF: Sg, Krg, Kro, Pcgo; SWOF: Sw, Krw, Kro, Pcow) tables.
    Verify table types, map headers to standard properties, and edit values as needed. Proceed to correction when ready.
    """)

    simulator = st.selectbox("Target Simulator", ["ECLIPSE", "CMG", "Intersect"], index=0, key="simulator_validation")
    uploaded_file = st.file_uploader("Upload Excel File", type=["xls", "xlsx"], key="file_uploader")
    
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file, sheet_name=None)
            st.session_state.data = df
            st.success("File uploaded successfully. Please verify and edit tables below.")
            
            for sheet_name, sheet_df in df.items():
                st.markdown(f"### Sheet: {sheet_name}")
                tables = detect_tables(sheet_df)
                if not tables:
                    st.warning(f"No valid tables found in {sheet_name}.")
                    continue
                
                for table_type, table_data, headers in tables:
                    st.markdown(f"#### Detected Table: {table_type}")
                    key = f"{sheet_name}_{table_type}_{str(uuid.uuid4())[:8]}"
                    
                    # Table type selection
                    st.session_state.table_assignments[key] = st.selectbox(
                        f"Confirm table type for {sheet_name} - {table_type}",
                        ["satoil", "wetgastable", "sgof", "swof", "ignore"],
                        index=["satoil", "wetgastable", "sgof", "swof", "ignore"].index(table_type) if table_type in ["satoil", "wetgastable", "sgof", "swof"] else 4,
                        key=f"type_{key}"
                    )
                    
                    # Header mapping
                    st.markdown("**Map Headers to Standard Properties**")
                    required_headers = (
                        ['Pressure', 'Bo', 'Rs', 'Viscosity'] if st.session_state.table_assignments[key] == 'satoil'
                        else ['Pressure', 'Bgdry', 'VscGdry', 'Bgwet', 'rs', 'VscGwet'] if st.session_state.table_assignments[key] == 'wetgastable'
                        else ['Sg', 'Krg', 'Kro', 'Pcgo'] if st.session_state.table_assignments[key] == 'sgof'
                        else ['Sw', 'Krw', 'Kro', 'Pcow'] if st.session_state.table_assignments[key] == 'swof'
                        else []
                    )
                    header_mappings = {}
                    for h in headers:
                        mapped = st.selectbox(
                            f"Map column '{h}'",
                            required_headers + ['None'],
                            index=required_headers.index(h) if h in required_headers else len(required_headers),
                            key=f"header_{key}_{h}"
                        )
                        if mapped != 'None':
                            header_mappings[h] = mapped
                    st.session_state.header_mappings[key] = header_mappings

                    # Editable table
                    st.markdown("**Edit Table Data**")
                    column_config = {
                        h: st.column_config.NumberColumn(
                            h, 
                            min_value=0 if h not in ['Pcgo', 'Pcow'] else None, 
                            max_value=1 if h in ['Sg', 'Sw', 'Krg', 'Krw', 'Kro'] else None, 
                            format="%.6f"
                        ) for h in table_data.columns
                    }
                    edited_df = st.data_editor(
                        table_data,
                        column_config=column_config,
                        num_rows="dynamic",
                        key=f"editor_{key}"
                    )
                    st.session_state.edited_data[key] = edited_df

                    # Validate
                    errors = validate_data([(st.session_state.table_assignments[key], edited_df, headers)], sheet_name)
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        st.success(f"Table {st.session_state.table_assignments[key]} in {sheet_name} validated successfully.")

            if st.button("Proceed to Correction", key="proceed_button"):
                if any(st.session_state.table_assignments.get(k, 'ignore') != 'ignore' for k in st.session_state.table_assignments):
                    st.session_state.page = 'correction'
                    st.experimental_rerun()
                else:
                    st.error("Please assign at least one table as satoil, wetgastable, sgof, or swof.")
        except Exception as e:
            st.error(f"Error loading file: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.page == 'correction':
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Step 2: PVT and RelPerm Correction and Plotting")
    st.markdown("""
    Specify correction factors, Rs unit, and volume inputs for PVT and RelPerm data adjustment. View interactive plots and download the adjusted data in the selected simulator format.
    """)

    simulator = st.selectbox("Target Simulator", ["ECLIPSE", "CMG", "Intersect"], index=0, key="simulator_correction")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("PVT Correction Factors")
        rs_unit = st.selectbox("Rs Unit (Satoil)", ["MMSCF/BBL", "SCF/BBL"], index=0, key="rs_unit")
        bo_factor = st.number_input("Bo Correction Factor", value=1.0, step=0.1, min_value=0.0, key="bo_factor")
        rs_factor = st.number_input("Rs Correction Factor", value=1.0, step=0.1, min_value=0.0, key="rs_factor")
        visco_factor = st.number_input("Viscosity Correction Factor", value=1.0, step=0.1, min_value=0.0, key="visco_factor")
        bgwet_factor = st.number_input("Bgwet Correction Factor", value=1.0, step=0.1, min_value=0.0, key="bgwet_factor")
        rs_gas_factor = st.number_input("rs (Gas) Correction Factor", value=1.0, step=0.1, min_value=0.0, key="rs_gas_factor")

    with col2:
        st.subheader("RelPerm Correction Factors")
        krg_factor = st.number_input("Krg Correction Factor (SGOF)", value=1.0, step=0.1, min_value=0.0, key="krg_factor")
        krw_factor = st.number_input("Krw Correction Factor (SWOF)", value=1.0, step=0.1, min_value=0.0, key="krw_factor")
        kro_factor = st.number_input("Kro Correction Factor (SGOF/SWOF)", value=1.0, step=0.1, min_value=0.0, key="kro_factor")

    st.subheader("Volume Inputs")
    col3, col4 = st.columns(2)
    with col3:
        ecl_oil_vol = st.number_input("Eclipse Volume (Oil, BBL)", value=0.0, min_value=0.0, key="ecl_oil_vol")
        mores_oil_vol = st.number_input("MoReS Volume (Oil, BBL)", value=0.0, min_value=0.0, key="mores_oil_vol")
    with col4:
        ecl_gas_vol = st.number_input("Eclipse Volume (Gas, BSCF)", value=0.0, min_value=0.0, key="ecl_gas_vol")
        mores_gas_vol = st.number_input("MoReS Volume (Gas, BSCF)", value=0.0, min_value=0.0, key="mores_gas_vol")

    if st.button("Process Data", key="process_button"):
        if st.session_state.data is None:
            st.error("No data loaded. Return to validation page to upload a file.")
        else:
            try:
                results, pvt_fig, relperm_fig = process_data(
                    st.session_state.data, bo_factor, rs_factor, visco_factor, bgwet_factor, rs_gas_factor,
                    krg_factor, krw_factor, kro_factor,
                    ecl_oil_vol, mores_oil_vol, ecl_gas_vol, mores_gas_vol, rs_unit,
                    st.session_state.table_assignments, st.session_state.header_mappings, st.session_state.edited_data
                )
                if results:
                    if any('satoil' in k or 'wetgastable' in k for k in results):
                        st.markdown("### PVT Plots")
                        st.plotly_chart(pvt_fig, use_container_width=True)
                    if any('sgof' in k or 'swof' in k for k in results):
                        st.markdown("### RelPerm Plots")
                        st.plotly_chart(relperm_fig, use_container_width=True)
                    st.session_state.results = results
                    st.success("Data processed and plotted successfully. Download the adjusted data below.")
                else:
                    st.warning("No valid tables processed. Check table assignments and data.")
            except Exception as e:
                st.error(f"Error processing data: {e}")

    if st.session_state.results:
        export_content = export_data(st.session_state.results, simulator)
        file_extension = ".inc" if simulator == "ECLIPSE" else ".dat" if simulator == "CMG" else ".txt"
        st.download_button(
            label="Download Adjusted File",
            data=export_content,
            file_name=f"adjusted_pvt_relperm{file_extension}",
            mime="text/plain",
            key="download_button"
        )

    if st.button("Back to Validation", key="back_button"):
        st.session_state.page = 'validation'
        st.experimental_rerun()
    st.markdown("</div>", unsafe_allow_html=True)
