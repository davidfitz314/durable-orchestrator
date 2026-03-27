## Durable Workflow Orchestrator

A minimal durable workflow execution engine built with FastAPI and PostgreSQL, demonstrating distributed worker coordination, persistent workflow state, and retry-based task execution.

Supports **parallel execution across multiple workers using PostgreSQL row-level locking (`SKIP LOCKED`)**.

This project explores backend orchestration patterns used in systems like Temporal, Airflow, Prefect, and Netflix Conductor, focusing on deterministic execution, failure recovery, and safe concurrent workers.

---

## Architecture Overview

The system separates orchestration into two components:

```
           ┌───────────────────────┐
           │      FastAPI API      │
           │                       │
           │  Create workflows     │
           │  Start workflow runs  │
           │  Inspect run status   │
           └─────────────┬─────────┘
                         │
                         ▼
              ┌───────────────────┐
              │     PostgreSQL     │
              │  Durable State     │
              │                   │
              │ workflow_runs     │
              │ step_runs         │
              │ definitions       │
              └─────────┬─────────┘
                        │
                        ▼
               ┌──────────────────┐
               │ Worker Processes │
               │                  │
               │ Claim runnable   │
               │ steps safely     │
               │ Execute tasks    │
               │ Persist results  │
               └──────────────────┘
```

PostgreSQL acts as a durable execution log and task queue, allowing workers to recover and resume execution even after failures.

---

## Key Features

### Durable Workflow State

Workflow definitions, runs, and step executions are persisted in PostgreSQL, allowing workflows to survive crashes or restarts.

---

### Safe Distributed Workers

Workers claim runnable steps using PostgreSQL row-level locking:

```sql
SELECT ... FOR UPDATE SKIP LOCKED
```

This ensures that multiple workers can run concurrently without executing the same step twice.

It also enables **horizontal scaling**, where additional worker processes can be added to increase throughput without coordination conflicts.

---

### Retry with Backoff

Failed steps are retried automatically with exponential backoff scheduling using the `next_run_at` field.

---

### Idempotent Execution Model

Step execution state is persisted so retries and restarts do not duplicate completed work.

---

### Horizontal Worker Scaling

Multiple worker processes can run simultaneously and safely coordinate work through the database.

---

## Parallel Execution Demo

This project supports **true parallel execution across multiple worker processes**.

When a workflow contains multiple independent steps, workers can claim and execute them concurrently using database coordination.

### Example Workflow

```json
{
  "steps": [
    {"name": "slow_add"},
    {"name": "slow_add"},
    {"name": "slow_add"},
    {"name": "slow_add"}
  ]
}
```

### Example Worker Output

```
[worker-1] claimed step_id=8 step=slow_add
[worker-2] claimed step_id=9 step=slow_add

[worker-1] succeeded step_id=8 output={'x': 2}
[worker-2] succeeded step_id=9 output={'x': 2}

[worker-1] claimed step_id=10 step=slow_add
[worker-2] claimed step_id=11 step=slow_add
```

### What This Demonstrates

* Multiple workers executing steps **at the same time**
* Safe work distribution via database locking
* No duplicate execution
* Horizontal scalability by adding workers

---

## Tech Stack

* Python 3.11
* FastAPI – API layer
* PostgreSQL – durable workflow state
* SQLAlchemy – ORM and query layer
* Alembic – database migrations
* Docker – local database environment

---

## Project Structure

```
durable-orchestrator/

app/
  main.py
  db.py
  models.py
  schemas.py
  api/
    definitions.py
    runs.py

worker/
  worker.py
  executor.py
  backoff.py

migrations/
docker-compose.yml
.env
README.md
```

---

## Data Model

### workflow_definitions

Stores workflow templates.

```
id
name
version
definition_json
created_at
```

---

### workflow_runs

Represents a single execution of a workflow.

```
id
workflow_definition_id
status
input_json
created_at
updated_at
```

---

### step_runs

Tracks execution of individual workflow steps.

```
id
workflow_run_id
step_name
step_type
status
attempt_count
max_attempts
next_run_at
output_json
error_json
locked_by
locked_at
```

---

## Execution Model

1. A workflow definition is created via the API
2. A workflow run is started
3. Step runs are created with status `PENDING`
4. Worker processes continuously poll for runnable steps
5. Workers claim a step using row-level locking
6. Step logic executes
7. Results are persisted
8. Workflow status is recomputed

---

## Example Workflow

```json
{
  "steps": [
    {"name": "fail_twice_then_succeed", "type": "transform", "max_attempts": 5},
    {"name": "add_one", "type": "transform", "max_attempts": 3}
  ]
}
```

Example execution:

```
Input:  x = 41

Step 1: fail_twice_then_succeed
Retry logic triggers

Step 2: add_one
Output: x = 42
```

---

## Running the Project

### 1. Start PostgreSQL

```bash
docker compose up -d
```

---

### 2. Run the API

```bash
uvicorn app.main:app --reload
```

API runs at:

```
http://localhost:8000
```

---

### 3. Run Worker

```bash
python -m worker.worker
```

Workers poll the database for runnable steps and execute them.

Multiple workers can run simultaneously.

---

## Example API Usage

Create workflow definition:

```
POST /definitions
```

Start workflow run:

```
POST /runs
```

Inspect workflow status:

```
GET /runs/{run_id}
```

---

## Observing Execution

Workflow state can be inspected directly in PostgreSQL:

```sql
SELECT * FROM workflow_runs;
SELECT * FROM step_runs;
```

The `locked_by` column indicates which worker claimed the step.

---

## Learning Goals

This project explores core concepts behind distributed workflow engines:

* Durable state machines
* Database-backed task queues
* Worker coordination via row-level locks
* Retry scheduling and failure handling
* Deterministic execution modeling

These patterns are foundational to modern orchestration systems such as Temporal, Airflow, and Prefect.

---

## Future Improvements

Planned enhancements:

* DAG-based workflows
* Step dependency resolution
* Human approval steps
* Event-driven worker wakeups
* Async execution pools
* Observability and metrics

---

## Author

David Chen-Fitzgerald ©2026
Software Engineer focused on distributed systems and AI infrastructure.

---
