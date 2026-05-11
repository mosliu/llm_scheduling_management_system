from llm_scheduling_management_system.schemas.tasks import CreateTaskRequest
from llm_scheduling_management_system.services.task_service import TaskService
from llm_scheduling_management_system.services.task_worker import TaskWorker


def test_task_worker_process_once_advances_a_queued_task(session):
    service = TaskService(session)
    task = service.create_task(
        CreateTaskRequest(
            template_id="event_summary_v1",
            input={"topic": "worker task"},
            options={},
        )
    )

    worker = TaskWorker(session)
    processed = worker.process_once(limit=10)
    updated = service.get_task(task.id)

    assert processed == 1
    assert updated is not None
    assert updated.status == "running"
    assert updated.completed_step_count == 2


def test_task_worker_skips_cancelled_tasks(session):
    service = TaskService(session)
    task = service.create_task(
        CreateTaskRequest(
            template_id="event_summary_v1",
            input={"topic": "cancelled worker task"},
            options={},
        )
    )
    service.cancel_task(task.id)

    worker = TaskWorker(session)
    processed = worker.process_once(limit=10)
    updated = service.get_task(task.id)

    assert processed == 0
    assert updated is not None
    assert updated.status == "cancelled"


def test_task_worker_process_until_idle_completes_task(session):
    service = TaskService(session)
    task = service.create_task(
        CreateTaskRequest(
            template_id="event_summary_v1",
            input={"topic": "idle worker task"},
            options={},
        )
    )

    worker = TaskWorker(session)
    processed = worker.process_until_idle(limit=10)
    updated = service.get_task(task.id)

    assert processed >= 4
    assert updated is not None
    assert updated.status == "succeeded"
