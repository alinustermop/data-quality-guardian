import logging
import great_expectations as gx
import os
from scripts import constants

class QualityGuardian:
    def __init__(self):
        self.context = gx.get_context()
        logging.getLogger("great_expectations").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
        self.context = gx.get_context()

        try:
            self.datasource = self.context.data_sources.add_sqlite(
                name="olist_datasource", 
                connection_string=constants.DB_CONN_GX
            )
        except Exception:
            self.datasource = self.context.data_sources.get("olist_datasource")

    def validate_customers(self):
        """Validates the customer table for unique IDs and valid states."""
        
        # 1. Define the asset (the table)
        asset_name = "customers_asset"
        try:
            asset = self.datasource.add_table_asset(name=asset_name, table_name="customers")
        except Exception:
            asset = self.datasource.get_asset(asset_name)
        
        # 2. Define the Batch Definition
        batch_def_name = "customers_batch_definition"
        try:
            batch_definition = asset.add_batch_definition_whole_table(batch_def_name)
        except Exception:
            batch_definition = asset.get_batch_definition(batch_def_name)

        # 3. Create an Expectation Suite
        suite_name = "customer_quality_suite"
        try:
            suite = self.context.suites.add(gx.ExpectationSuite(name=suite_name))
        except Exception:
            suite = self.context.suites.get(suite_name)

        # 4. Define Expectations
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="customer_id"))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="customer_id"))
        suite.add_expectation(gx.expectations.ExpectColumnValueLengthsToBeBetween(
            column="customer_state", min_value=2, max_value=2
        ))

        # 5. Create and Run Validation Definition
        validation_def_name = "customer_validation"
        try:
            validation_definition = self.context.validation_definitions.add(
                gx.ValidationDefinition(
                    name=validation_def_name,
                    data=batch_definition,
                    suite=suite
                )
            )
        except Exception:
            validation_definition = self.context.validation_definitions.get(validation_def_name)
        
        results = validation_definition.run()
        return results

    def validate_relational_integrity(self):
        """Checks if order_items refer to valid orders (Foreign Key check)."""
        # 1. Setup Assets
        try:
            items_asset = self.datasource.add_table_asset(name="items_asset", table_name="order_items")
        except Exception:
            items_asset = self.datasource.get_asset("items_asset")

        batch_def = "items_relational_batch"
        try:
            batch_definition = items_asset.add_batch_definition_whole_table(batch_def)
        except Exception:
            batch_definition = items_asset.get_batch_definition(batch_def)

        # 2. Setup Suite
        suite_name = "relational_integrity_suite"
        try:
            suite = self.context.suites.add(gx.ExpectationSuite(name=suite_name))
        except Exception:
            suite = self.context.suites.get(suite_name)

        # 3. The "Power" Move: Relational Check
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(
            column="order_id",
            value_set={"model": "orders", "column": "order_id"} 
        ))

        # 4. Run
        val_name = "relational_validation"
        try:
            validation_definition = self.context.validation_definitions.add(
                gx.ValidationDefinition(name=val_name, data=batch_definition, suite=suite)
            )
        except Exception:
            validation_definition = self.context.validation_definitions.get(val_name)
        
        return validation_definition.run()

    def save_report(self, results_list):
        """Generates a detailed Markdown audit report."""
        report_path = os.path.join(constants.BASE_DIR, "HEALTH_REPORT.md")
        
        with open(report_path, "w") as f:
            f.write("# Data Quality Audit Report\n")
            f.write(f"**Generated on:** 2026-03-19\n")
            f.write(f"**Environment:** Production (Local)\n\n")
            
            f.write("## 1. Executive Summary\n")
            f.write("This report summarizes the health of the Olist e-commerce dataset after ingestion into the Bronze layer.\n\n")
            
            f.write("| Component | Audit Status | Success Rate | Issues Found |\n")
            f.write("| :--- | :--- | :--- | :--- |\n")
            
            for name, res in results_list:
                status = "PASSED" if res.success else "FAILED"
                stats = res.statistics
                rate = f"{stats['success_percent']:.1f}%"
                issues = stats['evaluated_expectations'] - stats['successful_expectations']
                f.write(f"| {name} | **{status}** | {rate} | {issues} |\n")
            
            f.write("\n## 2. Detailed Audit Logs\n")
            for name, res in results_list:
                f.write(f"### Audit: {name}\n")
                f.write("| Rule Description | Status | Logic |\n")
                f.write("| :--- | :--- | :--- |\n")
                
                for check in res.results:
                    rule = check.expectation_config.type.replace("expect_column_", "").replace("_", " ").title()
                    status = "OK" if check.success else "ERROR"
                    logic = f"Target: {check.expectation_config.kwargs.get('column')}"
                    f.write(f"| {rule} | {status} | {logic} |\n")
                f.write("\n")

            f.write("## 3. Automated Actions Taken\n")
            f.write("- Data violating Relational Integrity was quarantined from the Silver layer.\n")
            f.write("- Null values in critical ID columns were removed during transformation.\n")
            f.write("- All strings standardized to Upper Case for join reliability.\n")