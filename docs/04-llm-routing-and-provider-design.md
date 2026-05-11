# LLM Routing and Provider Design

## 1. Goal

Support many workflows and many steps where each may use different LLMs, provider accounts, and policies while preserving traceability and replayability.

## 2. Core Principle

Do not hard-code model choice in workflow logic.

Avoid patterns like:

- if workflow X then use model A
- if tenant Y then use model B
- if node Z then use model C

Instead, build a first-class routing and profile system.

## 3. Key Concepts

## 3.1 Provider

Represents a concrete external or internal model backend.

Examples:

- OpenAI
- Azure OpenAI
- Anthropic
- Gemini
- Qwen
- DeepSeek
- vLLM
- Ollama
- internal enterprise model gateway

## 3.2 Model Profile

Represents a reusable model capability profile.

Examples:

- `cheap_structured_cn`
- `advanced_reasoning_cn`
- `high_context_analyst_en`
- `timeline_writer_cn`

A profile should include:

- provider reference
- model name
- temperature
- max tokens
- top_p
- timeout
- structured output mode
- retry policy
- fallback chain
- cost ceiling or policy

## 3.3 Routing Policy

Determines which profile to use for which execution context.

Dimensions may include:

- workflow template
- node key
- tenant
- request priority
- language
- budget class
- input size

## 3.4 Invocation Snapshot

Every actual call should capture a full snapshot of what was used, not only a profile name.

This is required for replay and audit.

## 4. Routing Precedence

Recommended precedence from highest to lowest:

1. request-level override
2. workflow-template-level override
3. node-level default
4. system default

This supports:

- custom tenant requests
- workflow-specific tuning
- stable default behavior

## 5. Suggested LLM Step Categories

Different step types should use different profiles.

### 5.1 Structured Extraction Steps

Use:

- lower-cost
- schema-constrained
- high-precision output

Examples:

- entity extraction
- time extraction
- stance label extraction

### 5.2 Reasoning Steps

Use:

- better reasoning
- stronger consistency

Examples:

- conflict resolution
- evidence comparison
- risk analysis

### 5.3 Report Generation Steps

Use:

- stronger writing capability
- language-specific quality profile

Examples:

- final event summary
- public opinion report
- timeline narrative

## 6. Fallback Strategy

Fallback should be explicit and recorded.

Examples:

- primary provider timeout -> retry once -> switch provider
- structured output parse failure -> same provider repair pass
- context overflow -> switch to higher-context profile

Every fallback action should be recorded in invocation metadata.

## 7. Prompt Management

Prompts should be versioned resources, not inline code strings scattered across the codebase.

Prompt template should define:

- prompt name
- version
- purpose
- variable schema
- output schema
- target step category

The system should persist:

- prompt template ID
- prompt version
- rendered prompt hash

## 8. Invocation Record Requirements

Each LLM call should persist:

- provider
- model name
- profile ID
- profile snapshot
- prompt template ID
- prompt version
- rendered prompt hash
- input artifact references
- input token count
- output token count
- latency
- cost
- finish reason
- retry count
- fallback source

## 9. Provider Abstraction Boundary

Workflows should call an internal LLM service contract such as:

- `invoke_structured()`
- `invoke_reasoning()`
- `invoke_generation()`

The provider adapter should translate these into provider-specific requests.

This prevents workflow logic from depending on:

- provider SDK shape
- request formatting differences
- structured output implementation details

## 10. MCP Tool Integration

MCP should be treated as one tool integration protocol, not as the only extension path.

Suggested abstraction:

- `tool_registry`
- `tool_adapter`
- `tool_execution_service`

Supported tool types:

- internal native tools
- HTTP tools
- MCP tools
- SDK tools

Every tool call should be persisted similarly to provider calls.

## 11. Cost Governance

Different workflows should be able to express different cost policies.

Examples:

- cheap preprocessing
- premium final generation
- maximum cost per task
- maximum cost per tenant per day

Routing policy should be able to downgrade model choice when needed.

## 12. Example Node-to-Profile Mapping

Examples:

- `extract_entities` -> `cheap_structured_cn`
- `extract_timeline_events` -> `cheap_structured_cn`
- `risk_analysis` -> `advanced_reasoning_cn`
- `final_event_summary` -> `report_writer_cn`
- `foreign_source_summary` -> `report_writer_en`

This should remain configuration-driven.

## 13. Relationship Between Search Providers and LLM Providers

The project includes two different categories of external intelligence providers:

- standalone search and fetch providers
- model providers with embedded search tools

These should not be mixed into one abstraction.

Recommended rule:

- Exa, Tavily, Firecrawl, TinyFish act as retrieval providers under the search pipeline
- Grok search acts as a tool-enabled LLM execution mode under the LLM routing layer

This distinction matters because:

- standalone providers return retrieval records that should be normalized into `search_hit` and `document`
- model-embedded search returns answer-oriented outputs plus citations and should be recorded as `llm_invocation` plus linked evidence metadata

## 14. When to Use Model-Embedded Search

Model-embedded search should be used selectively.

Good cases:

- answer-with-citations nodes
- X platform retrieval via `x_search`
- synthesis nodes that benefit from search tightly coupled with reasoning

Not ideal as the default for:

- bulk evidence discovery
- reusable raw search artifact generation
- strict provider-agnostic retrieval pipelines

## 15. Citation Handling

When using search-enabled LLM invocations, citations should be persisted as structured evidence metadata.

Suggested citation record contents:

- citation index
- cited URL
- cited title when available
- cited provider
- cited snippet or anchor text when available
- referenced output section or paragraph

This allows downstream audit and UI display without relying only on plain generated text.
