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
    def __init__(self) -> None:
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
        return self._by_node_key.get(node_key, self._default)
