import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STAGING_DIR = BASE_DIR / "data" / "staging"

STAGING_DIR.mkdir(parents=True, exist_ok=True)

def extract_data(file_path):
    """
    Extract data from a source file into a DataFrame.
    Args:
        file_path (str or Path): Path to the source file.
    Returns:
        pd.DataFrame: Extracted data.
    """
    file_path = str(file_path)

    if file_path.endswith(".csv"):
        return pd.read_csv(file_path)

    elif file_path.endswith((".xlsx", ".xls")):
        return pd.read_excel(file_path)

    else:
        raise ValueError(f"Unsupported file type: {file_path}")
    

def load_to_staging(df, file_path):
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(file_path, index=False)
    print(f"Saved to staging: {file_path}")

def main():
    logs = BASE_DIR / "data" / "raw" / "ICT001 S1 2025 Logs RELEASED V1.0.xlsx"
    results = BASE_DIR / "data" / "raw" / "cleaned_standard_results.xlsx"
    staging_path_logs = STAGING_DIR / "logs.csv"
    staging_path_results = STAGING_DIR / "results.csv"

    df_logs = extract_data(logs)
    load_to_staging(df_logs, staging_path_logs)
    print(f"Extracted logs data shape: {df_logs.shape}")

    df_results = extract_data(results)
    load_to_staging(df_results, staging_path_results)
    print(f"Extracted results data shape: {df_results.shape}")

if __name__ == "__main__":
    main()