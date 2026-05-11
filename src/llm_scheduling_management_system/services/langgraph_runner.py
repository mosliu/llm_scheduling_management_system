from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from llm_scheduling_management_system.domain.enums import TaskStatus
from llm_scheduling_management_system.domain.models import TaskRun
from llm_scheduling_management_system.services.task_runner import TaskAlreadyCompletedError, TaskRunner


class GraphState(TypedDict):
    task_id: str
    step_index: int


class LangGraphTaskRunner:
    def __init__(self, task_runner: TaskRunner) -> None:
        self.task_runner = task_runner

    def run_task(self, task: TaskRun) -> TaskRun:
        if task.status == TaskStatus.SUCCEEDED.value:
            raise TaskAlreadyCompletedError(task.id)

        pending_steps = [
            step
            for step in sorted(task.step_runs, key=lambda item: item.sequence_no)
            if step.status in {"pending", "retrying"}
        ]
        if pending_steps:
            self.task_runner.repository.mark_task_running(task, current_step_run_id=pending_steps[0].id)

        graph = StateGraph(GraphState)

        for index, step in enumerate(pending_steps):
            def make_node(local_step):
                def _node(state: GraphState):
                    current_task = self.task_runner.repository.get_task(state["task_id"])
                    if current_task is None:
                        return state
                    self.task_runner.run_specific_step(current_task, local_step)
                    return {"task_id": state["task_id"], "step_index": state["step_index"] + 1}
                return _node

            node_name = f"step_{index}"
            graph.add_node(node_name, make_node(step))
            if index == 0:
                graph.add_edge(START, node_name)
            else:
                graph.add_edge(f"step_{index - 1}", node_name)

        if pending_steps:
            graph.add_edge(f"step_{len(pending_steps) - 1}", END)
        else:
            graph.add_edge(START, END)

        app = graph.compile()
        app.invoke({"task_id": task.id, "step_index": 0})
        return self.task_runner.repository.get_task(task.id) or task
