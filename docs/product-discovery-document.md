# DataTalk Product Discovery Document

## 1. Title

**DataTalk: Schema-Aware Natural-Language Data Copilot for Business Teams**

DataTalk helps non-technical and semi-technical teams ask questions over
enterprise data, inspect the generated SQL, and verify answers through visible
source rows. The product direction combines a visual schema explorer, a
chat-style query interface, deterministic SQL validation, and a future
schema-specialized small language model.

## 2. User Personas

### Persona 1: Product Manager

**Profile:** A product manager working in an IT or SaaS company who needs fast
answers from customer, product, support, billing, and usage data.

**Goals:**

- Understand feature adoption, revenue movement, churn signals, and support
  pressure without waiting for analysts.
- Prepare product reviews, roadmap decisions, and leadership updates.
- Connect customer feedback, sales movement, product usage, and support tickets.

**Current behavior:**

- Asks data analysts or engineers for SQL extracts.
- Checks dashboards that often do not answer the exact question.
- Copies numbers from multiple tools into product docs or slides.

**Success criteria:**

- Can ask a question in natural language and get verified SQL-backed results.
- Can inspect which tables and rows produced the answer.
- Can reuse the result in product planning or stakeholder discussions.

### Persona 2: Risk Team Analyst

**Profile:** A risk or compliance team member who monitors business exposure,
operational risk, delayed payments, suspicious patterns, and policy exceptions.

**Goals:**

- Identify risk signals quickly across customers, invoices, support tickets, and
  usage events.
- Validate answers before escalation.
- Maintain auditability and avoid unsafe write operations.

**Current behavior:**

- Depends on scheduled reports or spreadsheet exports.
- Requests custom SQL when a new risk question appears.
- Cross-checks multiple systems manually before raising a case.

**Success criteria:**

- Can ask read-only risk questions safely.
- Can see SQL, source rows, and table lineage.
- Can trust that the system does not expose secrets or modify data.

### Persona 3: Sales Team Lead

**Profile:** A sales manager or revenue operations user who needs quick insight
into customers, product revenue, open invoices, deal health, and account risk.

**Goals:**

- Find top customers, revenue by region, product performance, and overdue
  invoices.
- Prepare account reviews without waiting for data exports.
- Spot churn risk before renewal or expansion conversations.

**Current behavior:**

- Uses CRM dashboards but lacks deeper joined data.
- Asks finance, product, or support for additional context.
- Builds manual spreadsheet summaries for weekly reviews.

**Success criteria:**

- Can ask revenue and account questions directly.
- Can verify the answer with rows and SQL.
- Can move faster in sales reviews and customer planning.

## 3. Selected Persona

**Selected persona: Product Manager**

### Justification

The product manager is the best primary persona because this role sits between
engineering, sales, support, finance, and leadership. Product managers ask broad
cross-functional questions that require joined context across multiple tables:
customers, products, revenue, support tickets, invoices, and usage events. This
matches DataTalk's strongest value proposition: turning schema-aware business
questions into safe SQL-backed answers with visible evidence.

The product manager also benefits from every major product capability:

- Schema view to understand what data exists.
- Chat query interface to ask ad hoc questions.
- SQL preview to trust the generated result.
- Source rows to defend decisions in reviews.
- Future SLM path to reduce context size and improve query speed.

## 4. Journey Map With Pain Points

| Journey Stage | User Action | Current Experience | Pain Point |
|---|---|---|---|
| 1. Define question | PM frames a product or business question | Question is often vague or crosses multiple data domains | Unsure which tables or metrics are available |
| 2. Find data source | PM checks dashboards, CRM, support tools, or asks analyst | Data is fragmented across tools | Too much time spent locating trusted data |
| 3. Request query | PM asks analyst or engineer for custom SQL | Request enters backlog or Slack thread | Slow turnaround for simple questions |
| 4. Interpret result | PM receives table, chart, or spreadsheet | Query logic is often hidden | Low confidence in result correctness |
| 5. Validate answer | PM asks follow-up questions or checks raw rows | Verification requires another request | Hard to trace answer back to source rows |
| 6. Share decision | PM prepares roadmap, review, or stakeholder summary | Numbers are manually copied into docs | Risk of stale or inconsistent data |
| 7. Ask follow-up | PM changes filter, time period, or metric | New question restarts the cycle | Iteration is slow and dependency-heavy |

## 5. Pain Points

1. **Data dependency:** Product managers depend on analysts or engineers for
   custom questions.
2. **Schema uncertainty:** Users do not know which tables, columns, or
   relationships are available.
3. **Slow iteration:** Follow-up questions take too long because every change
   may need a new SQL request.
4. **Low trust:** Dashboards show answers but not the SQL or source rows behind
   the answer.
5. **Context switching:** Users move between dashboards, spreadsheets, Slack,
   CRM, support tools, and docs.
6. **Unsafe generic AI risk:** Generic LLM answers can hallucinate schema,
   invent metrics, or produce unsafe SQL.
7. **Poor reuse:** Good queries are not stored as reusable business patterns.

## 6. Pain Point Prioritization: Time vs Effort Matrix

| Priority | Pain Point | User Time Lost | Effort To Solve | Reason |
|---|---|---:|---:|---|
| P1 | Slow iteration on follow-up questions | High | Medium | Directly blocks daily PM work and can be improved with chat + compiler |
| P1 | Low trust in generated or dashboard answers | High | Medium | SQL preview and source rows create immediate confidence |
| P1 | Schema uncertainty | Medium | Low | Visual schema explorer and sample rows are feasible and high value |
| P2 | Data dependency on analysts | High | High | Requires broader query coverage and governance |
| P2 | Generic AI hallucination risk | High | High | Needs SQL guard, schema grounding, and evaluation |
| P3 | Context switching across tools | Medium | High | Requires integrations beyond the demo scope |
| P3 | Poor query reuse | Medium | Medium | Needs saved queries, team workspaces, and permissions |

### Matrix Interpretation

| Effort / Time Lost | Low Time Lost | Medium Time Lost | High Time Lost |
|---|---|---|---|
| Low Effort | Improve labels and examples | Visual schema explorer | Schema search and glossary |
| Medium Effort | Saved prompt examples | Query history and source rows | Chat-based SQL compiler |
| High Effort | Team query library | Tool integrations | Full governed SLM data copilot |

## 7. Solution Ideas

### 3 OK Ideas

1. **Static data dictionary**
   - A searchable page showing tables, columns, and definitions.
   - Useful but does not answer questions directly.

2. **Prebuilt dashboard templates**
   - Fixed dashboards for revenue, customers, tickets, invoices, and products.
   - Fast for known questions but weak for ad hoc exploration.

3. **Analyst request form**
   - Structured form for PMs to request SQL or reports.
   - Improves intake but still keeps users dependent on analysts.

### 3 Best Ideas

1. **Schema-aware chat-to-SQL assistant**
   - User asks a business question.
   - System compiles SQL, validates it, and returns rows with explanation.

2. **Visual schema explorer with sample rows**
   - Users inspect tables and relationships before asking questions.
   - Improves trust and reduces schema confusion.

3. **Verified answer view**
   - Every answer includes SQL, source rows, lineage, and confidence.
   - Reduces hallucination risk and supports stakeholder communication.

### 3 Moonshot Ideas

1. **DataTalk-SLM: company-specific small language model**
   - Fine-tune a compact model on schema, glossary, and question-to-SQL
     examples.
   - Goal: faster inference, smaller context, and better domain alignment.

2. **Autonomous business insight agent**
   - Monitors data changes and proactively suggests product, risk, and sales
     insights.
   - Example: "Support tickets for Product A increased after the latest release."

3. **Governed multi-system enterprise copilot**
   - Connects CRM, support, billing, analytics, and warehouse data with access
     control, audit logs, and approved query policies.
   - Designed for production enterprise usage.

## 8. Moonshot Prioritization: Time vs Effort

| Moonshot Idea | Time To Value | Build Effort | Risk | Priority |
|---|---:|---:|---:|---|
| DataTalk-SLM company-specific model | Medium | High | Medium | 1 |
| Governed multi-system enterprise copilot | Long | Very High | High | 2 |
| Autonomous business insight agent | Long | Very High | Very High | 3 |

### Moonshot Matrix

| Effort / Time To Value | Short Time | Medium Time | Long Time |
|---|---|---|---|
| Medium Effort | Not applicable | Expand deterministic compiler | Not applicable |
| High Effort | Not applicable | **DataTalk-SLM** | Governed enterprise copilot |
| Very High Effort | Not applicable | Not applicable | Autonomous insight agent |

## 9. Selected Idea

**Selected idea: DataTalk-SLM, a schema-aware small language model with SQL
validation and source-row verification.**

### Why This Idea Is Selected

DataTalk-SLM is the right selected idea because it balances ambition with a
realistic product path. It keeps the current reliable compiler and SQL guard,
then adds a specialized model that can learn schema vocabulary, business terms,
and common question-to-SQL patterns. This direction supports the selected
persona, the product manager, because it helps them ask faster cross-functional
questions without losing trust or explainability.

### Selected Solution Scope

- Visual schema explorer for table and relationship understanding.
- Chat interface for natural-language questions.
- Static compiler for high-confidence supported query families.
- SQL guard for read-only validation.
- Source rows and SQL preview for verification.
- Browser chat history for one active conversation.
- Future SLM fine-tuning path for faster schema-aware query generation.

### Success Metrics

| Metric | Target |
|---|---|
| Time to first answer | Under 5 seconds for supported demo queries |
| Query explainability | 100% of answers show SQL and source rows |
| Supported query coverage | Revenue, customers, products, tickets, invoices, employees, and LMS examples |
| Safety | Only read-only SQL is allowed |
| User confidence | Users can verify table lineage and row-level evidence |

## 10. Final Product Statement

DataTalk will help product managers and business teams ask questions over
company data using natural language, inspect exactly how answers were produced,
and make faster decisions without waiting for every SQL request. The selected
direction is a schema-aware SLM data copilot with deterministic safety checks,
visible source rows, and a product-grade UI for schema exploration and chat.
