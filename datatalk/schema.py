from __future__ import annotations


DDL = """
CREATE TABLE customers (
  customer_id INTEGER PRIMARY KEY,
  customer_name TEXT NOT NULL,
  segment TEXT NOT NULL,
  region TEXT NOT NULL,
  industry TEXT NOT NULL,
  joined_date TEXT NOT NULL
);

CREATE TABLE products (
  product_id INTEGER PRIMARY KEY,
  product_name TEXT NOT NULL,
  category TEXT NOT NULL,
  list_price REAL NOT NULL
);

CREATE TABLE sales_orders (
  order_id INTEGER PRIMARY KEY,
  order_date TEXT NOT NULL,
  customer_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  region TEXT NOT NULL,
  channel TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  unit_price REAL NOT NULL,
  discount_pct REAL NOT NULL,
  FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
  FOREIGN KEY(product_id) REFERENCES products(product_id)
);

CREATE TABLE support_tickets (
  ticket_id INTEGER PRIMARY KEY,
  opened_date TEXT NOT NULL,
  closed_date TEXT,
  customer_id INTEGER NOT NULL,
  product_id INTEGER,
  priority TEXT NOT NULL,
  status TEXT NOT NULL,
  sentiment_score INTEGER NOT NULL,
  issue_type TEXT NOT NULL,
  FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
  FOREIGN KEY(product_id) REFERENCES products(product_id)
);

CREATE TABLE employees (
  employee_id INTEGER PRIMARY KEY,
  employee_name TEXT NOT NULL,
  department TEXT NOT NULL,
  region TEXT NOT NULL,
  hire_date TEXT NOT NULL,
  status TEXT NOT NULL,
  left_date TEXT,
  performance_band TEXT NOT NULL
);

CREATE TABLE invoices (
  invoice_id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL,
  invoice_date TEXT NOT NULL,
  due_date TEXT NOT NULL,
  paid_date TEXT,
  amount REAL NOT NULL,
  status TEXT NOT NULL,
  FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
);
"""

INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_sales_orders_date ON sales_orders(order_date);
CREATE INDEX IF NOT EXISTS idx_sales_orders_region ON sales_orders(region);
CREATE INDEX IF NOT EXISTS idx_sales_orders_customer ON sales_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status_priority ON support_tickets(status, priority);
CREATE INDEX IF NOT EXISTS idx_tickets_customer ON support_tickets(customer_id);
CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department);
CREATE INDEX IF NOT EXISTS idx_invoices_status_due ON invoices(status, due_date);
"""

BUSINESS_GLOSSARY = """
Business definitions:
- revenue = SUM(quantity * unit_price * (1 - discount_pct)) from sales_orders.
- average order value = revenue / COUNT(DISTINCT order_id).
- churn-risk ticket = support ticket where status is not 'closed' and
  (priority is 'high' or 'critical' or sentiment_score <= 2).
- attrition = employees where status = 'left'.
- overdue invoice = invoice where status = 'open' and due_date is before the
  analysis date.
- enterprise customers are customers where segment = 'enterprise'.
"""

SCHEMA_NOTES = """
Use only read-only SELECT queries. Prefer explicit columns and LIMIT for detail
questions. Dates are ISO strings. The seeded demo database mainly covers 2025
and Q1 2026.
"""


def schema_context() -> str:
    return "\n\n".join(
        [
            "SQLite schema:",
            DDL.strip(),
            BUSINESS_GLOSSARY.strip(),
            SCHEMA_NOTES.strip(),
        ]
    )
