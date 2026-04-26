import logging
import warnings
import sys
from scripts.Database_Manager import DatabaseManager
from scripts.Quality_Guardian import QualityGuardian
from scripts.Data_Cleaner import DataCleaner
from scripts.Data_Modeler import DataModeler
from scripts.Verification import DataVerifier
from scripts.Data_Visualizer import DataVisualizer

# Silence Library Verbosity
logging.getLogger("great_expectations").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=UserWarning)

class PipelineOrchestrator:
    """
    Orchestrates the end-to-end data pipeline: Ingestion, Validation, Cleaning, Modeling, Verification, and Visualization.
    """
    
    def __init__(self):
        self.CYAN = "\033[96m"
        self.GREEN = "\033[92m"
        self.RED = "\033[91m"
        self.RESET = "\033[0m"

    def _print_header(self, text: str):
        print("="*50)
        print(f"{self.CYAN}{text.upper()}{self.RESET}")
        print("="*50)

    def run_pipeline(self):
        """Executes all pipeline stages in the correct sequence."""
        try:
            # 1. INGESTION (Bronze Layer)
            self._print_header("[STEP 1/6]: Ingesting Raw Data (Bronze)")
            db_manager = DatabaseManager()
            db_manager.run_initial_ingestion()
            print(f"{self.GREEN}SUCCESS{self.RESET}: Raw data loaded into SQLite.")

            # 2. QUALITY VALIDATION
            self._print_header("[STEP 2/6]: Data Quality Guard")
            guardian = QualityGuardian()
            guardian.run_all()
            print(f"{self.GREEN}SUCCESS{self.RESET}: Quality checks complete.")

            # 3. CLEANING (Silver Layer)
            self._print_header("[STEP 3/6]: Cleaning & Transformation (Silver)")
            cleaner = DataCleaner()
            cleaner.run_all()
            print(f"{self.GREEN}SUCCESS{self.RESET}: Silver layer Parquet files generated.")

            # 4. MODEL (Gold Layer)
            self._print_header("[STEP 4/6]: Business Logic & Modeling (Gold)")
            modeler = DataModeler()
            modeler.run_all()
            print(f"{self.GREEN}SUCCESS{self.RESET}: Gold layer business reports created.")

            # 5: VERIFICATION
            self._print_header("[STEP 5/6]: Final Integrity Verification")
            verifier = DataVerifier()
            verifier.run_all()

            # # 6: VISUALIZATION
            # self._print_header("[STEP 6/6]: Generating Executive Insights")
            # visualizer = DataVisualizer()
            # visualizer.generate_all_visuals()

            # self._print_header("Pipeline Execution Complete")
            # print(f"{self.GREEN}All stages processed successfully.{self.RESET}\n")

        except Exception as e:
            print(f"\n{self.RED}CRITICAL ERROR{self.RESET} during pipeline execution: {e}")
            sys.exit(1)

if __name__ == "__main__":
    orchestrator = PipelineOrchestrator()
    orchestrator.run_pipeline()