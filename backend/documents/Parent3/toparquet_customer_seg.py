import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent  # directory where this script lives

csv_path = BASE_DIR / "Customer_Segmentation_2025Q3.csv"
parquet_path = BASE_DIR / "Customer_Segmentation_2025Q3.parquet"

print(f"Reading {csv_path}")
df = pd.read_csv(csv_path)

print(f"Writing {parquet_path}")
df.to_parquet(parquet_path, index=False)
