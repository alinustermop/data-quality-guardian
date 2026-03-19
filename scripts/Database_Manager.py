import polars as pl
import logging
import os
from scripts import constants

class DatabaseManager:
    def __init__(self):
        file_handler = logging.FileHandler(constants.LOG_FILE)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('  > %(message)s'))

        logging.basicConfig(
            level=logging.INFO,
            handlers=[file_handler, console_handler]
        )
        self.logger = logging.getLogger("DB_Manager")

    def load_csv_to_sqlite(self, table_name, csv_filename):
        """Reads a CSV with Polars and writes it to SQLite."""
        file_path = os.path.join(constants.RAW_DATA_DIR, csv_filename)
        
        if not os.path.exists(file_path):
            self.logger.error(f"File not found: {file_path}")
            return

        try:
            self.logger.info(f"Loading {csv_filename} into table '{table_name}'...")
            df = pl.read_csv(file_path)
            
            df.write_database(
                table_name=table_name,
                connection=f"sqlite:///{constants.DB_PATH}",
                if_table_exists="replace",
                engine="adbc"
            )
            self.logger.info(f"Successfully loaded {len(df)} rows into {table_name}.")
        except Exception as e:
            self.logger.error(f"Failed to load {table_name}: {e}")

    def get_table_preview(self, table_name, limit=5):
        """Verify the data was loaded."""
        query = f"SELECT * FROM {table_name} LIMIT {limit}"
        return pl.read_database(query, connection=f"sqlite:///{constants.DB_PATH}")