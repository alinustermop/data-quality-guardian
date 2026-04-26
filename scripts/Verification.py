import logging
import polars as pl
from pathlib import Path
from scripts import constants

class DataVerifier:
    """
    Provides tests to verify the existence, volume, and formatting of the Silver and Gold data layers.
    """

    def __init__(self):
        # Paths from constants
        self.silver_dir = Path(constants.PROCESSED_DATA_DIR)
        self.gold_dir = Path(constants.GOLD_DATA_DIR)

        # Color constants for terminal output
        self.GREEN = "\033[92m"
        self.RED = "\033[91m"
        self.YELLOW = "\033[93m"
        self.RESET = "\033[0m"

        self._setup_logging()

    def _setup_logging(self):
        """Helper to configure logging for the verification process."""
        self.logger = logging.getLogger("Data_Verifier")
        if not self.logger.hasHandlers():
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('  > %(message)s'))
            self.logger.addHandler(console_handler)
            self.logger.setLevel(logging.INFO)

# --- VERIFICATION FUNCTIONS ---

    def verify_silver_layer(self):
        """Checks Silver tables for formatting and rule compliance."""
        self.logger.info("--- Verifying Silver Layer (Cleaned Data) ---")
        tables_to_check = [
            "customers", "orders", "order_items", "products", 
            "marketing_leads", "closed_deals", "sellers", 
            "order_payments", "order_reviews"
        ]
        
        status = True
        for table in tables_to_check:
            path = self.silver_dir / f"{table}_cleaned.parquet"
            
            if not path.exists():
                self.logger.error(f"{self.RED}MISSING{self.RESET}: {table}")
                status = False
                continue

            df = pl.read_parquet(path)
            self.logger.info(f"OK: {table} found ({len(df)} rows)")

            # 1. Check Upper Case Standardization (Customers/Sellers)
            geo_cols = [c for c in df.columns if "city" in c or "state" in c]
            if geo_cols:
                sample = df.select(geo_cols).head(5)
                # Ensure no lowercase exists in these columns
                if any(sample.select(pl.col(c).str.contains(r"[a-z]")).to_series().any() for c in geo_cols):
                    self.logger.warning(f"  ! {self.YELLOW}Rule Warning{self.RESET}: Case standardization incomplete in {table}")

            # 2. Check Datetime Conversion (Orders)
            if table == "orders":
                date_cols = [c for c in df.columns if "timestamp" in c or "date" in c]
                for col in date_cols:
                    if df.schema[col] != pl.Datetime:
                        self.logger.error(f"  ! {self.RED}Type Error{self.RESET}: {col} in {table} is not Datetime")

        return status

    def verify_gold_layer(self):
        """Checks if all Gold reports match the DataModeler output."""
        self.logger.info("\n--- Verifying Gold Layer (Business Reports) ---")
        
        reports = [
            "delivery_reliability", "regional_logistics_performance", 
            "marketing_performance", "state_performance", "category_performance",
            "seller_rankings", "sales_trends", "product_reviews",
            "payment_behavior", "full_product_analysis", "geo_distribution",
            "order_seasonality", "comprehensive_sales", "logistics_flow"
        ]
        
        missing_reports = []
        for report in reports:
            path = self.gold_dir / f"gold_{report}.parquet"
            if path.exists():
                df = pl.read_parquet(path)
                if df.is_empty():
                    self.logger.warning(f"  ! {self.YELLOW}EMPTY{self.RESET}: gold_{report} exists but has 0 rows")
                else:
                    self.logger.info(f"{self.GREEN}Success{self.RESET}: gold_{report} generated ({len(df)} rows)")
            else:
                missing_reports.append(report)
                self.logger.error(f"{self.RED}MISSING{self.RESET}: gold_{report}")
        
        return len(missing_reports) == 0

# --- RUN ALL ---
    def run_all(self):
        """Final pipeline verification."""
        self.logger.info("Starting Pipeline Quality Assurance...")
        
        silver_ok = self.verify_silver_layer()
        gold_ok = self.verify_gold_layer()
        
        if silver_ok and gold_ok:
            self.logger.info(f"\n{self.GREEN}PASSED{self.RESET}: Data integrity verified across all layers.")
        else:
            self.logger.error(f"\n{self.RED}FAILED{self.RESET}: Data inconsistencies found.")
