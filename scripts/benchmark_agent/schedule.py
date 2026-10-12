"""Bound independent case concurrency without queuing an unbounded paid workload."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait


def run_jobs(jobs, call, workers=1):
    if workers == 1:
        for job in jobs:
            call(job)
        return
    if workers != 2:
        raise ValueError('Use one or two independent case workers')
    jobs = iter(jobs)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = set()
        try:
            for _ in range(workers):
                job = next(jobs, None)
                if job is not None:
                    pending.add(pool.submit(call, job))
            while pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    future.result()
                for _ in done:
                    job = next(jobs, None)
                    if job is not None:
                        pending.add(pool.submit(call, job))
        finally:
            for future in pending:
                future.cancel()
