from datetime import datetime, timedelta

def compute_backoff_seconds(attempt: int) -> int:
    # attempt starts at 1
    # 1 -> 2s, 2 -> 4s, 3 -> 8s ...
    return min(60, 2 ** attempt)

def next_run_time(attempt: int) -> datetime:
    return datetime.utcnow() + timedelta(seconds=compute_backoff_seconds(attempt))