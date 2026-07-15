import streamlit as st
from re_toolkit import (
    STANDARD_HEADERS,
    load_excel_data,
    detect_tables,
    validate_table,
    process_tables,
    export_simulator_data,
    create_pvt_plot,
    create_relperm_plot,
    SUPPORTED_SIMULATORS,
)

st.set_page_config(page_title='Reservoir Engineering Toolkit', layout='wide')

st.title('Reservoir Engineering Toolkit')
st.markdown('Industry-grade Python library for PVT, wet gas, and relative permeability workflows.')

TABLE_TYPES = ['satoil', 'wetgastable', 'sgof', 'swof', 'ignore']

if 'tables' not in st.session_state:
    st.session_state.tables = []

uploaded_file = st.file_uploader('Upload Excel file with PVT / RelPerm data', type=['xls', 'xlsx'])
if uploaded_file:
    sheets = load_excel_data(uploaded_file)
    st.success(f'Loaded {len(sheets)} sheet(s).')

    detected_tables = []
    for sheet_name, sheet_df in sheets.items():
        for table in detect_tables(sheet_df):
            table['sheet_name'] = sheet_name
            table['assigned_type'] = table['table_type']
            table['header_mapping'] = {}
            detected_tables.append(table)

    st.session_state.tables = detected_tables

if st.session_state.tables:
    st.sidebar.header('Correction Workflow')
    simulator = st.sidebar.selectbox('Target Simulator', SUPPORTED_SIMULATORS)
    rs_unit = st.sidebar.selectbox('Rs unit', ['MMSCF/BBL', 'SCF/BBL'])
    bo_factor = st.sidebar.number_input('Bo factor', value=1.0, step=0.1)
    rs_factor = st.sidebar.number_input('Rs factor', value=1.0, step=0.1)
    visco_factor = st.sidebar.number_input('Viscosity factor', value=1.0, step=0.1)
    bgwet_factor = st.sidebar.number_input('Bgwet factor', value=1.0, step=0.1)
    rs_gas_factor = st.sidebar.number_input('Gas Rs factor', value=1.0, step=0.1)
    krg_factor = st.sidebar.number_input('Krg factor', value=1.0, step=0.1)
    krw_factor = st.sidebar.number_input('Krw factor', value=1.0, step=0.1)
    kro_factor = st.sidebar.number_input('Kro factor', value=1.0, step=0.1)

    factor_map = {
        'bo': bo_factor,
        'rs': rs_factor,
        'viscosity': visco_factor,
        'bgwet': bgwet_factor,
        'rs_gas': rs_gas_factor,
        'krg': krg_factor,
        'krw': krw_factor,
        'kro': kro_factor,
    }

    for idx, table in enumerate(st.session_state.tables):
        section = st.container()
        with section:
            st.markdown(f"### Sheet: {table['sheet_name']} | Detected: {table['table_type'].upper()}")
            assigned_type = st.selectbox(
                f"Table type for {table['sheet_name']} row {table['header_row']}",
                TABLE_TYPES,
                index=TABLE_TYPES.index(table['assigned_type']),
                key=f"type_{table['sheet_name']}_{table['header_row']}",
            )
            table['assigned_type'] = assigned_type

            header_options = STANDARD_HEADERS.get(assigned_type, []) + ['None']
            mapping = {}
            for col in table['headers']:
                mapped_value = st.selectbox(
                    f"Map '{col}' to", header_options,
                    index=header_options.index(col) if col in header_options else len(header_options) - 1,
                    key=f"map_{table['sheet_name']}_{table['header_row']}_{col}",
                )
                if mapped_value != 'None':
                    mapping[col] = mapped_value
            table['header_mapping'] = mapping

            display_df = table['data'].copy()
            if mapping:
                display_df = display_df.rename(columns=mapping)
            st.dataframe(display_df.head(10))

            if assigned_type != 'ignore':
                validation_df = display_df.copy()
                errors = validate_table(assigned_type, validation_df)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    st.success('Validation passed for this table.')

    if st.button('Process and Export Adjusted Data'):
        results = process_tables(st.session_state.tables, factors=factor_map, rs_unit=rs_unit)
        if results:
            st.markdown('## Adjusted Plots')
            pvt_fig = create_pvt_plot(results)
            relperm_fig = create_relperm_plot(results)
            st.plotly_chart(pvt_fig, use_container_width=True)
            st.plotly_chart(relperm_fig, use_container_width=True)
            output_text = export_simulator_data(results, simulator)
            st.download_button('Download Simulator Input', output_text, file_name='adjusted_reservoir_data.txt', mime='text/plain')
        else:
            st.warning('No valid tables to process. Please confirm table assignments.')
else:
    st.info('Upload an Excel file to detect PVT and relperm tables and start the workflow.')
