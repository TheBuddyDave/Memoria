import pandas as pd
from pathlib import Path

# Directory where this script lives
BASE_DIR = Path(__file__).parent

stems = [
    "vendor_monthly_2025-10",
    "asn_compliance_2025-10",
    "defect_log_2025-10",
]

for stem in stems:
    csv_path = BASE_DIR / f"{stem}.csv"
    parquet_path = BASE_DIR / f"{stem}.parquet"

    print(f"Converting {csv_path} -> {parquet_path}")
    df = pd.read_csv(csv_path)
    df.to_parquet(parquet_path, index=False)
