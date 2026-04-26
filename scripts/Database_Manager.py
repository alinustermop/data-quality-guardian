import logging
import polars as pl
from pathlib import Path
from scripts import constants

class DatabaseManager:
    """
    Handles the ingestion of raw CSV data into the Bronze layer (SQLite).
    """

    def __init__(self):
        self.conn = constants.DB_CONN
        self.raw_dir = Path(constants.RAW_DATA_DIR)
        self.db_path = Path(constants.DB_PATH)
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._setup_logging()

    def _setup_logging(self):
        """Helper to configure consistent logging across the project."""
        self.logger = logging.getLogger("DB_Manager")

        if not self.logger.hasHandlers():
            file_handler = logging.FileHandler(constants.LOG_FILE)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('  > %(message)s'))
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
            self.logger.setLevel(logging.INFO)

    def load_csv_to_sqlite(self, table_name: str, csv_filename: str):
        """Reads a CSV file using Polars and writes it to SQLite (Bronze layer).
        
        Args:
            table_name: The name of the target table in the database.
            csv_filename: The name of the source CSV file located in RAW_DATA_DIR.
        """

        file_path = Path(constants.RAW_DATA_DIR) / csv_filename
        
        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            return

        try:
            self.logger.info(f"Loading {csv_filename} into table '{table_name}'...")
            df = pl.read_csv(file_path)
            
            df.write_database(
                table_name=table_name,
                connection=self.conn,
                if_table_exists="replace",
                engine="adbc"
            )
            self.logger.info(f"Successfully loaded {len(df)} rows into {table_name}.")
        except Exception as e:
            self.logger.error(f"Failed to load {table_name}: {e}")

    def get_table_preview(self, table_name: str, limit: int = 5) -> pl.DataFrame:
        """
        Retrieves a small sample of rows from a database table for inspection.
        
        Args:
            table_name: Name of the table to query.
            n_rows: Number of rows to return.
        """

        query = f"SELECT * FROM {table_name} LIMIT {limit}"
        try:
            return pl.read_database_uri(query=query, uri=self.conn, engine="adbc")
        except Exception as e:
            self.logger.error(f"Could not preview table {table_name}: {e}")
            return pl.DataFrame()
        
    def run_initial_ingestion(self):
        """Iterates through the TABLES constant to populate the database."""
        self.logger.info("Starting initial database ingestion...")

        for table_name, csv_file in constants.TABLES.items():
            self.load_csv_to_sqlite(table_name, csv_file)
            
        self.logger.info("Ingestion process complete.")