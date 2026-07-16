# Reservoir Engineering Toolkit (shindo-ru)

**Industry-grade Python library for PVT, wet gas, and relative permeability data processing and correction.**

🚀 **[Launch the Web App](https://shindo-ru.streamlit.app)**

---

## Features

✅ **Automatic Table Detection** - Intelligently detects PVT and RelPerm tables from Excel files  
✅ **Multi-Simulator Export** - ECLIPSE, CMG, and Intersect format support  
✅ **Header Mapping** - Smart column name normalization and manual override  
✅ **Validation** - Comprehensive data quality checks (non-negative values, saturation bounds, numeric validation)  
✅ **Interactive UI** - Streamlit-based web application with real-time feedback  
✅ **Data Adjustment** - Apply correction factors to Bo, Rs, Viscosity, Krg, Krw, Kro  
✅ **Visualization** - Interactive Plotly plots for original vs. adjusted data  

---

## Supported Table Types

- **SATOIL** - Dead oil properties (Pressure, Bo, Rs, Viscosity)
- **WETGASTABLE** - Wet gas properties (Pressure, Bgdry, VscGdry, Bgwet, rs, VscGwet)
- **SGOF** - Gas-oil relative permeability (Sg, Krg, Kro, Pcgo)
- **SWOF** - Water-oil relative permeability (Sw, Krw, Kro, Pcow)

---

## Installation

### From GitHub

```bash
git clone https://github.com/AetherAbode/shindo-ru.git
cd shindo-ru
pip install -r requirements.txt
```

### From PyPI (coming soon)

```bash
pip install re-toolkit
```

---

## Quick Start

### Web Application

```bash
streamlit run app.py
```

Then navigate to `http://localhost:8501` and upload your Excel file.

### Python Library

```python
from re_toolkit import (
    load_excel_data,
    detect_tables,
    process_data,
    export_simulator_data,
)

# Load Excel file
sheets = load_excel_data('pvt_data.xlsx')

# Detect tables
for sheet_name, sheet_df in sheets.items():
    tables = detect_tables(sheet_df)
    print(f"Found {len(tables)} tables in {sheet_name}")

# Process and adjust data
results = process_data(
    sheets,
    factors={'bo': 1.05, 'rs': 0.98, 'viscosity': 1.0},
    rs_unit='MMSCF/BBL',
)

# Export to simulator format
eclipse_data = export_simulator_data(results, 'ECLIPSE')
with open('output.inc', 'w') as f:
    f.write(eclipse_data)
```

---

## Project Structure

```
shindo-ru/
├── re_toolkit/                ← Main package
│   ├── __init__.py           ← Package exports
│   ├── core.py               ← Core processing logic
│   ├── io.py                 ← Excel I/O
│   └── plots.py              ← Visualization
│
├── app.py                     ← Streamlit web application
├── requirements.txt           ← Dependencies
├── .streamlitconfig.toml      ← Streamlit configuration
├── README.md                  ← This file
└── LICENSE                    ← MIT License
```

---

## API Reference

### Core Functions

#### `detect_tables(sheet_df: pd.DataFrame) -> List[Dict]`
Detects PVT and RelPerm tables in a DataFrame.

```python
tables = detect_tables(sheet_df)
# Returns: [{'table_type': 'satoil', 'headers': [...], 'data': df, 'header_row': 0}]
```

#### `validate_table(table_type: str, df: pd.DataFrame) -> List[str]`
Validates a table for data quality.

```python
errors = validate_table('satoil', df)
if errors:
    for error in errors:
        print(error)
```

#### `process_data(sheets, factors, rs_unit, table_assignments) -> Dict[str, pd.DataFrame]`
Processes and adjusts all tables in loaded sheets.

```python
results = process_data(
    sheets,
    factors={'bo': 1.0, 'rs': 1.0},
    rs_unit='MMSCF/BBL',
)
```

#### `export_simulator_data(results: Dict, simulator: str) -> str`
Exports processed data in simulator format.

```python
output = export_simulator_data(results, 'ECLIPSE')
```

---

## Deployment

### Streamlit Community Cloud (Recommended)

1. Push this repo to GitHub
2. Go to [Streamlit Community Cloud](https://streamlit.io/cloud)
3. Click "New app" → Connect GitHub repo → Select `app.py`
4. Deploy ✅

**Your app will be live at:** `https://[your-app-name].streamlit.app`

### Alternative: Deploy to Render

1. Go to [Render](https://render.com)
2. Create new Web Service
3. Connect GitHub repo
4. Set Start Command: `streamlit run app.py --server.port=10000 --server.address=0.0.0.0`
5. Deploy ✅

---

## Example Workflow

### Step 1: Upload Excel File
Prepare an Excel file with PVT/RelPerm tables:

```
Sheet: "PVT_Data"

| Pressure | Bo    | Rs     | Viscosity |
|----------|-------|--------|----------|
| 500      | 1.45  | 150    | 2.5      |
| 1000     | 1.32  | 300    | 1.8      |
```

### Step 2: Upload to App
Click "Upload Excel file" in the web interface.

### Step 3: Verify & Correct
- App auto-detects: SATOIL table ✅
- Confirm table type and map headers
- View validation results

### Step 4: Apply Corrections
- Set Bo factor: 1.05
- Set Rs factor: 0.98
- Select target simulator: ECLIPSE

### Step 5: Download
- View adjusted plots
- Download ECLIPSE-format input deck
- Use in your reservoir simulation

---

## Validation Rules

**All Tables:**
- All values must be numeric
- No NaN values allowed

**SATOIL & WETGASTABLE:**
- No negative values

**SGOF & SWOF:**
- Saturation (Sg, Sw) must be between 0 and 1
- No negative values

---

## Development

### Run Tests

```bash
pytest tests/
```

### Local Development

```bash
git clone https://github.com/AetherAbode/shindo-ru.git
cd shindo-ru
pip install -r requirements.txt
streamlit run app.py
```

---

## Contributing

Contributions welcome! Please:

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Support

📧 Issues & Questions: [GitHub Issues](https://github.com/AetherAbode/shindo-ru/issues)  
🌐 Web App: [Streamlit Cloud](https://shindo-ru.streamlit.app)  

---

**Made with ❤️ for reservoir engineers.**
