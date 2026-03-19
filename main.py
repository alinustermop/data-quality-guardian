import logging
import warnings
from scripts.Database_Manager import DatabaseManager
from scripts.Quality_Guardian import QualityGuardian
from scripts.Data_Cleaner import DataCleaner
from scripts.Data_Modeler import DataModeler
from scripts import constants

# Silence Library Verbosity
logging.getLogger("great_expectations").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=UserWarning) # Hides GX version warnings

def main():
    print("="*50)
    print("      DATA QUALITY GUARDIAN: PIPELINE START      ")
    print("="*50)

    # 1. INGEST (Bronze)
    db = DatabaseManager()
    print("\n[STEP 1/4] Data Ingestion")
    print("-" * 40)
    for table_name, csv_file in constants.TABLES.items():
        db.load_csv_to_sqlite(table_name, csv_file)

    # 2. VALIDATE
    print("\n[STEP 2/4] Quality Validation")
    print("-" * 40)
    guardian = QualityGuardian()
    c_res = guardian.validate_customers()
    r_res = guardian.validate_relational_integrity()
    
    guardian.save_report([
        ("Customers Master", c_res),
        ("Order Integrity", r_res)
    ])
    print("DONE: Health report generated.")

    # 3. CLEAN (Silver)
    print("\n[STEP 3/4] Data Transformation (Silver Layer)")
    print("-" * 40)
    cleaner = DataCleaner()
    cleaner.clean_customers()
    cleaner.clean_order_items()

    # 4. MODEL (Gold)
    print("\n[STEP 4/4] Business Intelligence (Gold Layer)")
    print("-" * 40)
    modeler = DataModeler()
    modeler.create_revenue_report()

    print("\n" + "="*50)
    print("      PIPELINE COMPLETE: DATA IS READY      ")
    print("="*50)

if __name__ == "__main__":
    main()