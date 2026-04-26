import logging
import polars as pl
from pathlib import Path
from datetime import datetime
import great_expectations as gx
from scripts import constants

class QualityGuardian:
    """
    Handles data quality validation using Great Expectations to ensure 
    raw 'Bronze' data meets standards before cleaning.
    """

    def __init__(self):
        # Silence verbose logs
        logging.getLogger("great_expectations").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
        
        self.context = gx.get_context()
        self.conn = constants.DB_CONN
        
        # Color constants for terminal output
        self.GREEN = "\033[92m"
        self.RED = "\033[91m"
        self.YELLOW = "\033[93m"
        self.RESET = "\033[0m"
        
        self.results_store = []
        self._setup_logging()
        self._setup_datasource()

    def _setup_logging(self):
        """Helper to configure logging."""
        self.logger = logging.getLogger("Quality_Guardian")
        if not self.logger.hasHandlers():
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('  > %(message)s'))
            self.logger.addHandler(console_handler)
            self.logger.setLevel(logging.INFO)

    def _setup_datasource(self):
        """Initializes the GX SQLite datasource."""
        ds_name = "olist_datasource"
        try:
            self.datasource = self.context.data_sources.get(ds_name)
        except Exception:
            self.datasource = self.context.data_sources.add_sqlite(
                name=ds_name, connection_string=self.conn
            )

    def _get_batch_definition(self, asset_name: str, table_name: str):
        """Helper to get or create a table asset and its batch definition."""
        try:
            asset = self.datasource.add_table_asset(name=asset_name, table_name=table_name)
            return asset.add_batch_definition_whole_table(f"{asset_name}_batch")
        except Exception:
            asset = self.datasource.get_asset(asset_name)
            return asset.get_batch_definition(f"{asset_name}_batch")

    def _get_or_create_suite(self, suite_name: str):
        """Helper to get an existing suite or create a new one."""
        try:
            return self.context.suites.add(gx.ExpectationSuite(name=suite_name))
        except Exception:
            return self.context.suites.get(suite_name)

    def _run_validation(self, name, batch_def, suite):
        """Helper to create and run a validation definition."""
        try:
            val_def = self.context.validation_definitions.add(
                gx.ValidationDefinition(name=name, data=batch_def, suite=suite)
            )
        except Exception:
            val_def = self.context.validation_definitions.get(name)
        
        res = val_def.run()
        
        for result in res.results:
            if 'unexpected_count' not in result.result:
                result.result['unexpected_count'] = 0
                
        self.results_store.append((name, res))
        return res


# --- VALIDATION FUNCTIONS ---

    def guard_orders(self):
        """Validates the orders table: checks for unique IDs and valid status values."""
        batch_def = self._get_batch_definition("orders_asset", "orders")
        suite = self._get_or_create_suite("orders_raw_check")
        
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="order_id"))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="order_id"))
        
        valid_statuses = ["delivered", "shipped", "canceled", "invoiced", "processing", "approved", "unavailable", "created"]
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(
            column="order_status", value_set=valid_statuses
        ))

        self._run_validation("orders_validation", batch_def, suite)
        self.logger.info(f"{self.GREEN}Success{self.RESET}: Orders expectations validated.")

    def guard_customers(self):
        """Validates customer table: checks for nulls, uniqueness, and state code lengths."""
        batch_def = self._get_batch_definition("customers_asset", "customers")
        suite = self._get_or_create_suite("customer_quality_suite")

        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="customer_id"))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="customer_id"))
        suite.add_expectation(gx.expectations.ExpectColumnValueLengthsToBeBetween(
            column="customer_state", min_value=2, max_value=2
        ))

        self._run_validation("customer_validation", batch_def, suite)
        self.logger.info(f"{self.GREEN}Success{self.RESET}: Customer expectations validated.")

    def guard_payments(self):
        """Validates payment data: ensures no negative values exist in financial records."""
        batch_def = self._get_batch_definition("payments_asset", "order_payments")
        suite = self._get_or_create_suite("payments_raw_check")
        
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="payment_value"))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(
            column="payment_value", min_value=0, max_value=None
        ))
        
        self._run_validation("payments_validation", batch_def, suite)
        self.logger.info(f"{self.GREEN}Success{self.RESET}: Payments expectations validated.")

    def guard_products(self):
        """Validates product table: checks for missing categories and positive dimensions."""
        batch_def = self._get_batch_definition("products_asset", "products")
        suite = self._get_or_create_suite("product_quality_suite")

        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(
            column="product_category_name",
            notes="Critical for downstream sales analysis by department."
        ))
        
        dimension_cols = ["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]
        for col in dimension_cols:
            suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(
                column=col, 
                min_value=0.1,
                notes="Ensures logistics calculations do not divide by zero or negative."
            ))

        self._run_validation("product_validation", batch_def, suite)
        self.logger.info(f"{self.GREEN}Success{self.RESET}: Product expectations validated.")

    def guard_relational_integrity(self):
        """Validates relational integrity: verifies order_items link to existing orders."""

        order_ids = pl.read_database_uri("SELECT order_id FROM orders", uri=self.conn, engine="adbc")
        item_ids = pl.read_database_uri("SELECT order_id FROM order_items", uri=self.conn, engine="adbc")

        orphans = item_ids.join(order_ids, on="order_id", how="anti")
        orphan_count = len(orphans)

        batch_def = self._get_batch_definition("relational_items_asset", "order_items")
        suite = self._get_or_create_suite("relational_integrity_suite")

        suite.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(
            min_value=0, 
            max_value=0 if orphan_count > 0 else None
        ))
        
        res = self._run_validation("relational_validation", batch_def, suite)
        if not res.success:
            res.results[0].result['unexpected_count'] = orphan_count
            self.logger.info(f"{self.RED}Failure{self.RESET}: Found {orphan_count} orphaned records.")

    def generate_health_report(self):
        """Generates an enhanced Markdown health report with failure counts and impact analysis."""
        report_path = Path(self.conn.replace("sqlite:///", "")).parent / "reports" / "data_health_summary.md"
        report_path.parent.mkdir(exist_ok=True)
    
        with open(report_path, "w") as f:
            f.write("# OLIST DATA QUALITY AUDIT\n")
            f.write(f"Report Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## 1. Executive Summary\n")
            f.write("| Dataset | Result | Success Rate | Exceptions |\n")
            f.write("| :--- | :--- | :--- | :--- |\n")
            
            for name, res in self.results_store:
                stats = res.statistics
                status = "PASS" if res.success else "FAIL"
                rate = f"{stats['success_percent']:.1f}%"
                exceptions = sum(
                    check.result.get('unexpected_count', 0) or 0 
                    for check in res.results
                )
                f.write(f"| {name.replace('_validation', '').title()} | {status} | {rate} | {exceptions} |\n")
            
            f.write("\n## 2. Detailed Validation Logs\n")
            for name, res in self.results_store:
                f.write(f"\n### {name.replace('_validation', '').title()}\n")
                f.write("| Expectation Rule | Status | Column / Logic | Failures | Business Impact |\n")
                f.write("| :--- | :--- | :--- | :--- | :--- |\n")
                
                for check in res.results:
                    config = check.expectation_config
                    rule = config.type.replace("expect_", "").replace("_", " ").title()
                    status = "VALID" if check.success else "INVALID"
                    col = config.kwargs.get('column', 'Table-Level')
                    fail_count = check.result.get('unexpected_count', 0)
                    
                    meta = config.meta or {}
                    notes = meta.get('notes', 'Standard validation check.')
                    
                    f.write(f"| {rule} | {status} | {col} | {fail_count} | {notes} |\n")


# --- RUN ALL ---

    def run_all(self):
        """Executes the full quality gate sequence."""
        self.logger.info("Starting Data Quality Guard (Bronze Layer)...")
        
        self.results_store = []
        
        # Execute validations
        self.guard_orders()
        self.guard_customers()
        self.guard_payments()
        self.guard_products()
        self.guard_relational_integrity()
        
        # Generate final documentation
        self.generate_health_report()