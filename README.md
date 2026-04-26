# Olist E-Commerce Data Pipeline
A modular data engineering pipeline designed to transform raw Olist e-commerce data into business-ready analytical assets. The project implements a Medallion Architecture to ensure data integrity, traceability, and performance.

## Key Features
* **Medallion Data Architecture**: Orchestrates data through three distinct layers:
    * **Bronze (Raw)**: SQLite-based relational staging of raw CSV data.
    * **Silver (Cleaned)**: Parquet-backed layer with standardized schemas, deduplicated records, and normalized formatting.
    * **Gold (Business)**: Aggregated analytical reports optimized for executive insights and BI consumption.
* **Automated Quality Gating**: Integrates `Great Expectations` to perform rigorous validation on the Bronze layer, catching nulls, schema drifts, and relational inconsistencies before cleaning.
* **High-Performance ETL**: Built with `Polars` to leverage multi-threaded processing and LazyFrame execution for efficient data manipulation.
* **Automated Verification**: Includes a post-processing verification suite that audits the existence, volume, and integrity of the generated Parquet files.
* **Structured Logging & Auditing**: Features a centralized logging system and generates a Markdown-based `data_health_summary.md` after every run to track pipeline health.

## Tech Stack
* **Language**: Python 3.x
* **Data Processing**: Polars
* **Quality Assurance**: Great Expectations
* **Storage**: SQLite (Staging) & Apache Parquet (Processing/Output)
* **Orchestration**: Custom Python-based Orchestrator (`main.py`)
* **Environment**: `pathlib` for robust cross-platform path management

## Data Architecture
The system follows a strict logical flow to ensure reliability:
1.  **Ingestion**: `Database_Manager` loads raw CSVs into a relational SQLite database.
2.  **Validation**: `Quality_Guardian` runs pre-defined expectation suites to audit data health.
3.  **Cleaning**: `Data_Cleaner` standardizes types (e.g., datetime), handles missing values, and persists to Parquet.
4.  **Modeling**: `Data_Modeler` joins disparate tables to create complex reports like `delivery_reliability` and `seller_rankings`.
5.  **Verification**: `DataVerifier` performs a final sanity check on all output files.

## Project Structure
```text
PROJECT/
├── data/
│   ├── olist_raw.db          # Bronze Layer (SQLite)
│   ├── gold/                 # Gold Layer (Aggregated Parquet)
│   ├── processed/            # Silver Layer (Cleaned Parquet)
│   ├── raw/                  # Source CSV files
│   └── reports/              # Quality audit results (MD)
├── scripts/
│   ├── Database_Manager.py   # Ingestion logic
│   ├── Quality_Guardian.py   # Great Expectations integration
│   ├── Data_Cleaner.py       # Silver transformation logic
│   ├── Data_Modeler.py       # Gold aggregation logic
│   ├── Verification.py       # Integrity testing suite
│   └── constants.py          # Configuration and path management
├── main.py                   # Pipeline Orchestrator
└── requirements.txt          # Project dependencies
```

## Setup & Usage
1.  **Clone the repository**.
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure environment**: Update paths in `constants.py` if necessary.
4.  **Run the pipeline**:
    ```bash
    python main.py
    ```
    The orchestrator will execute all six stages of the pipeline in sequence and output a summary to the console.

## Future Work
* **Visualization Suite**: Integration of Seaborn/Matplotlib for automated executive dashboards.
* **Advanced Polars Optimization**: Transitioning all cleaning operations to 100% LazyFrame execution for improved memory efficiency.
* **Live Quality Guard**: Implementing the Quality Guardian as a persistent decorator-based service.

## Disclaimer
This project is for educational and portfolio purposes, utilizing the public Olist dataset available on Kaggle.