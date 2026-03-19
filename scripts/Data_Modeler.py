import polars as pl
import os
from scripts import constants

class DataModeler:
    def __init__(self):
        self.silver_dir = constants.PROCESSED_DATA_DIR

    def create_revenue_report(self):
        """Joins Items, Orders, and Customers to find total revenue per State."""
        # 1. Load Silver data
        df_items = pl.read_parquet(os.path.join(self.silver_dir, "order_items_cleaned.parquet"))
        df_orders = pl.read_parquet(os.path.join(self.silver_dir, "orders_cleaned.parquet"))
        df_customers = pl.read_parquet(os.path.join(self.silver_dir, "customers_cleaned.parquet"))

        # 2. Join Logic (The Bridge)
        items_with_customer_id = df_items.join(df_orders, on="order_id", how="inner")
        final_df = items_with_customer_id.join(df_customers, on="customer_id", how="inner")

        # 3. Aggregate for Gold Layer
        gold_df = (
            final_df.group_by("customer_state")
            .agg(
                pl.col("price").sum().alias("total_revenue"),
                pl.count("order_id").alias("total_orders")
            )
            .sort("total_revenue", descending=True)
        )

        # 4. Save to Gold
        output_path = os.path.join(self.silver_dir, "revenue_report_gold.parquet")
        gold_df.write_parquet(output_path)
        
        print(f"Gold Layer Created: Revenue Report saved with {len(gold_df)} states.")
        print(gold_df.head(5)) # Show the top 5 states in terminal