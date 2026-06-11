from __future__ import annotations


LMS_DDL = """
CREATE SCHEMA core;
CREATE SCHEMA lms;
CREATE SCHEMA billing;
CREATE SCHEMA support;
CREATE SCHEMA analytics;

CREATE TABLE core.organizations (
  organization_id INTEGER PRIMARY KEY,
  organization_name TEXT NOT NULL,
  plan_name TEXT NOT NULL,
  region TEXT NOT NULL,
  created_at DATE NOT NULL
);

CREATE TABLE core.users (
  user_id INTEGER PRIMARY KEY,
  organization_id INTEGER NOT NULL,
  full_name TEXT NOT NULL,
  email TEXT NOT NULL,
  role TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at DATE NOT NULL
);

CREATE TABLE lms.courses (
  course_id INTEGER PRIMARY KEY,
  organization_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  category TEXT NOT NULL,
  difficulty TEXT NOT NULL,
  published_at DATE NOT NULL
);

CREATE TABLE lms.enrollments (
  enrollment_id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  course_id INTEGER NOT NULL,
  enrolled_at DATE NOT NULL,
  completed_at DATE,
  status TEXT NOT NULL,
  progress_pct INTEGER NOT NULL
);

CREATE TABLE lms.lessons (
  lesson_id INTEGER PRIMARY KEY,
  course_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  duration_minutes INTEGER NOT NULL,
  sequence_no INTEGER NOT NULL
);

CREATE TABLE lms.assessments (
  assessment_id INTEGER PRIMARY KEY,
  enrollment_id INTEGER NOT NULL,
  assessment_type TEXT NOT NULL,
  score_pct REAL NOT NULL,
  attempted_at DATE NOT NULL
);

CREATE TABLE billing.invoices (
  invoice_id INTEGER PRIMARY KEY,
  organization_id INTEGER NOT NULL,
  invoice_date DATE NOT NULL,
  due_date DATE NOT NULL,
  paid_date DATE,
  amount_usd REAL NOT NULL,
  status TEXT NOT NULL
);

CREATE TABLE support.tickets (
  ticket_id INTEGER PRIMARY KEY,
  organization_id INTEGER NOT NULL,
  user_id INTEGER,
  opened_at DATE NOT NULL,
  priority TEXT NOT NULL,
  status TEXT NOT NULL,
  issue_type TEXT NOT NULL,
  sentiment_score INTEGER NOT NULL
);

CREATE TABLE analytics.events (
  event_id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  course_id INTEGER,
  event_name TEXT NOT NULL,
  event_at TIMESTAMP NOT NULL,
  device_type TEXT NOT NULL
);
"""

LMS_GLOSSARY = """
Business definitions:
- active learners are core.users where status = 'active' and role = 'learner'.
- completion rate = completed enrollments / total enrollments.
- overdue invoices are billing.invoices where status = 'open' and due_date is before the analysis date.
- at-risk learners have lms.enrollments.status != 'completed' and progress_pct < 35 after 14 days.
- churn-risk organizations have high or critical open support tickets, low sentiment, or overdue invoices.
- course engagement can be measured from analytics.events grouped by event_name, user_id, or course_id.
"""


def lms_schema_context() -> str:
    return "\n\n".join(
        [
            "Use DuckDB/PostgreSQL-style schema-qualified table names.",
            LMS_DDL.strip(),
            LMS_GLOSSARY.strip(),
            "Return exactly one read-only SELECT query.",
        ]
    )
