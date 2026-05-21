from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from llm_scheduling_management_system.domain.enums import TaskStatus
from llm_scheduling_management_system.domain.models import TaskRun
from llm_scheduling_management_system.services.task_runner import TaskAlreadyCompletedError, TaskRunner


class GraphState(TypedDict):
    """LangGraph 运行状态的数据结构。

    用途:
        在 LangGraph 图的各节点执行流转期间传递执行状态（包括任务 ID 和当前步骤的索引）。

    用法:
        state: GraphState = {"task_id": "task_123", "step_index": 0}

    @Author: mosliu
    """
    task_id: str
    step_index: int


class LangGraphTaskRunner:
    """基于 LangGraph 调度执行任务的运行器。

    用途:
        通过构建 StateGraph，将任务中的待执行步骤动态组装为工作流图，驱动任务的串行或条件化步骤执行。

    用法:
        runner = LangGraphTaskRunner(task_runner)
        final_task = runner.run_task(task_run)

    @Author: mosliu
    """

    def __init__(self, task_runner: TaskRunner) -> None:
        """初始化 LangGraphTaskRunner 实例。

        用途:
            传入核心的任务执行器 TaskRunner，用于具体的步骤逻辑处理。

        用法:
            runner = LangGraphTaskRunner(task_runner)

        @Author: mosliu
        """
        self.task_runner = task_runner

    def run_task(self, task: TaskRun) -> TaskRun:
        """执行指定任务下的所有待处理步骤。

        用途:
            分析任务中状态为 pending/retrying 的步骤，通过 StateGraph 动态构建流转图并编译执行。返回最新状态的任务实例。

        用法:
            updated_task = runner.run_task(task)

        @Author: mosliu
        """
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
                """动态生成图节点函数包装器。

                用途:
                    为指定的步骤实例生成带有闭包状态的图节点函数。

                用法:
                    node_fn = make_node(step)

                @Author: mosliu
                """
                def _node(state: GraphState):
                    """图节点核心执行函数。

                    用途:
                        加载当前任务的最新的状态，调用 task_runner 执行具体步骤，并更新状态中的步骤索引。

                    用法:
                        next_state = _node(state)

                    @Author: mosliu
                    """
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
