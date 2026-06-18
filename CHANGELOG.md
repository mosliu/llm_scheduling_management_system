# Changelog

## 2026-06-18

### Changed

- Normalized MySQL/MariaDB database URLs to use `charset=utf8mb4` for runtime and Alembic connections.
- Updated externally sourced text fields to use MySQL `LONGTEXT` with `utf8mb4` collation, covering documents, artifacts, search hits, fetch invocations, LLM invocation traces, and step error messages.
- Added startup schema reconciliation for legacy MySQL tables so API and worker startup can repair text column charset and type drift when migrations were not run first.

### Fixed

- Fixed worker crashes caused by MySQL rejecting Chinese or supplementary Unicode content in `documents.content_text`.
- Prevented large fetched PDF/document bodies from failing on MySQL's 64 KiB `TEXT` limit.

### Added

- Added Alembic migration `20260618_003` to upgrade existing MySQL text columns to `LONGTEXT CHARACTER SET utf8mb4`.
- Added database Unicode tests for MySQL DDL generation, DSN normalization, and long multilingual document persistence.
- Added an explicit `/briefing` search result limit control, defaulting to 20 results per selected search provider.
- Added `/briefing` completed-step metrics for per-provider search result counts, fetch method, fetch call count, and fetched document count.

## 2026-05-21

### Added

- Added manual-only access control with password-to-user mapping from `config/access.toml`.
- Added password-only browser login flow for `/console`, `/docs`, and other HTTP endpoints.
- Added persistent recording of raw LLM HTTP request and response snapshots in LLM invocation metadata.
- Added task execution documentation for the Liuzhou earthquake workflow run.
- Added a Markdown export of the generated Liuzhou earthquake report.
- Added broad Chinese docstrings and inline documentation across core services, providers, models, and HTTP routes to improve maintainability.

### Changed

- Improved the console task list to show task start time, request description, and execution requirements.
- Refined the console visual style and tab contrast for better readability.
- Updated OpenAI-compatible LLM requests to send profile `temperature` and token limit settings explicitly.
- Added support for parsing streaming `chat/completions` responses so long-running `gpt-5.4` report generation can succeed with `stream=true`.

### Fixed

- Fixed a deployment/runtime debugging gap by retaining enough LLM exchange detail to inspect gateway failures after execution.
- Fixed empty-response handling for OpenAI-compatible streaming chat completions by concatenating incremental `delta.content` chunks.

## 2026-05-20

### Added

- Added Linux `undeploy.sh` helper for removing installed `systemd` services.

### Changed

- Switched the default Linux service deployment user/group settings to `root` in the bundled deployment scripts.
