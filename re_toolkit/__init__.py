from .core import (
    STANDARD_HEADERS,
    SUPPORTED_SIMULATORS,
    normalize_header,
    guess_table_type,
    detect_tables,
    validate_table,
    validate_tables,
    apply_header_mapping,
    process_tables,
    process_data,
    export_simulator_data,
)
from .io import load_excel_data
from .plots import create_pvt_plot, create_relperm_plot

__version__ = "1.0.0"
__all__ = [
    "STANDARD_HEADERS",
    "SUPPORTED_SIMULATORS",
    "normalize_header",
    "guess_table_type",
    "detect_tables",
    "validate_table",
    "validate_tables",
    "apply_header_mapping",
    "process_tables",
    "process_data",
    "export_simulator_data",
    "load_excel_data",
    "create_pvt_plot",
    "create_relperm_plot",
]
