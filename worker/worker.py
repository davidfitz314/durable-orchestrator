import os
import time
from datetime import datetime
from dotenv import load_dotenv

from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import JSONB

from app.db import SessionLocal
from app.models import RunStatus, WorkflowRun
from worker.backoff import next_run_time
from worker.executor import transform_step

load_dotenv()

WORKER_ID = os.getenv("WORKER_ID", "worker-1")
POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "1"))


# --- Claim runnable step safely (Postgres is our durable queue) ---
CLAIM_SQL = text("""
WITH cte AS (
  SELECT sr.id
  FROM step_runs sr
  JOIN workflow_runs wr ON wr.id = sr.workflow_run_id
  WHERE sr.status IN ('PENDING','WAITING_RETRY')
    AND sr.next_run_at <= now()
    AND wr.status NOT IN ('CANCELED','FAILED','SUCCEEDED')
  ORDER BY sr.next_run_at ASC, sr.id ASC
  FOR UPDATE SKIP LOCKED
  LIMIT 1
)
UPDATE step_runs
SET status = 'RUNNING',
    locked_at = now(),
    locked_by = :worker_id,
    updated_at = now()
WHERE id IN (SELECT id FROM cte)
RETURNING id, workflow_run_id, step_name, step_type, attempt_count, max_attempts, input_json;
""")

# --- Updates (bind JSONB so psycopg3 can adapt dicts) ---
SUCCESS_SQL = text("""
UPDATE step_runs
SET status='SUCCEEDED',
    output_json=:out,
    error_json=NULL,
    updated_at=now()
WHERE id=:id
""").bindparams(bindparam("out", type_=JSONB))

RETRY_SQL = text("""
UPDATE step_runs
SET status='WAITING_RETRY',
    attempt_count=attempt_count+1,
    next_run_at=:next_run_at,
    error_json=:err,
    updated_at=now()
WHERE id=:id
""").bindparams(bindparam("err", type_=JSONB))

FAIL_SQL = text("""
UPDATE step_runs
SET status='FAILED',
    attempt_count=attempt_count+1,
    error_json=:err,
    updated_at=now()
WHERE id=:id
""").bindparams(bindparam("err", type_=JSONB))


def set_run_running_if_needed(db: Session, run_id: int) -> None:
    run = db.get(WorkflowRun, run_id)
    if run and run.status == RunStatus.PENDING:
        run.status = RunStatus.RUNNING
        run.updated_at = datetime.utcnow()
        db.add(run)


def recompute_run_status(db: Session, run_id: int) -> None:
    rows = db.execute(
        text("""
            SELECT status, count(*)
            FROM step_runs
            WHERE workflow_run_id = :run_id
            GROUP BY status
        """),
        {"run_id": run_id},
    ).fetchall()

    counts = {status: count for (status, count) in rows}
    total = sum(counts.values())

    run = db.get(WorkflowRun, run_id)
    if not run:
        return

    if total == 0:
        # shouldn't happen, but keep deterministic
        run.status = RunStatus.FAILED
    elif counts.get("FAILED", 0) > 0:
        run.status = RunStatus.FAILED
    elif counts.get("CANCELED", 0) == total:
        run.status = RunStatus.CANCELED
    elif counts.get("SUCCEEDED", 0) == total:
        run.status = RunStatus.SUCCEEDED
    else:
        run.status = RunStatus.RUNNING

    run.updated_at = datetime.utcnow()
    db.add(run)


def main() -> None:
    print(f"[{WORKER_ID}] starting worker loop (poll={POLL_INTERVAL_SECONDS}s)")

    while True:
        # 1) Claim a runnable step (short transaction)
        db = SessionLocal()
        try:
            row = db.execute(CLAIM_SQL, {"worker_id": WORKER_ID}).mappings().first()
            if not row:
                db.commit()
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            step_id = int(row["id"])
            run_id = int(row["workflow_run_id"])
            step_name = row["step_name"]
            step_type = row["step_type"]
            attempt_count = int(row["attempt_count"])
            max_attempts = int(row["max_attempts"])
            input_json = row["input_json"] or {}

            set_run_running_if_needed(db, run_id)
            db.commit()

            print(f"[{WORKER_ID}] claimed step_id={step_id} run_id={run_id} step={step_name} type={step_type} attempt={attempt_count+1}/{max_attempts}")
        finally:
            db.close()

        # 2) Execute + persist result (separate transaction)
        db2 = SessionLocal()
        try:
            if step_type != "transform":
                raise RuntimeError(f"unsupported step_type: {step_type}")

            output = transform_step(step_name, input_json)

            db2.execute(SUCCESS_SQL, {"id": step_id, "out": output})
            db2.commit()
            print(f"[{WORKER_ID}] succeeded step_id={step_id} output={output}")

        except Exception as e:
            attempt_next = attempt_count + 1
            err_obj = {"message": str(e), "type": e.__class__.__name__}

            if attempt_next < max_attempts:
                nr = next_run_time(attempt_next)
                db2.execute(RETRY_SQL, {"id": step_id, "next_run_at": nr, "err": err_obj})
                db2.commit()
                print(f"[{WORKER_ID}] retrying step_id={step_id} next_run_at={nr.isoformat()} err={err_obj}")
            else:
                db2.execute(FAIL_SQL, {"id": step_id, "err": err_obj})
                db2.commit()
                print(f"[{WORKER_ID}] failed step_id={step_id} err={err_obj}")

        finally:
            db2.close()

        # 3) Update workflow run status (separate transaction)
        db3 = SessionLocal()
        try:
            recompute_run_status(db3, run_id)
            db3.commit()
        finally:
            db3.close()


if __name__ == "__main__":
    main()