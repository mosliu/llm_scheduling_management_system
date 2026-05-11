# Project Engineering Conventions

This project should be advanced with an engineering-first mindset.

The goal is not only to produce code that works, but to build a workflow platform that is traceable, maintainable, auditable, and easy to evolve.

## 1. Working Principles

### 1.1 Engineering First

All implementation work should follow engineering discipline:

- define scope before coding
- keep changes incremental
- preserve execution evidence
- prefer explicit contracts over implicit behavior
- treat documentation, configuration, and observability as part of the product

### 1.2 Record Every Meaningful Step

Every meaningful project step should leave usable records.

This includes:

- architecture decisions
- workflow design updates
- data model changes
- API contract changes
- provider integration decisions
- prompt or model routing changes
- task execution and validation results
- unresolved issues and follow-up actions

The project should avoid silent changes with no context trail.

### 1.3 Reproducibility

Any team member should be able to understand:

- why a change was made
- what assumptions it depends on
- how to rerun or verify it
- which configuration it needs

## 2. Repository Management

### 2.1 Version Control

This project should be managed with `git`.

Rules:

- commit small, coherent changes
- keep commit scopes focused
- do not mix unrelated work in one commit
- document meaningful architectural decisions in docs
- never commit secrets or local-only configuration

### 2.2 Python Tooling

This project should use `uv` for Python environment and dependency management.

Recommended commands:

- `uv sync`
- `uv run ...`
- `uv add ...`

Avoid introducing multiple competing environment management approaches.

## 3. Configuration Management

### 3.1 Separate Config from Code

External system configuration must live in dedicated config files rather than being embedded in code.

This includes:

- LLM provider configuration
- search provider configuration
- MCP server configuration
- database and cache configuration
- object storage configuration
- observability configuration

### 3.2 Example Config Files

Every required local config file should have a checked-in example file.

Examples:

- `config/app.example.toml`
- `config/llm.example.toml`
- `config/search.example.toml`
- `config/mcp.example.toml`

### 3.3 Ignore Real Config Files

Real local config files must be added to `.gitignore`.

Only example templates should be committed.

## 4. Documentation Rules

### 4.1 Docs Are Part of Delivery

Important design work must be reflected in `docs/`.

At minimum, keep these current:

- architecture overview
- workflow execution model
- data model
- API contracts
- configuration conventions
- implementation roadmap

### 4.2 Decision Recording

When a technical direction changes, record:

- decision summary
- reason for change
- impact scope
- follow-up actions

If a lightweight ADR flow is introduced later, use it consistently.

## 5. Development Workflow

### 5.1 Before Implementation

Before coding:

- confirm the target workflow or module
- identify impacted docs and config
- identify required persistence and observability updates
- identify whether the change affects API contracts or data schema

### 5.2 During Implementation

During coding:

- keep functions and modules focused
- preserve internal naming consistency
- add or update tests with the change
- record new configuration needs
- update docs when the design meaning changes

### 5.3 After Implementation

After coding:

- run relevant checks
- verify outputs
- record any residual risks
- update roadmap or follow-up backlog if needed

## 6. Traceability Requirements

The platform under construction must itself preserve execution traceability.

This project should consistently design for:

- task-level state visibility
- step-level state visibility
- artifact persistence
- checkpoint resume
- cache hit visibility
- provider invocation traceability
- prompt and model version traceability

Any implementation that hides these concerns behind opaque helper code should be treated as incomplete.

## 7. Directory Conventions

Suggested repository expectations:

- `docs/` for design and planning documents
- `config/` for example configuration templates
- `src/` for application code
- `tests/` for automated tests

If the repository grows, keep the structure explicit and stable.

## 8. Security and Secrets

Never commit:

- real API keys
- real provider credentials
- private service endpoints that should not be public
- local override files with secrets

Use example config files plus ignored local config files instead.

## 9. Quality Bar

Prefer:

- boring and debuggable solutions
- explicit schemas
- observable background execution
- reusable workflow modules
- deterministic configuration loading

Avoid:

- hidden global state
- provider-specific business logic scattered through workflow code
- large undocumented refactors
- direct secret values in source files

## 10. Team Atmosphere

This project should maintain the following working atmosphere:

- clear scope
- explicit reasoning
- visible progress
- disciplined change tracking
- stable configuration boundaries
- practical incremental delivery

The default expectation is that every meaningful project action leaves behind enough structure for the next person to continue without guesswork.
