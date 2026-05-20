from __future__ import annotations

import argparse
import time

from loguru import logger
from sqlalchemy.exc import OperationalError

from llm_scheduling_management_system.bootstrap import ensure_local_database
from llm_scheduling_management_system.db import SessionLocal
from llm_scheduling_management_system.logging import configure_logging
from llm_scheduling_management_system.services.task_worker import TaskWorker


def process_once(limit: int) -> int:
    session = SessionLocal()
    try:
        worker = TaskWorker(session)
        return worker.process_once(limit=limit)
    finally:
        session.close()


def process_until_idle(limit: int) -> int:
    total_processed = 0
    while True:
        processed = process_once(limit=limit)
        total_processed += processed
        if processed == 0:
            break
    logger.info("Worker service reached idle state after processing {} step(s)", total_processed)
    return total_processed


def run_loop(limit: int, poll_interval_seconds: float) -> None:
    logger.info(
        "Starting worker service loop with limit {} and poll interval {}s",
        limit,
        poll_interval_seconds,
    )
    while True:
        try:
            processed = process_once(limit=limit)
        except OperationalError as exc:
            logger.warning("Worker service hit OperationalError, sleeping before retry: {}", exc)
            time.sleep(poll_interval_seconds)
            continue
        except Exception:
            logger.exception("Worker service loop crashed, sleeping before retry.")
            time.sleep(poll_interval_seconds)
            continue

        if processed == 0:
            time.sleep(poll_interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["once", "until-idle", "loop"], default="loop")
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    configure_logging()
    ensure_local_database()

    if args.mode == "once":
        process_once(limit=args.limit)
        return
    if args.mode == "until-idle":
        process_until_idle(limit=args.limit)
        return
    run_loop(limit=args.limit, poll_interval_seconds=args.poll_interval)


if __name__ == "__main__":
    main()
