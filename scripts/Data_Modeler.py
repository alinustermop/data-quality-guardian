import logging
import polars as pl
from pathlib import Path
from scripts import constants

class DataModeler:
    """
    Handles the transformation of 'Silver' layer data into 'Gold' layer
    business-level reports and aggregates.
    """
    def __init__(self):
        # Paths from constants
        self.silver_dir = Path(constants.PROCESSED_DATA_DIR)
        self.gold_dir = Path(constants.GOLD_DATA_DIR)
        self.raw_dir = Path(constants.RAW_DATA_DIR)
        
        self.gold_dir.mkdir(parents=True, exist_ok=True)

        # Color constants for terminal output
        self.GREEN = "\033[92m"
        self.RED = "\033[91m"
        self.RESET = "\033[0m"

        self._setup_logging()
    
    def _setup_logging(self):
        """Helper to configure logging for the modeling process."""
        self.logger = logging.getLogger("Data_Modeler")
        if not self.logger.hasHandlers():
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('  > %(message)s'))
            self.logger.addHandler(console_handler)
            self.logger.setLevel(logging.INFO)

    def _load_silver_table(self, table_name: str) -> pl.DataFrame:
        """Helper to load a specific parquet table from the silver directory."""
        path = self.silver_dir / f"{table_name}_cleaned.parquet"
        if not path.exists():
            self.logger.error(f"Required Silver table {self.RED}missing{self.RESET}: {path}")
            return pl.DataFrame()
        return pl.scan_parquet(path)

    def _save_and_log(self, df: pl.DataFrame, name: str):
        """Helper to save gold parquet and print status."""
        if isinstance(df, pl.LazyFrame):
            df = df.collect()
            
        path = self.gold_dir / f"gold_{name}.parquet"
        df.write_parquet(path)
        self.logger.info(f"Gold Report: {name.replace('_', ' ').title()} saved ({len(df)} rows)")
        if df.is_empty(): 
            raise ValueError(f"{self.RED}Report {name} is empty!{self.RESET} Check Silver sources.")

# --- REPORT GENERATION FUNCTIONS ---

    def create_gold_delivery_reliability(self) -> pl.DataFrame:
        """Analyzes delivery reliability: identifies late orders, average delays, and percentage of missed estimates per customer."""
        orders = self._load_silver_table("orders")
        
        # Logic: Calculate day delta between actual and promised delivery to flag late orders
        report = (
            orders.filter(
                pl.col("order_delivered_customer_date").is_not_null() & 
                pl.col("order_estimated_delivery_date").is_not_null()
            )
            .with_columns([
                # Delay = Actual - Promised. Positive number = Late.
                ((pl.col("order_delivered_customer_date") - pl.col("order_estimated_delivery_date"))
                 .dt.total_days()).alias("delay_days")
            ])
            .group_by("customer_id")
            .agg([
                pl.col("delay_days").mean().alias("avg_delay_days"),
                # Count how many orders were actually late (delay > 0)
                (pl.col("delay_days") > 0).sum().alias("total_late_orders"),
                pl.len().alias("total_orders")
            ])
            .with_columns(
                (pl.col("total_late_orders") / pl.col("total_orders") * 100).alias("late_rate_pct")
            )
        )

        self._save_and_log(report, "delivery_reliability")
        return report

    def create_gold_regional_logistics_efficiency(self) -> pl.DataFrame:
        """Calculates regional shipping performance: actual vs. estimated times by state."""

        orders = self._load_silver_table("orders")
        cust = self._load_silver_table("customers")

        # Logic: Join geography and calculate actual vs. forecasted delivery time
        report = (
            orders.join(cust, on="customer_id", how="inner")
            .filter(
                pl.col("order_delivered_customer_date").is_not_null() &
                pl.col("order_purchase_timestamp").is_not_null()
            )
            .with_columns([
                # How long it actually took
                (pl.col("order_delivered_customer_date") - pl.col("order_purchase_timestamp"))
                .dt.total_days().alias("actual_days"),
                # How long we thought it would take
                (pl.col("order_estimated_delivery_date") - pl.col("order_purchase_timestamp"))
                .dt.total_days().alias("estimated_days")
            ])
            .group_by("customer_state")
            .agg([
                pl.col("actual_days").mean().alias("avg_actual_delivery_time"),
                pl.col("estimated_days").mean().alias("avg_forecasting_estimate"),
                (pl.col("actual_days") - pl.col("estimated_days")).mean().alias("prediction_error_days")
            ])
            .sort("avg_actual_delivery_time", descending=True)
        )

        self._save_and_log(report, "regional_logistics_performance")
        return report

    def create_gold_marketing_performance(self) -> pl.DataFrame:
        """Analyzes marketing performance: aggregates total leads, conversion rates, and sales velocity per origin channel."""
        leads = self._load_silver_table("marketing_leads")
        deals = self._load_silver_table("closed_deals")

        # Logic: Join leads with deals to calculate conversion success and time-to-close
        report = (
            leads.join(deals, on="mql_id", how="left")
            .with_columns([
                # Explicitly identify successful conversions
                (pl.col("won_date").is_not_null()).alias("is_converted"),
                
                # Calculate time-to-close (Sales Velocity)
                ((pl.col("won_date") - pl.col("first_contact_date")).dt.total_days()).alias("days_to_close")
            ])
            .group_by("origin")
            .agg([
                pl.col("mql_id").count().alias("total_leads"),
                pl.col("is_converted").sum().alias("converted_deals"),
                # Mean ignores nulls by default in Polars
                pl.col("days_to_close").mean().alias("avg_days_to_close")
            ])
            .with_columns(
                # Calculate conversion percentage
                (pl.col("converted_deals") / pl.col("total_leads") * 100).alias("conversion_rate_pct")
            )
            .sort("conversion_rate_pct", descending=True)
        )

        self._save_and_log(report, "marketing_performance")
        return report

    def create_gold_state_performance(self) -> pl.DataFrame:
        """Aggregates geographic performance: analyzes revenue distribution, order volume, and logistics costs by customer state."""

        items = self._load_silver_table("order_items")
        orders = self._load_silver_table("orders")
        cust = self._load_silver_table("customers")

        # Logic: Join orders and customer geography to attribute revenue and freight costs to specific regions
        report = (
            items.join(orders, on="order_id", how="left")
                 .join(cust, on="customer_id", how="left")
                 .group_by("customer_state")
                 .agg([
                    pl.col("price").sum().alias("total_revenue"),
                    pl.col("order_id").n_unique().alias("total_orders"),
                    pl.col("freight_value").mean().alias("avg_freight_cost")
                 ])
                 .sort("total_revenue", descending=True)
        )

        self._save_and_log(report, "state_performance")
        return report

    def create_gold_category_performance(self) -> pl.DataFrame:
        """Summary by category: total revenue, market volume, customer satisfaction (reviews), and catalog diversity."""
        items = self._load_silver_table("order_items")
        prod = self._load_silver_table("products")
        reviews = self._load_silver_table("order_reviews")

        # Logic: Combine product metadata with sales and reviews to assess category-level profitability and quality
        report = (
            items.join(prod, on="product_id", how="inner")
                 .join(reviews, on="order_id", how="left")
                 .group_by("product_category_name_english")
                 .agg([
                    pl.col("price").sum().alias("total_revenue"),
                    pl.col("order_id").n_unique().alias("order_count"),
                    pl.col("review_score").mean().alias("average_review_score"),
                    pl.col("product_id").n_unique().alias("product_count")
                 ])
                 .sort("total_revenue", descending=True)
        )

        self._save_and_log(report, "category_performance")
        return report

    def create_gold_seller_ranking(self) -> pl.DataFrame:
        """Ranks marketplace sellers: identifies top-performing partners based on sales value, order fulfillment, and assortment variety."""

        items = self._load_silver_table("order_items")

        # Logic: Group by seller to calculate total GMV and product assortment depth
        report = (
            items.group_by("seller_id")
                 .agg([
                    pl.col("price").sum().alias("total_sales_value"),
                    pl.col("product_id").n_unique().alias("unique_products_offered"),
                    pl.col("order_id").count().alias("total_orders_handled")
                ])
                 .sort("total_sales_value", descending=True)
        )

        self._save_and_log(report, "seller_rankings")
        return report
    
    def create_gold_sales_trends(self) -> pl.DataFrame:
        """Aggregates time-series sales data: tracks monthly revenue growth, order volume, and Average Order Value (AOV) to identify seasonality."""

        orders = self._load_silver_table("orders").filter(pl.col("is_completed_transaction") == True)
        payments = self._load_silver_table("order_payments")
        
        # Logic: Extract time components and join payment values to calculate performance trends over chronological months
        report = (
            orders.join(payments, on="order_id", how="inner")
            .with_columns([
                pl.col("order_purchase_timestamp").dt.year().alias("year"),
                pl.col("order_purchase_timestamp").dt.month().alias("month"),
                pl.col("order_purchase_timestamp").dt.truncate("1mo").alias("month_year")
            ])
            .group_by(["year", "month", "month_year"])
            .agg([
                pl.col("payment_value").sum().alias("total_revenue"),
                pl.col("order_id").n_unique().alias("order_count")
            ])
            .with_columns(
                (pl.col("total_revenue") / pl.col("order_count")).alias("average_order_value")
            )
            .sort("month_year")
        )

        self._save_and_log(report, "sales_trends")
        return report

    def create_gold_product_reviews(self) -> pl.DataFrame:
        """Analyzes product quality feedback: aggregates customer review scores by category to identify top-performing product lines."""
        items = self._load_silver_table("order_items")
        products = self._load_silver_table("products")
        reviews = self._load_silver_table("order_reviews")

        # Logic: Join items with products and cleaned reviews to identify category-level satisfaction trends
        report = (
            items.join(products, on="product_id", how="inner")
            .join(reviews, on="order_id", how="inner")
            .group_by("product_category_name_english")
            .agg([
                pl.col("review_score").mean().alias("avg_score"),
                pl.col("review_id").count().alias("review_count")
            ])
            .filter(pl.col("review_count") > 50) # Logic: Only show categories with significant data
            .sort("avg_score", descending=True)
        )

        self._save_and_log(report, "product_reviews")
        return report

    def create_gold_payment_behavior(self) -> pl.DataFrame:
        """Analyzes customer checkout behavior: evaluates the relationship between payment methods, installment usage, and average transaction value."""
        payments = self._load_silver_table("order_payments")
        orders = self._load_silver_table("orders")

        # Logic: Use cleaned payment types and values to determine the average financial footprint per payment method
        report = (
            payments.join(orders, on="order_id", how="inner")
            .group_by("payment_type")
            .agg([
                pl.col("payment_value").mean().alias("avg_value"),
                pl.col("payment_installments").mean().alias("avg_installments"),
                pl.col("order_id").n_unique().alias("transaction_count")
            ])
            .sort("avg_value", descending=True)
        )

        self._save_and_log(report, "payment_behavior")
        return report

    def create_gold_full_product_analysis(self) -> pl.DataFrame:
        """Enriches product data: merges inventory items with localized category translations to enable multi-language catalog reporting."""
        
        items = self._load_silver_table("order_items")
        products = self._load_silver_table("products")

        # Logic: Combine items with already-cleaned and translated product metadata for deep-dive reporting
        report = (
            items.join(products, on="product_id", how="inner")
        )

        self._save_and_log(report, "full_product_analysis")
        return report

    def create_gold_geospatial_distribution(self) -> pl.DataFrame:
        """Maps customer density: aggregates geographical coordinates and zip code prefixes to visualize regional market penetration."""
        customers = self._load_silver_table("customers")
        geo_path = self.raw_dir / "brazil_geo.json"

        geo = (
            pl.read_json(geo_path)
            .explode("features")
            .select([
                pl.col("features").struct.field("id").alias("state_id"),
                pl.col("features").struct.field("properties").struct.field("name").alias("state_name")
            ])
        ).lazy()
        # Logic: Join customer records with standardized Silver coordinates to create a high-resolution density map
        report = (
            customers.join(
                geo, 
                left_on="customer_state", 
                right_on="state_id", 
                how="inner"
            )
            .group_by(["customer_state", "state_name"])
            .agg(pl.col("customer_id").count().alias("customer_count"))
        )

        self._save_and_log(report, "geo_distribution")
        return report

    def create_gold_order_seasonality(self) -> pl.DataFrame:
        """Identifies temporal purchasing patterns: extracts cyclical trends by day of week and hour of day to optimize marketing and logistics timing."""

        orders = self._load_silver_table("orders")

        # Logic: Transform purchase timestamps into discrete time bins (weekday/hour) to surface hourly peak loads and weekly fluctuations
        report = (
            orders.with_columns([
                pl.col("order_purchase_timestamp").dt.weekday().alias("weekday"),
                pl.col("order_purchase_timestamp").dt.hour().alias("hour")
            ])
            .group_by(["weekday", "hour"])
            .agg(pl.col("order_id").count().alias("order_volume"))
            .sort(["weekday", "hour"])
        )

        self._save_and_log(report, "order_seasonality")
        return report

    def create_gold_comprehensive_sales(self) -> pl.DataFrame:
        """Constructs a master sales dataset: integrates order headers, payment details, and customer attributes into a single wide table."""
        
        orders = self._load_silver_table("orders")
        payments = self._load_silver_table("order_payments")
        cust = self._load_silver_table("customers")
        
        # Logic: Create a unified view of the sales cycle by linking transaction values to specific customer demographics and order statuses
        report = (
            orders.join(payments, on="order_id", how="inner")
                  .join(cust, on="customer_id", how="inner")
        )

        self._save_and_log(report, "comprehensive_sales")
        return report

    def create_gold_logistics_flow(self) -> pl.DataFrame:
        """Maps supply chain movement: creates a state-to-state origin-destination matrix to analyze inter-regional trade volume."""
        items = self._load_silver_table("order_items")
        sellers = self._load_silver_table("sellers")
        cust = self._load_silver_table("customers")

        # Logic: Link sellers and customers through order items to calculate fulfillment flow between different geographic states
        report = (
            items.join(sellers, on="seller_id", how="inner")
                 .join(self._load_silver_table("orders"), on="order_id", how="inner")
                 .join(cust, on="customer_id", how="inner")
                 .select([
                     pl.col("seller_state").alias("origin"),
                     pl.col("customer_state").alias("destination"),
                     pl.col("order_id")
                 ])
                 .group_by(["origin", "destination"])
                 .agg(pl.col("order_id").count().alias("order_count"))
        )

        self._save_and_log(report, "logistics_flow")
        return report

    def create_gold_geospatial_lookup(self) -> pl.DataFrame:
        """Prepares a validated geolocation dimension table: provides a single source of truth for coordinate mapping."""

        geo_path = self.raw_dir / "brazil_geo.json"
        geo = (
            pl.read_json(geo_path)
            .explode("features")
            .select([
                pl.col("features").struct.field("id").alias("state_id"),
                pl.col("features").struct.field("properties").struct.field("name").alias("state_name")
            ])
        ).lazy()
            
        # Logic: Pass through the cleaned silver geolocation data to the gold layer for direct BI tool consumption
        self._save_and_log(geo, "geolocation_lookup")
        return geo
    
# --- RUN ALL ---

    def run_all(self) -> None:
        """Executes the full Gold layer suite to refresh all business reports."""
        self.logger.info("Starting Gold Layer Generation...")
        
        # Performance & Ranking
        self.create_gold_state_performance()
        self.create_gold_category_performance()
        self.create_gold_seller_ranking()
        
        # Trends & Seasonality
        self.create_gold_sales_trends()
        self.create_gold_order_seasonality()
        
        # Logistics & Efficiency
        self.create_gold_regional_logistics_efficiency()
        self.create_gold_logistics_flow()
        self.create_gold_delivery_reliability()
        
        # Marketing & Customer Behavior
        self.create_gold_marketing_performance()
        self.create_gold_payment_behavior()
        self.create_gold_product_reviews()
        
        # Geospatial
        self.create_gold_geospatial_distribution()
        self.create_gold_geospatial_lookup()

        self.create_gold_full_product_analysis()
        self.create_gold_comprehensive_sales()
        
        self.logger.info(f"{self.GREEN}SUCCESS{self.RESET}: Gold Layer processing complete.")