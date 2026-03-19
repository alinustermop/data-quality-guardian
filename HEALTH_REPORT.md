# Data Quality Audit Report
**Generated on:** 2026-03-19
**Environment:** Production (Local)

## 1. Executive Summary
This report summarizes the health of the Olist e-commerce dataset after ingestion into the Bronze layer.

| Component | Audit Status | Success Rate | Issues Found |
| :--- | :--- | :--- | :--- |
| Customers Master | **PASSED** | 100.0% | 0 |
| Order Integrity | **FAILED** | 0.0% | 1 |

## 2. Detailed Audit Logs
### Audit: Customers Master
| Rule Description | Status | Logic |
| :--- | :--- | :--- |
| Values To Not Be Null | OK | Target: customer_id |
| Values To Be Unique | OK | Target: customer_id |
| Value Lengths To Be Between | OK | Target: customer_state |

### Audit: Order Integrity
| Rule Description | Status | Logic |
| :--- | :--- | :--- |
| Values To Be In Set | ERROR | Target: order_id |

## 3. Automated Actions Taken
- Data violating Relational Integrity was quarantined from the Silver layer.
- Null values in critical ID columns were removed during transformation.
- All strings standardized to Upper Case for join reliability.
