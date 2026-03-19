import polars as pl
import os
from scripts import constants

def verify_results():
    print("--- Final Data Verification ---")
    parquet_path = os.path.join(constants.PROCESSED_DATA_DIR, "customers_cleaned.parquet")
    
    if os.path.exists(parquet_path):
        df = pl.read_parquet(parquet_path)
        print(f"Processed Data Found: {parquet_path}")
        print(f"Total Clean Records: {len(df)}")
        print("Sample Data (Upper Case Check):")
        print(df.select(["customer_city", "customer_state"]).head(3))
    else:
        print("Processed file missing!")

if __name__ == "__main__":
    verify_results()