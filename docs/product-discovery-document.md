# DataTalk Product Discovery Document

## 1. Title

**DataTalk: Schema-Aware Natural-Language Data Copilot for Business Teams**

DataTalk helps non-technical and semi-technical business users ask questions over company data using natural language, inspect the schema visually, verify generated SQL, and trust answers through visible source rows.

## 2. User Personas

### Persona 1: Riya Shah

| Field | Detail |
|---|---|
| Name | Riya Shah |
| Occupation | Product Manager |
| Age | 32 |
| Experience | 7 years in B2B SaaS product management and analytics workflows |
| Behaviour | Asks cross-functional questions across product, sales, customer support, billing, and risk data. Uses dashboards first, then asks analysts when the dashboard does not answer follow-up questions. Prefers fast experiments, clear evidence, and reusable insights. |
| Pain points | Does not always know table names or relationships. Waits on analysts for ad hoc SQL. Loses time validating whether an answer came from the correct dataset. Needs quick follow-up questions during planning and review meetings. |

### Persona 2: Arjun Mehta

| Field | Detail |
|---|---|
| Name | Arjun Mehta |
| Occupation | Risk Team Analyst |
| Age | 35 |
| Experience | 9 years in operational risk, audit reporting, compliance checks, and exception analysis |
| Behaviour | Reviews suspicious accounts, overdue invoices, open tickets, churn signals, and customer risk patterns. Works carefully and validates every number before sharing it. Uses structured reports but often needs deeper drilldowns. |
| Pain points | Manual data checks are slow. Risk questions usually need joins across customers, invoices, tickets, and orders. Generic AI tools can hallucinate SQL. Audit work requires traceable source rows, not only summarized answers. |

### Persona 3: Neha Kapoor

| Field | Detail |
|---|---|
| Name | Neha Kapoor |
| Occupation | Sales Team Lead |
| Age | 29 |
| Experience | 6 years in enterprise sales, customer growth, and revenue operations |
| Behaviour | Looks for high-value customers, regional performance, product revenue, overdue invoices, and account health. Needs quick answers before pipeline reviews and customer calls. Prefers simple language and visual output over raw SQL. |
| Pain points | Depends on RevOps or analysts for custom customer lists. Dashboard filters do not cover every selling question. Cannot easily connect revenue, support, and billing signals. Needs confidence that a generated list is current and accurate. |

## 3. Selected Person

**Selected person: Riya Shah, Product Manager**

### Why?

Riya is the strongest starting persona because Product Managers sit between product, sales, support, billing, and leadership. Their questions naturally span the same tables DataTalk supports: customers, products, sales orders, support tickets, invoices, and employees.

This persona also exposes the most important product risks early:

| Reason | Why It Matters |
|---|---|
| Cross-functional data needs | Product Managers ask questions across multiple teams, so schema awareness and table relationships become essential. |
| High follow-up frequency | PMs rarely stop at one query. They ask follow-up questions during planning, review, and prioritization. |
| Trust requirement | PM decisions affect roadmap and customer commitments, so answers must show SQL, source rows, and confidence. |
| Clear demo value | A PM can easily understand the benefit of natural-language query, visual schema, and grounded results in one workflow. |

## 4. Journey Map

| Journey Stage | Actions | Emotion With Emoji | Pain Points | Opportunities |
|---|---|---|---|---|
| 1. Frame business question | Riya asks, "Which South region customers have open issues and revenue impact?" | Curious 🙂 | Question is clear in business language but not in SQL. | Let the user start from natural language without knowing schema names. |
| 2. Check schema and data | Opens schema view to understand available tables, fields, and relationships. | Confused 😕 | Table relationships and foreign keys are hard to remember. | Show a visual HLD schema map with clickable table data. |
| 3. Ask natural-language query | Types the question in the chat interface and submits it. | Hopeful 🙂 | Generic AI may misunderstand intent or invent unavailable columns. | Use schema-aware query compilation with supported query families. |
| 4. Wait for processing | Watches the app process the query, generate SQL, and prepare rows. | Impatient 😣 | Waiting without feedback feels broken and reduces confidence. | Show a clear processing state before SQL and results appear. |
| 5. Review SQL and results | Reads the compiled SQL, answer summary, confidence, and source rows. | Cautious 🤔 | A result without evidence cannot be trusted in business meetings. | Display generated SQL, route, confidence, latency, and visible source rows. |
| 6. Validate the answer | Compares result rows with schema view and sample data. | Confident 🙂 | Switching between tools makes validation slower. | Keep schema, data, and chat in one workspace. |
| 7. Ask follow-up question | Modifies the question to filter by region, product, status, or period. | Motivated 🚀 | Small wording changes can fail if the parser is too rigid. | Improve query coverage and preserve chat context within the current session. |

## 5. Pain Points

| ID | Pain Point | Description |
|---|---|---|
| P1 | Schema uncertainty | Users do not know exact table names, column names, or table relationships. |
| P2 | Slow follow-up iteration | Users need many variations of a question, but each manual SQL request takes time. |
| P3 | Analyst dependency | Business users depend on analysts for ad hoc queries and joined datasets. |
| P4 | Low trust in generated answers | Users need proof through SQL, source rows, and visible data lineage. |
| P5 | Context switching | Users move between dashboards, spreadsheets, SQL tools, and chat tools. |
| P6 | Unsafe or hallucinated SQL | Generic language models can produce invalid columns, wrong joins, or unsupported queries. |
| P7 | Poor query reuse | Good ad hoc questions are often lost after a meeting or one-time analysis. |

## 6. Pain Point Time vs Effort Scoring Matrix

Scoring method:

- There are **7 pain points**, so each score uses **1 to 7 points**.
- **User Impact:** 7 = highest impact, 1 = lowest impact.
- **Time Lost:** 7 = most time lost, 1 = least time lost.
- **Effort Feasibility:** 7 = easiest to solve, 1 = hardest to solve.
- **Total Score = User Impact + Time Lost + Effort Feasibility**.
- Highest total score is prioritized first.

| Rank | Pain Point | User Impact (1-7) | Time Lost (1-7) | Effort Feasibility (1-7) | Total Score | Decision |
|---:|---|---:|---:|---:|---:|---|
| 1 | P2 - Slow follow-up iteration | 7 | 7 | 5 | 19 | Select |
| 2 | P4 - Low trust in generated answers | 6 | 6 | 6 | 18 | Select |
| 3 | P1 - Schema uncertainty | 5 | 5 | 7 | 17 | Select |
| 4 | P3 - Analyst dependency | 7 | 7 | 2 | 16 | Later |
| 5 | P6 - Unsafe or hallucinated SQL | 6 | 5 | 4 | 15 | Later |
| 6 | P5 - Context switching | 4 | 4 | 3 | 11 | Later |
| 7 | P7 - Poor query reuse | 3 | 3 | 4 | 10 | Later |

**Selected pain points:** P2, P4, and P1.

These pain points are selected because they combine strong user impact, high time loss, and practical implementation feasibility in the current DataTalk product.

## 7. Solution Ideas

### 3 OK Ideas

| Idea | Description | Limitation |
|---|---|---|
| Static data dictionary | Publish table names, fields, and example questions in a documentation page. | Helps understanding but does not answer questions directly. |
| Prebuilt dashboard templates | Build fixed charts for common sales, support, and billing questions. | Useful for repeated reporting, weak for ad hoc questions. |
| Analyst request form | Let users submit structured data requests to analysts. | Organizes requests but still creates waiting time and dependency. |

### 3 Best Ideas

| Idea | Description | Benefit |
|---|---|---|
| Schema-aware chat-to-SQL assistant | Convert natural language into safe SQL using known schema and allowed query families. | Reduces follow-up time and analyst dependency. |
| Visual schema explorer with source rows | Show HLD table relationships, clickable tables, and sample rows. | Reduces schema uncertainty and improves self-service validation. |
| Verified answer panel | Show answer summary, compiled SQL, confidence, route, latency, and source rows. | Builds trust and makes AI output reviewable. |

### 3 Moonshot Ideas

| Idea | Description | Expected Advantage |
|---|---|---|
| DataTalk-SLM | Train a company-specific small language model for schema-grounded business querying. | Faster, cheaper, and more controlled than relying only on a large generic model. |
| Governed multi-system enterprise copilot | Connect CRM, billing, support, product analytics, and warehouse data with permission-aware answers. | Turns DataTalk into an enterprise-wide decision assistant. |
| Autonomous business insight agent | Proactively detects anomalies, risks, churn signals, and revenue opportunities without waiting for prompts. | Moves from query answering to automatic business intelligence. |

## 8. Moonshot Time vs Effort Scoring Matrix

Scoring method:

- There are **3 moonshot ideas**, so each score uses **1 to 3 points**.
- **User Value:** 3 = highest value, 1 = lowest value.
- **Time To Value:** 3 = fastest to validate, 1 = slowest to validate.
- **Effort Feasibility:** 3 = easiest to build, 1 = hardest to build.
- **Total Score = User Value + Time To Value + Effort Feasibility**.
- Highest total score is selected.

| Rank | Moonshot Idea | User Value (1-3) | Time To Value (1-3) | Effort Feasibility (1-3) | Total Score | Decision |
|---:|---|---:|---:|---:|---:|---|
| 1 | DataTalk-SLM | 3 | 2 | 2 | 7 | Selected |
| 2 | Governed multi-system enterprise copilot | 3 | 1 | 1 | 5 | Next |
| 3 | Autonomous business insight agent | 2 | 1 | 1 | 4 | Later |

## 9. Selected Idea

**Selected idea: DataTalk-SLM, a schema-aware small language model with deterministic SQL validation and source-row verification.**

DataTalk-SLM is selected because it directly addresses the top-ranked pain points:

| Selected Pain Point | How DataTalk-SLM Solves It |
|---|---|
| P2 - Slow follow-up iteration | Users can ask and refine questions in chat without waiting for manual SQL support. |
| P4 - Low trust in generated answers | The product shows compiled SQL, confidence, route, latency, and source rows. |
| P1 - Schema uncertainty | The model and UI are grounded in known tables, columns, relationships, and supported query families. |

The selected solution is practical because the current DataTalk implementation already includes:

- A visual schema and data page.
- A chat-style natural-language query interface.
- Static compiler mode for safe demo queries.
- SQL display and source-row verification.
- Public GitHub Pages deployment without browser-side secrets.
- A path to connect a trained SLM model API later without exposing train, validation, or test data.

## 10. Final Product Statement

DataTalk is a schema-aware data copilot that helps business teams move from natural-language questions to verified SQL-backed answers. The selected product direction is to evolve the current demo into DataTalk-SLM: a company-specific small language model trained for fast, grounded, and trustworthy business querying.
