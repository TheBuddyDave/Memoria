import pandas as pd
df = pd.read_csv("Parent2\Supplier_ETA_Snapshot.csv")
df.to_parquet("Supplier_ETA_Snapshot.parquet", index=False)
