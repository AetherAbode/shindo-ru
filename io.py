import pandas as pd
from typing import Dict


def load_excel_data(source) -> Dict[str, pd.DataFrame]:
    """Load all sheets from an Excel source into a dictionary of DataFrames.

    Parameters:
        source: file path or file-like object accepted by pandas.read_excel.

    Returns:
        A mapping of sheet name to sheet DataFrame.
    """
    return pd.read_excel(source, sheet_name=None)
