import argparse

from llm_scheduling_management_system.bootstrap import ensure_local_database
from llm_scheduling_management_system.db import SessionLocal
from llm_scheduling_management_system.services.task_worker import TaskWorker


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["once", "until-idle", "loop"], default="loop")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    args = parser.parse_args()

    ensure_local_database()
    session = SessionLocal()
    try:
        worker = TaskWorker(session)
        if args.mode == "once":
            worker.process_once()
        elif args.mode == "until-idle":
            worker.process_until_idle()
        else:
            worker.run_loop(poll_interval_seconds=args.poll_interval)
    finally:
        session.close()
