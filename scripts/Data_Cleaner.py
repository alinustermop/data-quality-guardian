import logging
import polars as pl
from pathlib import Path
from scripts import constants

class DataCleaner:
    """
    Handles the transformation of raw database tables into cleaned Parquet files.
    """

    def __init__(self):
        # Paths from constants
        self.conn = constants.DB_CONN
        self.silver_dir = Path(constants.PROCESSED_DATA_DIR)

        self.silver_dir.mkdir(parents=True, exist_ok=True)

        # Color constants for terminal output
        self.GREEN = "\033[92m"
        self.RED = "\033[91m"
        self.RESET = "\033[0m"

        self._setup_logging()

    def _setup_logging(self):
        """Helper to configure logging for the cleaning process."""
        self.logger = logging.getLogger("Data_Cleaner")
        if not self.logger.hasHandlers():
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('  > %(message)s'))
            self.logger.addHandler(console_handler)
            self.logger.setLevel(logging.INFO)

    def _get_silver_path(self, name: str):
        """Helper to get the standard path for a cleaned table."""
        return self.silver_dir / f"{name}_cleaned.parquet"

    def _save_and_log(self, df: pl.DataFrame, name: str):
        """Helper to save a LazyFrame as a Parquet file and log the operation status."""
        path = self._get_silver_path(name)
        row_count = len(df)
        df.write_parquet(path)
        self.logger.info(f"Cleaned {name.replace('_', ' ').title()}: {row_count} rows saved")

# --- CLEANING FUNCTIONS ---

    def clean_customers(self) -> pl.DataFrame:
        """Cleans the customers table: standardizes names and removes duplicates."""

        df = pl.read_database_uri(
            query="SELECT * FROM customers", 
            uri=self.conn, 
            engine="adbc"
        )

        # Rule: Ensure unique customers and normalize city/state formatting
        df_clean = (
            df.unique(subset=["customer_unique_id"])
              .with_columns([
                  pl.col("customer_city").str.strip_chars().str.to_uppercase(),
                  pl.col("customer_state").str.strip_chars().str.to_uppercase()
              ])
        )

        self._save_and_log(df_clean, "customers")
        return df_clean

    def clean_orders(self) -> pl.DataFrame:
        """Cleans the orders table: preserves all statuses and enforces strict typing."""

        df = pl.read_database_uri(
            query="SELECT * FROM orders", 
            uri=self.conn, 
            engine="adbc")
        
        date_cols = [c for c in df.collect_schema().names() if "timestamp" in c or "date" in c]
        
        # Rule: Only keep completed transactions and ensure proper datetime types
        df_clean = df.with_columns([
            pl.col("order_status").cast(pl.Categorical),
            (pl.col("order_status") == "delivered").alias("is_completed_transaction"),
            pl.col("order_status").is_in(["canceled", "unavailable"]).alias("is_failed"),
            *[
                pl.col(c)
                .str.strip_chars()
                .replace("", None)
                .str.to_datetime(format="%Y-%m-%d %H:%M:%S", strict=False)
                for c in date_cols
            ]
        ])
        
        self._save_and_log(df_clean, "orders")
        return df_clean

    def clean_order_items(self) -> pl.DataFrame:
        """Cleans the order items: removes orphans and ensures positive pricing."""

        df_items = pl.read_database_uri(
            query="SELECT * FROM order_items", 
            uri=self.conn, 
            engine="adbc"
        )
        
        orders_path = self._get_silver_path("orders")
        
        if orders_path.exists():
            df_orders = pl.read_parquet(orders_path).select("order_id")
        else:
            df_orders = pl.read_database_uri(
                query="SELECT order_id FROM orders", 
                uri=self.conn, 
                engine="adbc"
            )
        
        # Rule: Only keep items with valid orders and positive price
        df_clean = (
            df_items.join(df_orders, on="order_id", how="inner")
                    .filter(pl.col("price") > 0)
        )

        self._save_and_log(df_clean, "order_items")
        return df_clean
    
    def clean_products(self) -> pl.DataFrame:
        """Cleans the products table: removes items with missing categories and invalid weights."""
        df_prod = pl.read_database_uri(
            query="SELECT * FROM products", 
            uri=self.conn, 
            engine="adbc")
        
        initial_count = len(df_prod)

        df_trans = pl.read_database_uri(query="SELECT * FROM product_category_name_translation", uri=self.conn, engine="adbc")

        # Rule: Filter out null categories and unrealistic weights (0g to 50kg limit)
        df_clean = (
            df_prod.filter(
                pl.col("product_category_name").is_not_null() &
                pl.col("product_weight_g").is_between(1, 50000)
            )
            .join(df_trans, on="product_category_name", how="left")
            .with_columns(
                pl.col("product_category_name_english").fill_null(pl.col("product_category_name"))
            )
        )

        self._save_and_log(df_clean, "products")
        return df_clean

    def clean_marketing_funnel_data(self) -> tuple[pl.LazyFrame, pl.LazyFrame]:
        """Cleans leads and deals: removes duplicate MQL IDs."""

        df_leads = pl.read_database_uri(
            query="SELECT * FROM marketing_leads", 
            uri=self.conn, 
            engine="adbc"
            )

        df_deals = pl.read_database_uri(
            query="SELECT * FROM closed_deals", 
            uri=self.conn, 
            engine="adbc"
        )

        # Rule: Ensure each MQL ID is unique across leads and deals
        df_leads_clean = (
            df_leads.unique(subset=["mql_id"])
            .with_columns(pl.col("first_contact_date").str.to_datetime(strict=False))
        )

        df_deals_clean = (
            df_deals.unique(subset=["mql_id"])
            .with_columns(pl.col("won_date").str.to_datetime(strict=False))
        )

        self._save_and_log(df_leads_clean, "marketing_leads")
        self._save_and_log(df_deals_clean, "closed_deals")
        return df_leads_clean, df_deals_clean

    def clean_sellers(self) -> pl.DataFrame:
        """Cleans sellers table: standardizes city and state names."""

        df = pl.read_database_uri(
            query="SELECT * FROM sellers", 
            uri=self.conn, 
            engine="adbc")
        
        # Rule: Normalize casing for geographical columns
        df_clean = df.with_columns([
            pl.col("seller_city").str.strip_chars().str.to_uppercase(),
            pl.col("seller_state").str.strip_chars().str.to_uppercase()
        ])
        
        self._save_and_log(df_clean, "sellers")
        return df_clean

    def clean_order_payments(self) -> pl.DataFrame:
        """Cleans the payments table: ensures positive values and standardizes types."""
        df = pl.read_database_uri(query="SELECT * FROM order_payments", uri=self.conn, engine="adbc")
        # Rule: Filter values and ensure payment types are lowercase/clean
        df_clean = df.filter(pl.col("payment_value") > 0).with_columns(
            pl.col("payment_type").str.to_lowercase()
        )
        
        self._save_and_log(df_clean, "order_payments")
        return df_clean

    def clean_order_reviews(self) -> pl.DataFrame:
        """Cleans the reviews table: handles date casting and null review scores."""
        df = pl.read_database_uri(query="SELECT * FROM order_reviews", uri=self.conn, engine="adbc")
        
        # Rule: Convert review timestamps and fill missing scores with the median
        df_clean = df.with_columns([
            pl.col("review_creation_date").str.to_datetime(strict=False),
            pl.col("review_answer_timestamp").str.to_datetime(strict=False),
            pl.col("review_score").fill_null(df["review_score"].median())
        ])
        
        self._save_and_log(df_clean, "order_reviews")
        return df_clean

# --- RUN ALL ---

    def run_all(self) -> None:
        """Executes the full cleaning pipeline in the correct dependency order."""
        self.logger.info("Starting Silver Layer Cleaning...")

        # Level 1: Independent Tables
        self.clean_orders()
        self.clean_customers()
        self.clean_sellers()
        self.clean_products()
        self.clean_marketing_funnel_data()

        # Level 2: Tables that depend on Level 1
        self.clean_order_items()
        self.clean_order_payments()
        self.clean_order_reviews()

        self.logger.info(f"{self.GREEN}SUCCESS{self.RESET}: Silver Layer processing complete.")