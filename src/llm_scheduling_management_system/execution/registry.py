from llm_scheduling_management_system.execution.executors import (
    BuildTimelineExecutor,
    ClassifyAndFilterSourcesExecutor,
    DefaultStepExecutor,
    ExtractOfficialResponsesExecutor,
    ExtractEventTimeExecutor,
    FetchDocumentsExecutor,
    MCPToolExecutor,
    LLMReportExecutor,
    MergeSearchResultsExecutor,
    NormalizeAndFilterExecutor,
    SegmentPublicOpinionExecutor,
    SearchFanoutExecutor,
    StepExecutor,
)


class ExecutorRegistry:
    """执行器注册表类。

    用途:
        用于根据工作流节点标识符（node_key）查找并获取对应的步骤执行器（StepExecutor）实例。

    用法:
        registry = ExecutorRegistry()
        executor = registry.get("search_fanout")

    @Author: mosliu
    """
    def __init__(self) -> None:
        """初始化执行器注册表。

        用途:
            实例化并映射所有支持的节点标识符到其对应的执行器实例，同时设置默认执行器。

        用法:
            实例化 ExecutorRegistry 时自动调用。

        @Author: mosliu
        """
        self._by_node_key: dict[str, StepExecutor] = {
            "search_fanout": SearchFanoutExecutor(),
            "fetch_documents": FetchDocumentsExecutor(),
            "mcp_lookup_context": MCPToolExecutor(),
            "merge_search_results": MergeSearchResultsExecutor(),
            "normalize_and_filter": NormalizeAndFilterExecutor(),
            "classify_and_filter_sources": ClassifyAndFilterSourcesExecutor(),
            "extract_official_responses": ExtractOfficialResponsesExecutor(),
            "segment_public_opinion": SegmentPublicOpinionExecutor(),
            "extract_event_time": ExtractEventTimeExecutor(),
            "build_timeline": BuildTimelineExecutor(),
            "generate_event_summary": LLMReportExecutor(),
            "analyze_public_opinion": LLMReportExecutor(),
            "generate_public_opinion_report": LLMReportExecutor(),
            "generate_timeline_report": LLMReportExecutor(),
        }
        self._default = DefaultStepExecutor()

    def get(self, node_key: str) -> StepExecutor:
        """根据节点标识符获取对应的步骤执行器。

        用途:
            通过节点标识符返回特定的执行器实例，如果标识符未注册，则返回默认的 DefaultStepExecutor。

        用法:
            executor = registry.get("search_fanout")

        @Author: mosliu
        """
        return self._by_node_key.get(node_key, self._default)
