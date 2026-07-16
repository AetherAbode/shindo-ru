import pandas as pd
from typing import Any, Dict, List, Optional

SUPPORTED_SIMULATORS = ["ECLIPSE", "CMG", "Intersect"]

STANDARD_HEADERS = {
    'satoil': ['Pressure', 'Bo', 'Rs', 'Viscosity'],
    'wetgastable': ['Pressure', 'Bgdry', 'VscGdry', 'Bgwet', 'rs', 'VscGwet'],
    'sgof': ['Sg', 'Krg', 'Kro', 'Pcgo'],
    'swof': ['Sw', 'Krw', 'Kro', 'Pcow'],
}

HINT_HEADERS = {
    'satoil': ['psat', 'pressure', 'po', 'p', 'bo', 'rs', 'gor', 'viso', 'vsco', 'cbo', 'viscosity'],
    'wetgastable': ['pressure', 'bgdry', 'vscgdry', 'bgwet', 'rs', 'rs_gas', 'vscgwet', 'bgwet', 'vscgwet'],
    'sgof': ['sg', 'krg', 'kro', 'pcgo'],
    'swof': ['sw', 'krw', 'kro', 'pcow'],
}


def normalize_header(header: Any) -> str:
    if pd.isna(header):
        return ''
    return str(header).strip().lower().replace(' ', '').replace('_', '').replace('-', '')


def guess_table_type(headers: List[str]) -> Optional[str]:
    normalized = [normalize_header(h) for h in headers if h]
    for table_type, hints in HINT_HEADERS.items():
        if any(h in normalized for h in [normalize_header(item) for item in hints]):
            return table_type
    return None


def detect_tables(sheet_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Detect PVT and relative permeability tables in a sheet."""
    sheet_df = sheet_df.copy().fillna('')
    tables: List[Dict[str, Any]] = []
    row_count = len(sheet_df)

    for i in range(row_count):
        row = sheet_df.iloc[i]
        headers = [str(value).strip() for value in row if str(value).strip()]
        guessed_type = guess_table_type(headers)
        if not guessed_type:
            continue

        start_idx = i + 1
        end_idx = start_idx
        while end_idx < row_count:
            next_row = sheet_df.iloc[end_idx]
            next_values = [str(value).strip().lower() for value in next_row if str(value).strip()]
            if guess_table_type(next_values) or not any(next_values):
                break
            end_idx += 1

        table_data = sheet_df.iloc[start_idx:end_idx]
        table_data = table_data.loc[:, table_data.columns.notnull()]
        if table_data.empty or len(table_data.columns) < len(headers):
            continue

        table_data.columns = headers[: len(table_data.columns)]
        tables.append({
            'table_type': guessed_type,
            'headers': headers,
            'data': table_data.reset_index(drop=True),
            'header_row': i,
        })

    return tables


def validate_table(table_type: str, df: pd.DataFrame) -> List[str]:
    errors: List[str] = []
    if table_type not in STANDARD_HEADERS:
        errors.append(f'Unknown table type: {table_type}')
        return errors

    required = STANDARD_HEADERS[table_type]
    missing = [col for col in required if col not in df.columns]
    if missing:
        errors.append(f'Missing required columns for {table_type}: {missing}')

    if not df.empty:
        numeric_df = pd.DataFrame()
        for column in df.columns:
            numeric_df[column] = pd.to_numeric(df[column], errors='coerce')
        if numeric_df.isna().any().any():
            errors.append(f'Non-numeric values detected in {table_type} table.')
        if (numeric_df < 0).any().any() and table_type in ['satoil', 'wetgastable', 'sgof', 'swof']:
            errors.append(f'Negative values detected in {table_type} table.')
        if table_type in ['sgof', 'swof']:
            sat_col = 'Sg' if table_type == 'sgof' else 'Sw'
            if sat_col in numeric_df.columns:
                if not numeric_df[sat_col].between(0, 1).all():
                    errors.append(f'{sat_col} values must be between 0 and 1 in {table_type} table.')
    return errors


def validate_tables(tables: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    return {
        table['table_type']: validate_table(table['table_type'], table['data'])
        for table in tables
    }


def apply_header_mapping(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    renamed = {
        str(column): str(mapping[column])
        for column in df.columns
        if column in mapping and mapping[column]
    }
    return df.rename(columns=renamed)


def process_tables(
    tables: List[Dict[str, Any]],
    factors: Optional[Dict[str, float]] = None,
    rs_unit: str = 'MMSCF/BBL',
) -> Dict[str, pd.DataFrame]:
    if factors is None:
        factors = {}

    results: Dict[str, pd.DataFrame] = {}
    for idx, table in enumerate(tables):
        assigned_type = table.get('assigned_type', table['table_type'])
        if assigned_type == 'ignore':
            continue

        table_df = table['data'].copy()
        if table.get('header_mapping'):
            table_df = apply_header_mapping(table_df, table['header_mapping'])

        table_df.columns = [str(c).strip() for c in table_df.columns]
        adjusted = _apply_adjustments(assigned_type, table_df, factors, rs_unit)
        results[f"{table['sheet_name']}_{assigned_type}_{idx}"] = adjusted
    return results


def _apply_adjustments(table_type: str, df: pd.DataFrame, factors: Dict[str, float], rs_unit: str) -> pd.DataFrame:
    adjusted = df.copy().astype(float)

    if table_type == 'satoil':
        if rs_unit == 'SCF/BBL':
            adjusted['Rs'] = adjusted['Rs'] / 1_000_000
        adjusted['Bo_adjusted'] = adjusted['Bo'] * factors.get('bo', 1.0)
        adjusted['Rs_adjusted'] = adjusted['Rs'] * factors.get('rs', 1.0)
        adjusted['Viscosity_adjusted'] = adjusted['Viscosity'] * factors.get('viscosity', 1.0)
    elif table_type == 'wetgastable':
        adjusted['Bgwet_adjusted'] = adjusted['Bgwet'] * factors.get('bgwet', 1.0)
        adjusted['rs_adjusted'] = adjusted['rs'] * factors.get('rs_gas', 1.0)
    elif table_type == 'sgof':
        adjusted['Krg_adjusted'] = adjusted['Krg'] * factors.get('krg', 1.0)
        adjusted['Kro_adjusted'] = adjusted['Kro'] * factors.get('kro', 1.0)
    elif table_type == 'swof':
        adjusted['Krw_adjusted'] = adjusted['Krw'] * factors.get('krw', 1.0)
        adjusted['Kro_adjusted'] = adjusted['Kro'] * factors.get('kro', 1.0)

    return adjusted


def process_data(
    sheets: Dict[str, pd.DataFrame],
    factors: Optional[Dict[str, float]] = None,
    rs_unit: str = 'MMSCF/BBL',
    table_assignments: Optional[Dict[str, str]] = None,
) -> Dict[str, pd.DataFrame]:
    if factors is None:
        factors = {}
    if table_assignments is None:
        table_assignments = {}

    results: Dict[str, pd.DataFrame] = {}

    for sheet_name, sheet_df in sheets.items():
        tables = detect_tables(sheet_df)
        for table in tables:
            assigned_type = table_assignments.get(f"{sheet_name}_{table['table_type']}", table['table_type'])
            if assigned_type == 'ignore':
                continue
            table_df = table['data'].copy()
            table_df.columns = [str(col).strip() for col in table_df.columns]
            adjusted = _apply_adjustments(assigned_type, table_df, factors, rs_unit)
            results[f"{sheet_name}_{assigned_type}"] = adjusted
    return results


def export_simulator_data(results: Dict[str, pd.DataFrame], simulator: str) -> str:
    if simulator not in SUPPORTED_SIMULATORS:
        raise ValueError(f'Unsupported simulator: {simulator}')

    output_lines: List[str] = []
    for key, df in results.items():
        if 'satoil' in key:
            if simulator == 'ECLIPSE':
                output_lines.append('PVTO')
                output_lines.append('-- Rs Po Bo cPo')
                for _, row in df.iterrows():
                    output_lines.append(f"{row['Rs_adjusted']:.6f} {row['Pressure']:.1f} {row['Bo_adjusted']:.4f} {row['Viscosity_adjusted']:.4f}")
                output_lines.append('/\n')
            elif simulator == 'CMG':
                output_lines.append('*PVTO')
                output_lines.append('*GOR PRESSURE BO VISCOSITY')
                for _, row in df.iterrows():
                    output_lines.append(f"{row['Rs_adjusted']:.6f} {row['Pressure']:.1f} {row['Bo_adjusted']:.4f} {row['Viscosity_adjusted']:.4f}")
                output_lines.append('/\n')
            else:
                output_lines.append('PVTO')
                output_lines.append('-- Rs Po Bo cPo')
                for _, row in df.iterrows():
                    output_lines.append(f"{row['Rs_adjusted']:.6f} {row['Pressure']:.1f} {row['Bo_adjusted']:.4f} {row['Viscosity_adjusted']:.4f}")
                output_lines.append('/\n')
        elif 'wetgastable' in key:
            if simulator == 'ECLIPSE':
                output_lines.append('PVTG')
                output_lines.append('-- P rv Bg cPg')
                for _, row in df.iterrows():
                    rv = row['rs_adjusted'] / 1000 if row['rs_adjusted'] > 0 else 0.0
                    output_lines.append(f"{row['Pressure']:.1f} {rv:.6f} {row['Bgwet_adjusted']*1000:.6f} {row['VscGwet']:.6f}")
                output_lines.append('/\n')
            elif simulator == 'CMG':
                output_lines.append('*PVTG')
                output_lines.append('*PRESSURE RV BG VISCOSITY')
                for _, row in df.iterrows():
                    rv = row['rs_adjusted'] / 1000 if row['rs_adjusted'] > 0 else 0.0
                    output_lines.append(f"{row['Pressure']:.1f} {rv:.6f} {row['Bgwet_adjusted']*1000:.6f} {row['VscGwet']:.6f}")
                output_lines.append('/\n')
            else:
                output_lines.append('PVTG')
                output_lines.append('-- P rv Bg cPg')
                for _, row in df.iterrows():
                    rv = row['rs_adjusted'] / 1000 if row['rs_adjusted'] > 0 else 0.0
                    output_lines.append(f"{row['Pressure']:.1f} {rv:.6f} {row['Bgwet_adjusted']*1000:.6f} {row['VscGwet']:.6f}")
                output_lines.append('/\n')
        elif 'sgof' in key:
            if simulator == 'ECLIPSE':
                output_lines.append('SGOF')
                output_lines.append('-- Sg Krg Kro Pcgo')
            elif simulator == 'CMG':
                output_lines.append('*SGOF')
                output_lines.append('*SG KRG KRO PCGO')
            else:
                output_lines.append('SGOF')
                output_lines.append('-- Sg Krg Kro Pcgo')
            for _, row in df.iterrows():
                output_lines.append(f"{row['Sg']:.6f} {row['Krg_adjusted']:.6f} {row['Kro_adjusted']:.6f} {row['Pcgo']:.6f}")
            output_lines.append('/\n')
        elif 'swof' in key:
            if simulator == 'ECLIPSE':
                output_lines.append('SWOF')
                output_lines.append('-- Sw Krw Kro Pcow')
            elif simulator == 'CMG':
                output_lines.append('*SWOF')
                output_lines.append('*SW KRW KRO PCOW')
            else:
                output_lines.append('SWOF')
                output_lines.append('-- Sw Krw Kro Pcow')
            for _, row in df.iterrows():
                output_lines.append(f"{row['Sw']:.6f} {row['Krw_adjusted']:.6f} {row['Kro_adjusted']:.6f} {row['Pcow']:.6f}")
            output_lines.append('/\n')
    return '\n'.join(output_lines).strip() + '\n'
