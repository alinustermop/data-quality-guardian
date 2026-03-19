import polars as pl
import os
from scripts import constants

class DataCleaner:
    def __init__(self):
        self.conn = f"sqlite:///{constants.DB_PATH}"

    def clean_customers(self):
        """Cleans the customers table: standardizes names and removes duplicates."""
        df = pl.read_database_uri(
            query="SELECT * FROM customers", 
            uri=self.conn, 
            engine="adbc"
        )
        
        initial_count = len(df)
        
        df_clean = (
            df.unique(subset=["customer_unique_id"])
              .with_columns([
                  pl.col("customer_city").str.to_uppercase(),
                  pl.col("customer_state").str.to_uppercase()
              ])
        )
        
        os.makedirs(constants.PROCESSED_DATA_DIR, exist_ok=True)
        
        output_path = os.path.join(constants.PROCESSED_DATA_DIR, "customers_cleaned.parquet")
        df_clean.write_parquet(output_path)
        
        print(f"Cleaned Customers: {initial_count} -> {len(df_clean)} rows. Saved to Parquet.")
        return df_clean

    def clean_orders(self):
        """Cleans the orders table."""
        df = pl.read_database_uri("SELECT * FROM orders", uri=self.conn, engine="adbc")
        
        df_clean = df.filter(pl.col("order_status") == "delivered")
        
        output_path = os.path.join(constants.PROCESSED_DATA_DIR, "orders_cleaned.parquet")
        df_clean.write_parquet(output_path)
        print(f"Cleaned Orders: {len(df_clean)} delivered orders saved to Parquet.")
        return df_clean

    def clean_order_items(self):
        """Cleans order_items by removing orphans and validating prices."""
        # 1. Load both tables
        df_items = pl.read_database_uri("SELECT * FROM order_items", uri=self.conn, engine="adbc")
        df_orders = pl.read_database_uri("SELECT order_id FROM orders", uri=self.conn, engine="adbc")
        
        initial_count = len(df_items)

        # 2. Relational Cleaning (Inner Join)
        df_clean = df_items.join(df_orders, on="order_id", how="inner")
        
        # 3. Value Cleaning
        df_clean = df_clean.filter(pl.col("price") > 0)
        
        # 4. Save
        output_path = os.path.join(constants.PROCESSED_DATA_DIR, "order_items_cleaned.parquet")
        df_clean.write_parquet(output_path)
        
        orphans_removed = initial_count - len(df_clean)
        print(f"Cleaned Order Items: Removed {orphans_removed} orphans. Saved to Parquet.")
        return df_clean

    def create_gold_sales_report(self):
        """Joins Customers, Orders, and Items to create a high-level Sales Report (Gold Layer)."""
        # Load the Silver Parquet files we just created
        cust_path = os.path.join(constants.PROCESSED_DATA_DIR, "customers_cleaned.parquet")
        items_path = os.path.join(constants.PROCESSED_DATA_DIR, "order_items_cleaned.parquet")
        
        # Load 'orders' from DB for the join (we haven't made a parquet for it yet)
        df_orders = pl.read_database_uri("SELECT order_id, customer_id FROM orders", uri=self.conn, engine="adbc")
        
        df_cust = pl.read_parquet(cust_path)
        df_items = pl.read_parquet(items_path)

        # The Join Chain (The 'Gold' logic)
        gold_df = (
            df_items.join(df_orders, on="order_id")
                    .join(df_cust, on="customer_id")
                    .group_by("customer_state")
                    .agg([
                        pl.col("price").sum().alias("total_revenue"),
                        pl.col("order_id").n_unique().alias("total_orders")
                    ])
                    .sort("total_revenue", descending=True)
        )

        output_path = os.path.join(constants.PROCESSED_DATA_DIR, "gold_state_revenue.parquet")
        gold_df.write_parquet(output_path)
        print(f"Gold Layer Created: {output_path}")
        return gold_df