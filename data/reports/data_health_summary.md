# OLIST DATA QUALITY AUDIT
Report Timestamp: 2026-04-25 21:40:30

## 1. Executive Summary
| Dataset | Result | Success Rate | Exceptions |
| :--- | :--- | :--- | :--- |
| Orders | PASS | 100.0% | 0 |
| Customer | PASS | 100.0% | 0 |
| Payments | PASS | 100.0% | 0 |
| Product | FAIL | 60.0% | 614 |
| Relational | PASS | 100.0% | 0 |

## 2. Detailed Validation Logs

### Orders
| Expectation Rule | Status | Column / Logic | Failures | Business Impact |
| :--- | :--- | :--- | :--- | :--- |
| Column Values To Not Be Null | VALID | order_id | 0 | Standard validation check. |
| Column Values To Be Unique | VALID | order_id | 0 | Standard validation check. |
| Column Values To Be In Set | VALID | order_status | 0 | Standard validation check. |

### Customer
| Expectation Rule | Status | Column / Logic | Failures | Business Impact |
| :--- | :--- | :--- | :--- | :--- |
| Column Values To Not Be Null | VALID | customer_id | 0 | Standard validation check. |
| Column Values To Be Unique | VALID | customer_id | 0 | Standard validation check. |
| Column Value Lengths To Be Between | VALID | customer_state | 0 | Standard validation check. |

### Payments
| Expectation Rule | Status | Column / Logic | Failures | Business Impact |
| :--- | :--- | :--- | :--- | :--- |
| Column Values To Not Be Null | VALID | payment_value | 0 | Standard validation check. |
| Column Values To Be Between | VALID | payment_value | 0 | Standard validation check. |

### Product
| Expectation Rule | Status | Column / Logic | Failures | Business Impact |
| :--- | :--- | :--- | :--- | :--- |
| Column Values To Not Be Null | INVALID | product_category_name | 610 | Standard validation check. |
| Column Values To Be Between | INVALID | product_weight_g | 4 | Standard validation check. |
| Column Values To Be Between | VALID | product_length_cm | 0 | Standard validation check. |
| Column Values To Be Between | VALID | product_height_cm | 0 | Standard validation check. |
| Column Values To Be Between | VALID | product_width_cm | 0 | Standard validation check. |

### Relational
| Expectation Rule | Status | Column / Logic | Failures | Business Impact |
| :--- | :--- | :--- | :--- | :--- |
| Table Row Count To Be Between | VALID | Table-Level | 0 | Standard validation check. |
